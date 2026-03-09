from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone


class PlayerStore:
    def __init__(self, db_path: str = "ed_engine_players.db") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                elo INTEGER DEFAULT 1200,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                player_id TEXT,
                final_score INTEGER,
                placement INTEGER,
                elo_before INTEGER,
                elo_after INTEGER,
                played_at TEXT
            );
            CREATE TABLE IF NOT EXISTS move_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                player_id TEXT,
                turn_number INTEGER,
                quality TEXT,
                played_at TEXT
            );
        """)
        self._conn.commit()

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        return dict(row)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_or_create_player(self, username: str) -> dict:
        existing = self.get_player_by_username(username)
        if existing:
            return existing

        player_id = uuid.uuid4().hex[:8]
        now = self._now()
        self._conn.execute(
            "INSERT INTO players (id, username, elo, games_played, wins, created_at, updated_at) "
            "VALUES (?, ?, 1200, 0, 0, ?, ?)",
            (player_id, username, now, now),
        )
        self._conn.commit()
        return self.get_player(player_id)  # type: ignore[return-value]

    def get_player(self, player_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        return self._row_to_dict(row)

    def get_player_by_username(self, username: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM players WHERE username = ?", (username,)
        ).fetchone()
        return self._row_to_dict(row)

    def update_elo(self, player_id: str, new_elo: int) -> None:
        self._conn.execute(
            "UPDATE players SET elo = ?, updated_at = ? WHERE id = ?",
            (new_elo, self._now(), player_id),
        )
        self._conn.commit()

    def record_game(
        self,
        game_id: str,
        player_id: str,
        final_score: int,
        placement: int,
        elo_before: int,
        elo_after: int,
    ) -> None:
        now = self._now()
        self._conn.execute(
            "INSERT INTO game_history (game_id, player_id, final_score, placement, elo_before, elo_after, played_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (game_id, player_id, final_score, placement, elo_before, elo_after, now),
        )
        # Update player stats
        is_win = 1 if placement == 1 else 0
        self._conn.execute(
            "UPDATE players SET games_played = games_played + 1, wins = wins + ?, "
            "elo = ?, updated_at = ? WHERE id = ?",
            (is_win, elo_after, now, player_id),
        )
        self._conn.commit()

    def record_move_quality(
        self, game_id: str, player_id: str, turn_number: int, quality: str
    ) -> None:
        self._conn.execute(
            "INSERT INTO move_quality (game_id, player_id, turn_number, quality, played_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (game_id, player_id, turn_number, quality, self._now()),
        )
        self._conn.commit()

    def get_game_history(self, player_id: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM game_history WHERE player_id = ? ORDER BY played_at DESC LIMIT ?",
            (player_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_move_accuracy(self, player_id: str) -> float:
        """Percentage of moves rated 'good' or better."""
        total = self._conn.execute(
            "SELECT COUNT(*) FROM move_quality WHERE player_id = ?", (player_id,)
        ).fetchone()[0]
        if total == 0:
            return 0.0
        good = self._conn.execute(
            "SELECT COUNT(*) FROM move_quality WHERE player_id = ? AND quality IN ('good', 'great', 'excellent', 'perfect')",
            (player_id,),
        ).fetchone()[0]
        return round(good / total * 100.0, 1)

    def get_leaderboard(self, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM players ORDER BY elo DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_player_stats(self, player_id: str) -> dict:
        player = self.get_player(player_id)
        if player is None:
            return {}

        games = player["games_played"]
        win_rate = round(player["wins"] / games * 100.0, 1) if games > 0 else 0.0
        accuracy = self.get_move_accuracy(player_id)

        # Average score
        avg_row = self._conn.execute(
            "SELECT AVG(final_score) FROM game_history WHERE player_id = ?", (player_id,)
        ).fetchone()
        avg_score = round(avg_row[0], 1) if avg_row[0] is not None else 0.0

        # Best placement
        best_row = self._conn.execute(
            "SELECT MIN(placement) FROM game_history WHERE player_id = ?", (player_id,)
        ).fetchone()
        best_placement = best_row[0] if best_row[0] is not None else None

        return {
            **player,
            "win_rate": win_rate,
            "avg_score": avg_score,
            "best_placement": best_placement,
            "move_accuracy": accuracy,
        }

    def close(self) -> None:
        self._conn.close()
