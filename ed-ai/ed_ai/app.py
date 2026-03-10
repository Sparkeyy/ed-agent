"""FastAPI service for the Everdell AI opponent."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from ed_ai.agent import AIPlayer
from ed_ai.evaluator import evaluate_move
from ed_ai.ollama_client import OllamaClient
from ed_ai.parser import ResponseParser
from ed_ai.prompts.personas import get_system_prompt
from ed_ai.prompts.serializer import GameStateSerializer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("ed_ai.app")

app = FastAPI(title="ed-ai", version="0.2.0", description="AI opponent for Everdell")

# Shared state
_active_games: dict[str, AIPlayer] = {}
_ollama = OllamaClient()

ENGINE_URL = os.environ.get("ED_ENGINE_URL", "http://localhost:4242")


# --- Request / Response models ---

class JoinRequest(BaseModel):
    game_id: str
    difficulty: str = Field(default="journeyman", pattern="^(apprentice|journeyman|master)$")
    name: str = "AI Player"


class JoinResponse(BaseModel):
    game_id: str
    player_id: str
    difficulty: str
    message: str


class ThinkRequest(BaseModel):
    game_state: dict[str, Any]
    valid_actions: list[dict[str, Any]] = Field(default_factory=list)
    difficulty: str = "journeyman"


class ThinkResponse(BaseModel):
    action: dict[str, Any]
    reasoning: str = ""
    retries: int = 0
    source: str = "rl"  # "rl", "ollama", or "heuristic"


class EvaluateRequest(BaseModel):
    game_state: dict[str, Any]
    action_taken: dict[str, Any]
    valid_actions: list[dict[str, Any]] = Field(default_factory=list)
    difficulty: str = Field(default="journeyman", pattern="^(apprentice|journeyman|master)$")


class AlternativeAction(BaseModel):
    action: dict[str, Any]
    reason: str
    score_delta: float = 0.0


class EvaluateResponse(BaseModel):
    quality: str
    score: float = Field(ge=0.0, le=1.0)
    alternatives: list[AlternativeAction] = Field(default_factory=list)
    explanation: str


class GameSession(BaseModel):
    game_id: str
    player_id: str
    difficulty: str
    is_running: bool
    game_over: bool
    turns_played: int
    last_error: str | None = None


# --- Endpoints ---

@app.post("/join", response_model=JoinResponse)
async def join_game(req: JoinRequest, background_tasks: BackgroundTasks) -> JoinResponse:
    """Join an existing game as an AI player and start playing in background."""
    if req.game_id in _active_games:
        existing = _active_games[req.game_id]
        if existing.is_running:
            raise HTTPException(400, f"AI already active in game {req.game_id}")

    # Join the game via engine API
    join_url = f"{ENGINE_URL}/api/v1/games/{req.game_id}/join"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(join_url, json={"player_name": req.name})
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Failed to join game: {exc}") from exc

    player_token = data.get("player_token", "")
    player_id = str(data.get("player_id", ""))

    if not player_token:
        raise HTTPException(502, f"Engine returned no player_token: {data}")

    # Create AI player and start background task
    player = AIPlayer(
        game_id=req.game_id,
        player_token=player_token,
        player_id=player_id,
        difficulty=req.difficulty,
        engine_url=ENGINE_URL,
        ollama_client=_ollama,
    )
    _active_games[req.game_id] = player
    background_tasks.add_task(player.play_game)

    logger.info("AI joined game %s as %s (difficulty=%s)", req.game_id, req.name, req.difficulty)
    return JoinResponse(
        game_id=req.game_id,
        player_id=player_id,
        difficulty=req.difficulty,
        message=f"AI '{req.name}' joined and is now playing.",
    )


@app.post("/think", response_model=ThinkResponse)
async def think(req: ThinkRequest) -> ThinkResponse:
    """Given a game state + valid_actions, return chosen action (for external callers).

    Pipeline: RL model → Ollama → heuristic fallback.
    """
    # Merge valid_actions into game_state if provided separately
    state = dict(req.game_state)
    if req.valid_actions and "valid_actions" not in state:
        state["valid_actions"] = req.valid_actions
    elif req.valid_actions:
        state["valid_actions"] = req.valid_actions

    valid_actions = state.get("valid_actions", [])

    # Try RL model first (<1ms inference)
    temp_player = AIPlayer(
        game_id="", player_token="", player_id="",
        difficulty=req.difficulty, ollama_client=_ollama,
        use_rl=True,
    )
    if temp_player._rl_model is not None:
        rl_action = temp_player._think_rl(state)
        if rl_action is not None:
            return ThinkResponse(
                action=rl_action,
                reasoning="RL model inference",
                retries=0,
                source="rl",
            )
        logger.info("/think: RL inference failed, trying Ollama")

    # Try Ollama
    serializer = GameStateSerializer()
    parser = ResponseParser()
    system_prompt = get_system_prompt(req.difficulty)
    user_prompt = serializer.serialize(state)

    ollama_available = await _ollama.is_available()
    if ollama_available:
        last_error = ""
        for attempt in range(3):
            retry_hint = f"\n\nPrevious attempt failed: {last_error}" if last_error else ""
            try:
                raw = await _ollama.generate(
                    prompt=user_prompt + retry_hint,
                    system=system_prompt,
                )
                action = parser.parse(raw, valid_actions=valid_actions)
                if action is not None:
                    return ThinkResponse(
                        action=action,
                        reasoning=raw,
                        retries=attempt,
                        source="ollama",
                    )
                last_error = "could not parse valid action from response"
            except Exception as exc:
                last_error = str(exc)

    # Heuristic fallback
    action = temp_player.heuristic_fallback(valid_actions, state)
    return ThinkResponse(
        action=action,
        reasoning="heuristic fallback",
        retries=3 if ollama_available else 0,
        source="heuristic",
    )


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest) -> EvaluateResponse:
    """Evaluate a player's move quality (chess-style rating with alternatives)."""
    result = await evaluate_move(
        ollama=_ollama,
        game_state=req.game_state,
        action_taken=req.action_taken,
        valid_actions=req.valid_actions,
        difficulty=req.difficulty,
    )
    return EvaluateResponse(**result)


