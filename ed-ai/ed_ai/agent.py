"""Core AI player that polls the game engine and submits actions."""

from __future__ import annotations

import asyncio
import logging
import os
import random
from typing import Any

import httpx

from ed_ai.ollama_client import OllamaClient
from ed_ai.parser import ResponseParser
from ed_ai.prompts.personas import get_system_prompt
from ed_ai.prompts.serializer import GameStateSerializer

logger = logging.getLogger("ed_ai.agent")

# Season ordering for heuristic decisions
_SEASON_ORDER = {"spring": 0, "summer": 1, "autumn": 2, "winter": 3}

# RL model cache (loaded once per difficulty)
_rl_cache: dict[str, tuple[Any, float]] = {}


def _try_load_rl(difficulty: str) -> tuple[Any, float] | None:
    """Attempt to load RL model for given difficulty. Returns (network, temperature) or None."""
    if difficulty in _rl_cache:
        return _rl_cache[difficulty]
    try:
        from ed_ai.rl.checkpoint import load_for_difficulty
        network, temperature, _ = load_for_difficulty(difficulty)
        _rl_cache[difficulty] = (network, temperature)
        logger.info("RL model loaded for difficulty=%s (temp=%.1f)", difficulty, temperature)
        return (network, temperature)
    except (ImportError, FileNotFoundError) as e:
        logger.debug("RL model not available for %s: %s", difficulty, e)
        _rl_cache[difficulty] = None  # type: ignore[assignment]
        return None


