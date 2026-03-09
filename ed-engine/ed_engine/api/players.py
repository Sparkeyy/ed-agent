"""Player API — profiles, leaderboard, and ELO tracking."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ed_engine.db import PlayerStore

router = APIRouter()

# Singleton store — initialized once at import time
_store = PlayerStore()

CLASSIFICATIONS = [
    (1600, "Elder"),
    (1400, "Ranger"),
    (1200, "Forager"),
    (1000, "Wanderer"),
    (0, "Seedling"),
]


def classify(elo: int) -> str:
    for threshold, name in CLASSIFICATIONS:
        if elo >= threshold:
            return name
    return "Seedling"


def get_store() -> PlayerStore:
    return _store


class RegisterPlayerRequest(BaseModel):
    name: str


@router.post("")
async def register_player(req: RegisterPlayerRequest) -> dict:
    player = _store.get_or_create_player(req.name)
    player["classification"] = classify(player["elo"])
    return player


@router.get("/leaderboard")
async def leaderboard(limit: int = 20) -> list[dict]:
    entries = _store.get_leaderboard(limit=limit)
    for e in entries:
        e["classification"] = classify(e["elo"])
    return entries


@router.get("/{username}")
async def get_profile(username: str) -> dict:
    player = _store.get_player_by_username(username)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    stats = _store.get_player_stats(player["id"])
    stats["classification"] = classify(stats["elo"])
    stats["avg_move_accuracy"] = stats.pop("move_accuracy", 0.0)
    stats["elo_history"] = _store.get_elo_history(player["id"])

    # Shape game_history into recent_games format
    raw_history = _store.get_game_history(player["id"])
    recent_games = []
    for g in raw_history:
        recent_games.append({
            "game_id": g["game_id"],
            "date": g.get("played_at", ""),
            "players": 0,  # not tracked per-game yet
            "placement": g["placement"],
            "score": g["final_score"],
            "opponent_scores": [],
        })
    stats["recent_games"] = recent_games
    return stats
