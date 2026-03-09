from __future__ import annotations

from typing import Any
from uuid import UUID

import aiosqlite

DB_PATH = "ed_engine.db"


class SQLiteManager:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        """Create tables if they don't exist."""
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS game_results (
                id TEXT PRIMARY KEY,
                players_json TEXT NOT NULL,
                winner_id TEXT,
                scores_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def get_player(self, player_id: UUID) -> dict[str, Any] | None:
        """Fetch a player by id."""
        raise NotImplementedError

    async def save_player(self, player_id: UUID, name: str) -> None:
        """Insert or update a player."""
        raise NotImplementedError

    async def save_game_result(
        self,
        game_id: UUID,
        players_json: str,
        winner_id: UUID | None,
        scores_json: str,
    ) -> None:
        """Persist a completed game result."""
        raise NotImplementedError
