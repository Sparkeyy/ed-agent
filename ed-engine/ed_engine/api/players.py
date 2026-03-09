from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory store stub
_players: dict[UUID, dict[str, Any]] = {}


class RegisterPlayerRequest(BaseModel):
    name: str


@router.post("", response_model=dict)
async def register_player(req: RegisterPlayerRequest) -> dict[str, Any]:
    """Register a new player."""
    from uuid import uuid4

    player_id = uuid4()
    player = {"id": str(player_id), "name": req.name, "games_played": 0, "wins": 0}
    _players[player_id] = player
    return player


@router.get("/{player_id}")
async def get_player(player_id: UUID) -> dict[str, Any]:
    """Get a player profile."""
    player = _players.get(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("")
async def leaderboard() -> list[dict[str, Any]]:
    """Get the leaderboard."""
    return sorted(_players.values(), key=lambda p: p.get("wins", 0), reverse=True)
