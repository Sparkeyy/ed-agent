"""Game session and session store for managing active games."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from ed_engine.engine.game_manager import GameManager


class GameSession:
    """Tracks a game in progress with player tokens."""

    def __init__(self, game_id: str, max_players: int) -> None:
        self.game_id: str = game_id
        self.game_manager: GameManager | None = None
        self.player_tokens: dict[str, str] = {}  # token -> player_id
        self.player_names: dict[str, str] = {}  # player_id -> name
        self.max_players: int = max_players
        self.started: bool = False
        self.sse_queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}  # token -> event queue

    def add_player(self, name: str) -> tuple[str, str]:
        """Add a player to the session. Returns (token, player_id)."""
        if len(self.player_tokens) >= self.max_players:
            raise ValueError("Game is full")
        if self.started:
            raise ValueError("Game has already started")

        token = str(uuid4())
        player_id = str(uuid4())
        self.player_tokens[token] = player_id
        self.player_names[player_id] = name
        return token, player_id

    def verify_token(self, token: str) -> str | None:
        """Returns player_id if token is valid, else None."""
        return self.player_tokens.get(token)

    def start_game(self) -> None:
        """Initialize the GameManager and start the game."""
        if self.started:
            raise ValueError("Game has already started")
        if len(self.player_tokens) < 2:
            raise ValueError("Need at least 2 players to start")

        # Build player list in join order
        names = [self.player_names[pid] for pid in self.player_tokens.values()]
        self.game_manager = GameManager(names)

        # Map our session player_ids to the GameManager's player UUIDs
        gm_players = self.game_manager.get_state().players
        session_pids = list(self.player_tokens.values())
        self._pid_to_gm_uuid: dict[str, str] = {}
        for i, session_pid in enumerate(session_pids):
            self._pid_to_gm_uuid[session_pid] = str(gm_players[i].id)

        self.started = True

    def get_gm_player_uuid(self, session_player_id: str) -> str | None:
        """Map a session player_id to the GameManager's internal UUID."""
        return getattr(self, "_pid_to_gm_uuid", {}).get(session_player_id)

    def register_sse(self, token: str) -> asyncio.Queue[dict[str, Any]]:
        """Register an SSE connection and return its event queue."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.sse_queues[token] = queue
        return queue

    def unregister_sse(self, token: str) -> None:
        """Remove an SSE queue when the connection closes."""
        self.sse_queues.pop(token, None)

    def broadcast_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Push an event to all connected SSE clients."""
        event = {"event": event_type, "data": data}
        for queue in self.sse_queues.values():
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop event for slow consumers


class SessionStore:
    """In-memory store of active game sessions."""

    def __init__(self) -> None:
        self._games: dict[str, GameSession] = {}

    def create(self, max_players: int, creator_name: str) -> GameSession:
        """Create a new game session with the creator as first player."""
        game_id = str(uuid4())
        session = GameSession(game_id=game_id, max_players=max_players)
        session.add_player(creator_name)
        self._games[game_id] = session
        return session

    def get(self, game_id: str) -> GameSession | None:
        return self._games.get(game_id)

    def remove(self, game_id: str) -> None:
        self._games.pop(game_id, None)


# Global store instance
store = SessionStore()