class AIPlayer:
    """AI opponent that polls the game engine, thinks via Ollama or RL model, and submits actions."""

    MAX_RETRIES = 3
    POLL_INTERVAL = 1.0  # seconds between game state polls

    def __init__(
        self,
        game_id: str,
        player_token: str,
        player_id: str,
        difficulty: str = "journeyman",
        engine_url: str | None = None,
        ollama_client: OllamaClient | None = None,
        use_rl: bool | None = None,
    ) -> None:
        self.game_id = game_id
        self.player_token = player_token
        self.player_id = player_id
        self.difficulty = difficulty
        self.engine_url = (engine_url or os.environ.get("ED_ENGINE_URL", "http://localhost:4242")).rstrip("/")
        self.ollama = ollama_client or OllamaClient()
        self.parser = ResponseParser()
        self.serializer = GameStateSerializer()
        self.system_prompt = get_system_prompt(difficulty)
        self.is_running = False
        self.game_over = False
        self.turns_played = 0
        self.last_error: str | None = None
        # RL model: auto-detect if available, or force with use_rl param
        self._use_rl = use_rl
        self._rl_model = None
        self._rl_temperature = 1.0
        if use_rl is not False:
            rl = _try_load_rl(difficulty)
            if rl:
                self._rl_model, self._rl_temperature = rl

    async def play_game(self) -> None:
        """Main loop: poll for game state, think when it's our turn, submit action."""
        self.is_running = True
        logger.info("AI player started: game=%s difficulty=%s", self.game_id, self.difficulty)

        try:
            while not self.game_over:
                try:
                    state = await self.get_game_state()
                except httpx.HTTPError as exc:
                    logger.warning("Failed to get game state: %s", exc)
                    self.last_error = str(exc)
                    await asyncio.sleep(self.POLL_INTERVAL * 2)
                    continue

                # Check if game is over
                if state.get("game_over") or state.get("status") == "finished":
                    self.game_over = True
                    logger.info("Game over: game=%s turns=%d", self.game_id, self.turns_played)
                    break

                # Check if it's our turn and we have valid actions
                valid_actions = state.get("valid_actions", [])
                current_player = state.get("current_player_id", state.get("current_player"))
                is_our_turn = (
                    str(current_player) == str(self.player_id)
                    if current_player is not None
                    else bool(valid_actions)
                )

                if is_our_turn and valid_actions:
                    action = await self.think(state)
                    try:
                        await self.submit_action(action)
                        self.turns_played += 1
                        self.last_error = None
                    except httpx.HTTPError as exc:
                        logger.warning("Failed to submit action: %s", exc)
                        self.last_error = str(exc)

                await asyncio.sleep(self.POLL_INTERVAL)
        except asyncio.CancelledError:
            logger.info("AI player cancelled: game=%s", self.game_id)
        except Exception:
            logger.exception("AI player crashed: game=%s", self.game_id)
        finally:
            self.is_running = False

    async def get_game_state(self) -> dict[str, Any]:
        """Fetch current game state from the engine."""
        url = f"{self.engine_url}/api/v1/games/{self.game_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"player_token": self.player_token})
            resp.raise_for_status()
            return resp.json()

    async def submit_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Submit an action to the game engine."""
        url = f"{self.engine_url}/api/v1/games/{self.game_id}/action"
        payload = {"player_token": self.player_token, **action}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

    def _think_rl(self, state: dict[str, Any]) -> dict[str, Any] | None:
        """Try RL model inference. Returns action dict or None on failure."""
        if self._rl_model is None:
            return None
        try:
            import torch
            from ed_ai.rl.state_encoder import encode_state_from_dict
            from ed_ai.rl.action_encoder import (
                build_action_mask, build_event_id_map, decode_action,
            )

            valid_actions = state.get("valid_actions", [])
            if not valid_actions:
                return None

            encoded = encode_state_from_dict(state, self.player_id)
            event_id_map = build_event_id_map(state)
            mask = build_action_mask(valid_actions, event_id_map)
            if mask.sum() == 0:
                return None

            state_t = torch.from_numpy(encoded).float()
            mask_t = torch.from_numpy(mask).float()
            action_idx, _, _ = self._rl_model.get_action(
                state_t, mask_t, temperature=self._rl_temperature
            )
            action = decode_action(action_idx, valid_actions, event_id_map)
            if action and self._is_valid(action, valid_actions):
                logger.info("RL model chose action: %s", action.get("action_type"))
                return action
        except Exception as exc:
            logger.warning("RL inference failed: %s", exc)
        return None

    async def think(self, state: dict[str, Any]) -> dict[str, Any]:
        """AI reasoning: try RL model first, then Ollama, then heuristic fallback.

        Returns a valid action dict ready for submission.
        """
        valid_actions = state.get("valid_actions", [])

        # Try RL model first (<1ms inference)
        if self._rl_model is not None:
            rl_action = self._think_rl(state)
            if rl_action is not None:
                return rl_action
            logger.debug("RL model failed, falling through to Ollama")

        # Try Ollama if available
        user_prompt = self.serializer.serialize(state)
        ollama_available = await self.ollama.is_available()
        if ollama_available:
            last_error = ""
            for attempt in range(self.MAX_RETRIES):
                retry_hint = f"\n\nPrevious attempt failed: {last_error}" if last_error else ""
                try:
                    raw = await self.ollama.generate(
                        prompt=user_prompt + retry_hint,
                        system=self.system_prompt,
                    )
                    action = self.parser.parse(raw, valid_actions=valid_actions)
                    if action is not None and self._is_valid(action, valid_actions):
                        logger.info(
                            "Ollama chose action (attempt %d): %s", attempt + 1, action
                        )
                        return action
                    last_error = f"parsed action not in valid_actions (got: {action})"
                except Exception as exc:
                    last_error = str(exc)
                    logger.warning("Ollama attempt %d failed: %s", attempt + 1, exc)

            logger.info("Ollama failed after %d retries, using heuristic", self.MAX_RETRIES)
        else:
            logger.info("Ollama unavailable, using heuristic fallback")

        return self.heuristic_fallback(valid_actions, state)

    def heuristic_fallback(
        self, valid_actions: list[dict[str, Any]], state: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """When Ollama fails, pick action by simple heuristics.

        Priority:
        - Prefer play_card over place_worker (cards = points)
        - Prefer higher base_points cards
        - Prefer production cards early, prosperity cards late
        - Place workers on resource locations matching needed resources
        - Prepare for season when no good moves left
        """
        if not valid_actions:
            return {"action_type": "prepare_for_season"}

        # Categorize actions
        play_card_actions = []
        place_worker_actions = []
        prepare_actions = []
        claim_event_actions = []
        resolve_choice_actions = []
        other_actions = []

        for action in valid_actions:
            action_type = action.get("action_type", action.get("type", ""))
            if action_type == "play_card":
                play_card_actions.append(action)
            elif action_type == "place_worker":
                place_worker_actions.append(action)
            elif action_type == "prepare_for_season":
                prepare_actions.append(action)
            elif action_type == "claim_event":
                claim_event_actions.append(action)
            elif action_type == "resolve_choice":
                resolve_choice_actions.append(action)
            else:
                other_actions.append(action)

        # Resolve choices immediately — pick by base_points or resource value
        if resolve_choice_actions:
            def resolve_score(a: dict) -> float:
                pts = a.get("base_points", 0) or 0
                if pts:
                    return pts
                # Resource value heuristic
                val = a.get("value", "")
                resource_value = {"pebble": 4, "resin": 3, "berry": 2, "twig": 1}
                return resource_value.get(val, 0)
            resolve_choice_actions.sort(key=resolve_score, reverse=True)
            return resolve_choice_actions[0]

        # Claim events — free VP, always prioritize
        if claim_event_actions:
            return claim_event_actions[0]

        # Determine game phase from season (check player-level season)
        season = "spring"
        if state:
            # Season may be at top level or in current player data
            season = state.get("season", "")
            if not season:
                players = state.get("players", [])
                for p in players:
                    if p.get("is_current"):
                        season = p.get("season", "spring")
                        break
        season = season.lower() if isinstance(season, str) else "spring"
        season_idx = _SEASON_ORDER.get(season, 0)
        is_late_game = season_idx >= 2  # autumn or winter

        # Prefer play_card actions, sorted by efficiency
        if play_card_actions:
            def card_score(a: dict) -> float:
                pts = a.get("base_points", a.get("points", 0)) or 0
                card_type = a.get("card_type", "").lower()
                # Free plays via paired construction
                bonus = 10 if a.get("use_paired_construction") or a.get("is_free") else 0
                # Card type bonuses — match both short and full enum names
                if "production" in card_type and not is_late_game:
                    bonus += 3
                elif "prosperity" in card_type and is_late_game:
                    bonus += 3
                return pts + bonus

            play_card_actions.sort(key=card_score, reverse=True)
            return play_card_actions[0]

        # Place workers on resource locations
        if place_worker_actions:
            random.shuffle(place_worker_actions)
            return place_worker_actions[0]

        # Other actions
        if other_actions:
            return other_actions[0]

        # Prepare for season as last resort
        if prepare_actions:
            return prepare_actions[0]

        # Absolute fallback
        return valid_actions[0]

    @staticmethod
    def _is_valid(action: dict[str, Any], valid_actions: list[dict[str, Any]]) -> bool:
        """Check if the parsed action matches one of the valid actions."""
        if valid_actions is None:
            return True
        if not valid_actions:
            return False

        action_type = action.get("action_type", action.get("type", ""))
        if not action_type:
            return False

        # Check action type matches any valid action
        for va in valid_actions:
            va_type = va.get("action_type", va.get("type", ""))
            if action_type != va_type:
                continue
            # If types match, check key fields
            match = True
            for key in ("card_name", "location_id", "meadow_index", "source"):
                if key in action and key in va:
                    if action[key] != va[key]:
                        match = False
                        break
            if match:
                return True

        return False

    def status(self) -> dict[str, Any]:
        """Return current status for monitoring."""
        return {
            "game_id": self.game_id,
            "player_id": self.player_id,
            "difficulty": self.difficulty,
            "is_running": self.is_running,
            "game_over": self.game_over,
            "turns_played": self.turns_played,
            "last_error": self.last_error,
        }