class ChatRequest(BaseModel):
    question: str
    game_context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    answer: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Answer rules questions about Everdell using the AI assistant."""
    system = (
        "You are an Everdell rules expert. Answer questions about the base game only. "
        "Be concise and accurate. No expansion content. If asked about strategy, "
        "give brief practical advice."
    )
    user_msg = req.question
    if req.game_context:
        import json
        user_msg += f"\n\nCurrent game context: {json.dumps(req.game_context, default=str)[:2000]}"
    try:
        resp = await _ollama.generate(prompt=user_msg, system=system)
        return ChatResponse(answer=resp)
    except Exception:
        return ChatResponse(answer="AI assistant is currently unavailable. Check the Rules tab for reference.")


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check including Ollama connectivity."""
    ollama_ok = await _ollama.is_available()
    ollama_models: list[str] = []
    if ollama_ok:
        try:
            ollama_models = await _ollama.list_models()
        except Exception:
            pass

    active_count = sum(1 for p in _active_games.values() if p.is_running)
    return {
        "status": "ok",
        "service": "ed-ai",
        "ollama_available": ollama_ok,
        "ollama_host": _ollama.base_url,
        "ollama_model": _ollama.model,
        "ollama_models": ollama_models,
        "active_games": active_count,
        "total_games": len(_active_games),
    }


@app.get("/games", response_model=list[GameSession])
async def list_games() -> list[GameSession]:
    """List all AI game sessions (active and completed)."""
    return [
        GameSession(**player.status())
        for player in _active_games.values()
    ]


# --- RL Training Endpoints ---

@app.get("/rl/status")
async def rl_status() -> dict[str, Any]:
    """Get RL model and training status."""
    from ed_ai.rl.train import get_training_status
    from ed_ai.rl.checkpoint import list_checkpoints, DEFAULT_MODEL_DIR

    training = get_training_status()
    checkpoints = list_checkpoints()
    rl_loaded = bool(getattr(app, "_rl_loaded", False))

    return {
        "training": training,
        "checkpoints": checkpoints,
        "model_dir": str(DEFAULT_MODEL_DIR),
        "rl_available": len(checkpoints) > 0,
    }


class TrainRequest(BaseModel):
    num_batches: int = Field(default=10000, ge=1, le=1000000)
    games_per_batch: int = Field(default=64, ge=1, le=512)
    num_workers: int | None = None
    lr: float = Field(default=3e-4, gt=0)
    temperature: float = Field(default=1.0, gt=0)
    resume_from: str | None = None


@app.post("/rl/train")
async def rl_train(req: TrainRequest) -> dict[str, Any]:
    """Start RL training in background thread."""
    from ed_ai.rl.train import start_background_training

    result = start_background_training(
        num_batches=req.num_batches,
        games_per_batch=req.games_per_batch,
        num_workers=req.num_workers,
        lr=req.lr,
        temperature=req.temperature,
        resume_from=req.resume_from,
    )
    return result


@app.post("/rl/cancel")
async def rl_cancel() -> dict[str, Any]:
    """Cancel active RL training."""
    from ed_ai.rl.train import cancel_training
    return cancel_training()


@app.get("/rl/progress")
async def rl_progress(last_n: int = 50) -> dict[str, Any]:
    """Get recent training progress metrics."""
    from ed_ai.rl.checkpoint import DEFAULT_MODEL_DIR
    import json

    progress_file = DEFAULT_MODEL_DIR / "training_progress.jsonl"
    if not progress_file.exists():
        return {"metrics": [], "total_entries": 0}

    lines = progress_file.read_text().strip().split("\n")
    total = len(lines)
    recent = lines[-last_n:] if last_n < total else lines
    metrics = []
    for line in recent:
        try:
            metrics.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return {"metrics": metrics, "total_entries": total}
