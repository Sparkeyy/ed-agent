import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ed_engine.engine.deck import setup_game
from ed_engine.models.game import GameState

router = APIRouter()

# In-memory store (will be replaced by DB later)
_games: dict[UUID, GameState] = {}


class CreateGameRequest(BaseModel):
    player_names: list[str]


class ActionRequest(BaseModel):
    player_id: UUID
    action_type: str
    payload: dict[str, Any] = {}


@router.post("", response_model=GameState)
async def create_game(req: CreateGameRequest) -> GameState:
    """Create a new game with the given players."""
    game = setup_game(req.player_names)
    _games[game.id] = game
    return game


@router.get("/{game_id}", response_model=GameState)
async def get_game(game_id: UUID) -> GameState:
    """Get the current game state."""
    game = _games.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("/{game_id}/action")
async def perform_action(game_id: UUID, req: ActionRequest) -> dict[str, Any]:
    """Perform a game action."""
    game = _games.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    # Stub: action processing will be wired up later
    return {"status": "ok", "message": "Action processing not yet implemented"}


@router.get("/{game_id}/events")
async def game_events(game_id: UUID) -> EventSourceResponse:
    """SSE stream of game events."""

    async def event_generator():
        # Stub: will emit real events once engine is wired
        yield {"event": "connected", "data": f'{{"game_id": "{game_id}"}}'}
        while True:
            await asyncio.sleep(30)
            yield {"event": "heartbeat", "data": "{}"}

    return EventSourceResponse(event_generator())
