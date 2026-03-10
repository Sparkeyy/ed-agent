"""In-process AI player that runs as a background asyncio task."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from uuid import UUID

from ed_engine.engine.actions import GameAction

logger = logging.getLogger("ed_engine.ai_runner")

# Active AI tasks keyed by (game_id, player_id)
_ai_tasks: dict[tuple[str, str], asyncio.Task] = {}

AI_NAMES = [
    "Rugwort", "Bramblewick", "Thistledew", "Mossclaw", "Fernwhisper",
    "Ashenbark", "Willowmere", "Pebblethorn", "Dewcrest", "Ivywood",
]

_name_counter = 0


def next_ai_name() -> str:
    global _name_counter
    name = AI_NAMES[_name_counter % len(AI_NAMES)]
    _name_counter += 1
    return name


async def run_ai_player(
    session: Any,  # GameSession
    player_token: str,
    player_id: str,
    difficulty: str,
) -> None:
    """Background task: poll game state, pick action, submit."""
    game_id = session.game_id
    logger.info("AI started: game=%s player=%s difficulty=%s", game_id, player_id, difficulty)

    try:
        # Wait for game to start
        while not session.started:
            await asyncio.sleep(0.5)

        gm = session.game_manager
        if gm is None:
            return

        gm_uuid_str = session.get_gm_player_uuid(player_id)
        if gm_uuid_str is None:
            logger.error("AI player %s not found in game manager mapping", player_id)
            return

        gm_uuid = UUID(gm_uuid_str)
        turns = 0

        while True:
            game = gm.get_state()
            if game.game_over:
                logger.info("AI done: game=%s turns=%d", game_id, turns)
                break

            current = gm.get_current_player()
            if current is None or current.id != gm_uuid:
                await asyncio.sleep(0.8)
                continue

            # Get valid actions
            valid_actions = gm.get_valid_actions(gm_uuid_str)
            if not valid_actions:
                await asyncio.sleep(0.5)
                continue

            # Pick action
            action = _pick_action(valid_actions, game, difficulty)

            # Delay before executing so humans can see the board state
            await asyncio.sleep(1.2 if difficulty == "master" else 0.8)

            # Execute
            try:
                kwargs: dict[str, Any] = {}
                if action.location_id:
                    kwargs["location_id"] = action.location_id
                if action.card_name:
                    kwargs["card_name"] = action.card_name
                if action.source:
                    kwargs["source"] = action.source
                if action.meadow_index is not None:
                    kwargs["meadow_index"] = action.meadow_index
                if action.use_paired_construction:
                    kwargs["use_paired_construction"] = True
                if action.choice_index is not None:
                    kwargs["choice_index"] = action.choice_index

                gm.perform_action(gm_uuid, action.action_type, **kwargs)
                turns += 1

                # Broadcast updated state to SSE subscribers
                _broadcast_state(session)

            except (ValueError, Exception) as exc:
                logger.warning("AI action failed: %s — %s", action, exc)

    except asyncio.CancelledError:
        logger.info("AI cancelled: game=%s", game_id)
    except Exception:
        logger.exception("AI crashed: game=%s", game_id)
    finally:
        _ai_tasks.pop((game_id, player_id), None)


def _broadcast_state(session: Any) -> None:
    """Push game state to all SSE subscribers."""
    from ed_engine.engine.perspective import PerspectiveFilter
    if session.game_manager is None:
        return
    for sse_token, queue in list(session.sse_queues.items()):
        try:
            # Build per-player filtered state
            session_pid = session.verify_token(sse_token)
            gm_pid = session.get_gm_player_uuid(session_pid) if session_pid else None
            filtered = PerspectiveFilter.serialize_for_api(session.game_manager, player_id=gm_pid)

            # Remap IDs
            gm_to_session: dict[str, str] = {}
            for spid, gm_uuid in getattr(session, "_pid_to_gm_uuid", {}).items():
                gm_to_session[gm_uuid] = spid
            filtered["game_id"] = session.game_id
            if filtered.get("current_player_id") in gm_to_session:
                filtered["current_player_id"] = gm_to_session[filtered["current_player_id"]]
            for p in filtered.get("players", []):
                if p.get("id") in gm_to_session:
                    p["id"] = gm_to_session[p["id"]]

            event = {"event": "game_state", "data": filtered}
            queue.put_nowait(event)
        except (asyncio.QueueFull, KeyError):
            pass

    # Check game over
    if session.game_manager.get_state().game_over:
        session.broadcast_event("game_over", {"game_id": session.game_id})


def _pick_action(
    valid_actions: list[GameAction], game: Any, difficulty: str
) -> GameAction:
    """Heuristic action selection. Difficulty affects strategy quality."""
    if len(valid_actions) == 1:
        return valid_actions[0]

    # --- Resolve choices: context-aware for all difficulties ---
    resolve = [a for a in valid_actions if a.action_type == "resolve_choice"]
    if resolve:
        if difficulty == "apprentice":
            return random.choice(resolve)
        return _smart_resolve(resolve, game)

    # Categorize
    play_card = [a for a in valid_actions if a.action_type == "play_card"]
    place_worker = [a for a in valid_actions if a.action_type == "place_worker"]
    prepare = [a for a in valid_actions if a.action_type == "prepare_for_season"]
    claim_event = [a for a in valid_actions if a.action_type == "claim_event"]

    # --- Apprentice: mostly random ---
    if difficulty == "apprentice":
        if random.random() < 0.3 and play_card:
            return random.choice(play_card)
        return random.choice(valid_actions)

    # --- Claim events first — free VP for journeyman & master ---
    if claim_event:
        return claim_event[0]

    # --- Score each play_card action ---
    if play_card:
        scored = []
        for a in play_card:
            card = _find_card(a, game)
            pts = card.base_points if card else 0

            # Free plays (paired construction) are always top priority
            if a.use_paired_construction:
                scored.append((100 + pts, a))
                continue

            cost = card.cost.total() if card and hasattr(card, "cost") else 0
            card_type = str(card.card_type) if card and hasattr(card, "card_type") else ""

            # Efficiency: VP value minus resource cost penalty
            score = pts * 2 - cost

            # Production cards better early (more activations ahead)
            if "GREEN_PRODUCTION" in card_type:
                score += 3
            # Prosperity cards better late (on_score bonus)
            if "PURPLE_PROSPERITY" in card_type:
                score += 2

            scored.append((score, a))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Master: always pick best. Journeyman: 80% best, 20% second best.
        if difficulty == "master" or len(scored) == 1:
            return scored[0][1]
        if random.random() < 0.8:
            return scored[0][1]
        return scored[min(1, len(scored) - 1)][1]

    if place_worker:
        random.shuffle(place_worker)
        return place_worker[0]

    if prepare:
        return prepare[0]

    return valid_actions[0]


def _smart_resolve(resolve: list[GameAction], game: Any) -> GameAction:
    """Score resolve_choice options by context (card type, resource value)."""
    pc = game.pending_choice if game.pending_choice else {}
    choice_type = pc.get("choice_type", "")
    options = pc.get("options", [])

    def score_option(action: GameAction) -> float:
        idx = action.choice_index or 0
        opt = options[idx] if idx < len(options) else {}
        if not isinstance(opt, dict):
            return 0

        # Card selection: pick highest base_points
        if choice_type == "select_card":
            return opt.get("base_points", 0)

        # Resource selection: value pebble > resin > berry > twig
        if choice_type == "select_resource":
            val = opt.get("value", "")
            # Trade-count options ("0", "1", "2"): prefer trading 1 (net positive
            # without wasting too many resolve turns)
            if val.isdigit():
                n = int(val)
                return 1 if n == 1 else (0.5 if n == 0 else -1)
            resource_value = {"pebble": 4, "resin": 3, "berry": 2, "twig": 1}
            return resource_value.get(val, 0)

        return 0

    return max(resolve, key=score_option)


def _find_card(action: GameAction, game: Any) -> Any:
    """Find the card object for a play_card action."""
    if action.source == "meadow" and action.meadow_index is not None:
        if 0 <= action.meadow_index < len(game.meadow):
            return game.meadow[action.meadow_index]
    if action.source == "hand" and action.card_name:
        for p in game.players:
            for c in p.hand:
                if c.name == action.card_name:
                    return c
    return None


def start_ai(session: Any, player_token: str, player_id: str, difficulty: str) -> None:
    """Launch an AI background task for this player."""
    key = (session.game_id, player_id)
    if key in _ai_tasks:
        task = _ai_tasks[key]
        if not task.done():
            return  # Already running
    task = asyncio.create_task(run_ai_player(session, player_token, player_id, difficulty))
    _ai_tasks[key] = task
