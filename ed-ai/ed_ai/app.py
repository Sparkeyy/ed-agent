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
    source: str = "ollama"  # "ollama" or "heuristic"


class EvaluateRequest(BaseModel):
    game_state: str
    action_taken: dict[str, Any]
    valid_actions: list[dict[str, Any]] = Field(default_factory=list)
    difficulty: str = Field(default="journeyman", pattern="^(apprentice|journeyman|master)$")


class AlternativeAction(BaseModel):
    action: dict[str, Any]
    reason: str


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
    """Given a game state + valid_actions, return chosen action (for external callers)."""
    # Merge valid_actions into game_state if provided separately
    state = dict(req.game_state)
    if req.valid_actions and "valid_actions" not in state:
        state["valid_actions"] = req.valid_actions
    elif req.valid_actions:
        state["valid_actions"] = req.valid_actions

    serializer = GameStateSerializer()
    parser = ResponseParser()
    system_prompt = get_system_prompt(req.difficulty)
    valid_actions = state.get("valid_actions", [])
    user_prompt = serializer.serialize(state)

    # Try Ollama
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
    temp_player = AIPlayer(
        game_id="", player_token="", player_id="",
        difficulty=req.difficulty, ollama_client=_ollama,
    )
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
