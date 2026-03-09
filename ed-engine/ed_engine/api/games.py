"""Games API — create, join, query, act, and stream game events."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import StreamingResponse

from ed_engine.api.schemas import (
    AddAiRequest,
    AddAiResponse,
    CreateGameRequest,
    CreateGameResponse,
    GameStateResponse,
    JoinGameRequest,
    JoinGameResponse,
    PerformActionRequest,
    PerformActionResponse,
    ValidAction,
)
from ed_engine.api.session import GameSession, store
from ed_engine.engine.ai_runner import start_ai
from ed_engine.engine.perspective import PerspectiveFilter
from ed_engine.db.elo import update_multiplayer_elo

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_game_state_response(
    session: GameSession,
    player_token: str | None = None,
) -> GameStateResponse:
    """Build a GameStateResponse from a session, filtered by perspective."""
    if not session.started or session.game_manager is None:
        # Game not started yet — return lobby state
        players_info = {
            pid: name for pid, name in session.player_names.items()
        }
        return GameStateResponse(
            game_id=session.game_id,
            state={
                "status": "waiting",
                "players": players_info,
                "max_players": session.max_players,
                "current_count": len(session.player_tokens),
            },
            valid_actions=[],
            current_player_id=None,
            game_over=False,
        )

    gm = session.game_manager

    # Resolve the requesting player's GM UUID for perspective filtering
    gm_player_id: str | None = None
    if player_token:
        session_pid = session.verify_token(player_token)
        if session_pid:
            gm_player_id = session.get_gm_player_uuid(session_pid)

    # Use PerspectiveFilter for the full state serialization
    filtered = PerspectiveFilter.serialize_for_api(gm, player_id=gm_player_id)

    # Reverse-map current_player_id from GM UUID to session player_id
    current_pid = None
    gm_current = filtered.get("current_player_id")
    if gm_current:
        for spid, gm_uuid in getattr(session, "_pid_to_gm_uuid", {}).items():
            if gm_uuid == gm_current:
                current_pid = spid
                break

    # Convert valid_actions to ValidAction schema objects
    valid_actions: list[ValidAction] = []
    for a in filtered.get("valid_actions", []):
        params: dict[str, Any] = {}
        if "location_id" in a:
            params["location_id"] = a["location_id"]
        if "card_name" in a:
            params["card_name"] = a["card_name"]
        if "source" in a:
            params["source"] = a["source"]
        if "meadow_index" in a:
            params["meadow_index"] = a["meadow_index"]
        if a.get("use_paired_construction"):
            params["use_paired_construction"] = True
        valid_actions.append(
            ValidAction(
                action_type=a["action_type"],
                description="",
                params=params,
            )
        )

    # Remap all GM UUIDs to session player IDs so frontend sees consistent IDs
    gm_to_session: dict[str, str] = {}
    for spid, gm_uuid in getattr(session, "_pid_to_gm_uuid", {}).items():
        gm_to_session[gm_uuid] = spid

    filtered["game_id"] = session.game_id
    if filtered.get("current_player_id") in gm_to_session:
        filtered["current_player_id"] = gm_to_session[filtered["current_player_id"]]
    for p in filtered.get("players", []):
        if p.get("id") in gm_to_session:
            p["id"] = gm_to_session[p["id"]]

    return GameStateResponse(
        game_id=session.game_id,
        state=filtered,
        valid_actions=valid_actions,
        current_player_id=current_pid,
        game_over=filtered["game_over"],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=CreateGameResponse)
async def create_game(req: CreateGameRequest) -> CreateGameResponse:
    """Create a new game session."""
    session = store.create(max_players=req.player_count, creator_name=req.creator_name)
    # The creator is the first player
    token = list(session.player_tokens.keys())[0]
    player_id = session.player_tokens[token]
    return CreateGameResponse(
        game_id=session.game_id,
        player_token=token,
        player_id=player_id,
    )


@router.post("/{game_id}/join", response_model=JoinGameResponse)
async def join_game(game_id: str, req: JoinGameRequest) -> JoinGameResponse:
    """Join an existing game."""
    session = store.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game not found")

    try:
        token, player_id = session.add_player(req.player_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Broadcast player_joined
    session.broadcast_event("player_joined", {
        "player_id": player_id,
        "player_name": req.player_name,
    })

    # Auto-start when full
    if len(session.player_tokens) == session.max_players:
        session.start_game()
        session.broadcast_event("game_started", {"game_id": session.game_id})

    return JoinGameResponse(player_token=token, player_id=player_id)


@router.post("/{game_id}/ai", response_model=AddAiResponse)
async def add_ai_player(game_id: str, req: AddAiRequest) -> AddAiResponse:
    """Add an AI opponent to the game."""
    session = store.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if session.started:
        raise HTTPException(status_code=400, detail="Game has already started")

    if len(session.player_tokens) >= session.max_players:
        raise HTTPException(status_code=400, detail="Game is full")

    # Add AI as a regular player
    try:
        token, player_id = session.add_player(req.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Mark as AI in session
    if not hasattr(session, "ai_players"):
        session.ai_players = {}  # type: ignore[attr-defined]
    session.ai_players[player_id] = {"token": token, "difficulty": req.difficulty}  # type: ignore[attr-defined]

    # Broadcast player_joined
    session.broadcast_event("player_joined", {
        "player_id": player_id,
        "player_name": req.name,
        "is_ai": True,
        "difficulty": req.difficulty,
    })

    # Auto-start when full
    if len(session.player_tokens) == session.max_players:
        session.start_game()
        session.broadcast_event("game_started", {"game_id": session.game_id})

        # Start background tasks for all AI players
        for ai_pid, ai_info in session.ai_players.items():  # type: ignore[attr-defined]
            start_ai(session, ai_info["token"], ai_pid, ai_info["difficulty"])

    return AddAiResponse(player_id=player_id, name=req.name, difficulty=req.difficulty)


@router.get("/{game_id}", response_model=GameStateResponse)
async def get_game(
    game_id: str,
    player_token: str | None = Query(default=None),
) -> GameStateResponse:
    """Get the current game state."""
    session = store.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game not found")

    return _build_game_state_response(session, player_token)


@router.post("/{game_id}/action", response_model=PerformActionResponse)
async def perform_action(game_id: str, req: PerformActionRequest) -> PerformActionResponse:
    """Perform a game action."""
    session = store.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if not session.started or session.game_manager is None:
        raise HTTPException(status_code=400, detail="Game has not started yet")

    # Verify token
    session_pid = session.verify_token(req.player_token)
    if session_pid is None:
        raise HTTPException(status_code=403, detail="Invalid player token")

    # Map to GameManager UUID
    gm_uuid_str = session.get_gm_player_uuid(session_pid)
    if gm_uuid_str is None:
        raise HTTPException(status_code=403, detail="Player not in this game")

    gm_uuid = UUID(gm_uuid_str)

    # Check it's this player's turn
    current = session.game_manager.get_current_player()
    if current is None or current.id != gm_uuid:
        raise HTTPException(status_code=400, detail="Not your turn")

    # Build kwargs for the action
    action_kwargs: dict[str, Any] = {}
    if req.location_id:
        action_kwargs["location_id"] = req.location_id
    if req.card_name:
        action_kwargs["card_name"] = req.card_name
    action_kwargs.update(req.payload)

    try:
        session.game_manager.perform_action(
            gm_uuid,
            req.action_type,
            **action_kwargs,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build response for the acting player
    game_resp = _build_game_state_response(session, req.player_token)

    # Broadcast per-player filtered state to each SSE subscriber
    for sse_token in list(session.sse_queues.keys()):
        player_resp = _build_game_state_response(session, sse_token)
        event = {"event": "game_state", "data": player_resp.model_dump(mode="json")}
        try:
            session.sse_queues[sse_token].put_nowait(event)
        except (asyncio.QueueFull, KeyError):
            pass  # Drop for slow/disconnected consumers

    # Check for game over
    if session.game_manager.get_state().game_over:
        scores = {
            session.player_names.get(spid, "?"): 0
            for spid in session.player_tokens.values()
        }
        # Compute scores from GameManager state
        for player in session.game_manager.get_state().players:
            for spid, gm_id in getattr(session, "_pid_to_gm_uuid", {}).items():
                if gm_id == str(player.id):
                    name = session.player_names.get(spid, "?")
                    scores[name] = player.score
                    break

        winner = max(scores, key=scores.get) if scores else None  # type: ignore[arg-type]
        session.broadcast_event("game_over", {"scores": scores, "winner": winner})

        # Update ELO ratings
        try:
            from ed_engine.api.players import get_store, classify

            ps = get_store()
            # Build results sorted by score (descending)
            elo_results = []
            sorted_players = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            for placement, (name, score) in enumerate(sorted_players, 1):
                player = ps.get_or_create_player(name)
                elo_results.append({
                    "player_id": player["id"],
                    "elo": player["elo"],
                    "placement": placement,
                    "score": score,
                    "name": name,
                })
            updated = update_multiplayer_elo(elo_results)
            for r in updated:
                ps.record_game(
                    game_id=session.game_id,
                    player_id=r["player_id"],
                    final_score=r["score"],
                    placement=r["placement"],
                    elo_before=r["elo"],
                    elo_after=r["new_elo"],
                )
        except Exception:
            pass  # ELO update is non-critical

    return PerformActionResponse(status="ok", game=game_resp)


@router.get("/{game_id}/events")
async def game_events(
    game_id: str,
    player_token: str | None = Query(default=None),
) -> StreamingResponse:
    """SSE event stream for a game."""
    session = store.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game not found")

    # Use a dedicated token key for anonymous viewers
    sse_key = player_token or f"anon-{id(asyncio.current_task())}"
    queue = session.register_sse(sse_key)

    async def event_generator():
        try:
            # Send initial connected event
            yield f"event: connected\ndata: {json.dumps({'game_id': game_id})}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = event["event"]
                    data = json.dumps(event["data"])
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat comment to keep connection alive
                    yield ": heartbeat\n\n"
        finally:
            session.unregister_sse(sse_key)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
