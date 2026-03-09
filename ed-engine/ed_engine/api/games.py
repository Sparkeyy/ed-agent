"""Games API — create, join, query, act, and stream game events."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import StreamingResponse

from ed_engine.api.schemas import (
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

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_game_state_response(
    session: GameSession,
    player_token: str | None = None,
) -> GameStateResponse:
    """Build a GameStateResponse from a session."""
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
    state = gm.get_state()
    current_player = gm.get_current_player()
    current_pid = None
    if current_player:
        # Reverse-map GameManager UUID to session player_id
        for spid, gm_uuid in getattr(session, "_pid_to_gm_uuid", {}).items():
            if gm_uuid == str(current_player.id):
                current_pid = spid
                break

    valid_actions: list[ValidAction] = []
    if player_token:
        session_pid = session.verify_token(player_token)
        if session_pid:
            gm_uuid = session.get_gm_player_uuid(session_pid)
            if gm_uuid:
                raw_actions = gm.get_valid_actions(UUID(gm_uuid))
                for a in raw_actions:
                    # GameAction is a Pydantic model; extract fields
                    if hasattr(a, "action_type"):
                        params: dict[str, Any] = {}
                        if a.location_id:
                            params["location_id"] = a.location_id
                        if a.card_name:
                            params["card_name"] = a.card_name
                        if a.source:
                            params["source"] = a.source
                        valid_actions.append(
                            ValidAction(
                                action_type=str(a.action_type),
                                description="",
                                params=params,
                            )
                        )
                    elif isinstance(a, dict):
                        valid_actions.append(
                            ValidAction(
                                action_type=a["action_type"],
                                description=a.get("description", ""),
                                params=a.get("params", {}),
                            )
                        )

    return GameStateResponse(
        game_id=session.game_id,
        state=state.model_dump(mode="json"),
        valid_actions=valid_actions,
        current_player_id=current_pid,
        game_over=state.game_over,
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

    # Build response
    game_resp = _build_game_state_response(session, req.player_token)

    # Broadcast state update
    session.broadcast_event("game_state", game_resp.model_dump(mode="json"))

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
