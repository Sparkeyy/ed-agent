"""Serialize game state dict into a compact text prompt for the LLM."""

from __future__ import annotations

from typing import Any

# Resource emoji mapping
_RES = {"twig": "\U0001fab5", "resin": "\U0001f4a7", "pebble": "\U0001faa8", "berry": "\U0001fad0"}


def _res_str(resources: dict[str, int]) -> str:
    """Format resources as compact emoji string: 3wood 2resin 1pebble 4berry."""
    parts = []
    for key in ("twig", "resin", "pebble", "berry"):
        val = resources.get(key, 0)
        emoji = _RES.get(key, key)
        parts.append(f"{val}{emoji}")
    return " ".join(parts)


def _card_summary(card: dict[str, Any] | str) -> str:
    """Compact summary of a card."""
    if isinstance(card, str):
        return card
    name = card.get("name", card.get("card_name", "?"))
    pts = card.get("base_points", card.get("points", ""))
    cost_parts = []
    for res_key in ("twig", "resin", "pebble", "berry"):
        val = card.get(f"cost_{res_key}", card.get(res_key, 0))
        if val:
            cost_parts.append(f"{val}{_RES.get(res_key, res_key)}")
    cost_str = "".join(cost_parts) if cost_parts else "free"
    suffix = f" ({pts}pt, {cost_str})" if pts != "" else f" ({cost_str})"
    return f"{name}{suffix}"


class GameStateSerializer:
    """Convert an Everdell game state dict into a compact text prompt."""

    def serialize(self, state: dict[str, Any]) -> str:
        lines: list[str] = []

        # Header
        season = state.get("season", "?")
        turn = state.get("turn_number", state.get("turn", "?"))
        player_name = state.get("player_name", state.get("name", "AI"))
        lines.append("=== EVERDELL - YOUR TURN ===")
        lines.append(f'Season: {season} | Turn: {turn} | You are: "{player_name}"')
        lines.append("")

        # My resources
        resources = state.get("resources", {})
        if resources:
            lines.append(f"MY RESOURCES: {_res_str(resources)}")

        # Workers
        workers_avail = state.get("workers_available", state.get("available_workers", "?"))
        workers_total = state.get("workers_total", state.get("total_workers", "?"))
        lines.append(f"MY WORKERS: {workers_avail}/{workers_total} available")

        # City
        city = state.get("city", [])
        max_city = state.get("max_city_size", 15)
        if city:
            city_names = [_card_summary(c) for c in city]
            lines.append(f"MY CITY ({len(city)}/{max_city}): {', '.join(city_names)}")
        else:
            lines.append(f"MY CITY (0/{max_city}): empty")

        # Hand
        hand = state.get("hand", [])
        if hand:
            hand_items = [f"[{i+1}] {_card_summary(c)}" for i, c in enumerate(hand)]
            lines.append(f"MY HAND ({len(hand)}): {' '.join(hand_items)}")
        else:
            lines.append("MY HAND: empty")
        lines.append("")

        # Meadow
        meadow = state.get("meadow", [])
        if meadow:
            meadow_items = [f"[{i+1}] {_card_summary(c)}" for i, c in enumerate(meadow)]
            lines.append(f"MEADOW: {' '.join(meadow_items)}")
            lines.append("")

        # Opponents
        opponents = state.get("opponents", [])
        if opponents:
            opp_strs = []
            for opp in opponents:
                opp_name = opp.get("name", opp.get("player_name", "?"))
                opp_res = opp.get("resources", {})
                opp_workers = opp.get("workers_available", "?")
                opp_total_workers = opp.get("workers_total", "?")
                opp_city = opp.get("city", [])
                opp_strs.append(
                    f"{opp_name}: {_res_str(opp_res)} | "
                    f"Workers {opp_workers}/{opp_total_workers} | "
                    f"City {len(opp_city)}/{max_city}"
                )
            lines.append("OPPONENTS: " + " | ".join(opp_strs))
            lines.append("")

        # Valid actions
        actions = state.get("valid_actions", [])
        if actions:
            lines.append("VALID ACTIONS:")
            for i, a in enumerate(actions):
                lines.append(f"{i + 1}. {self._format_action(a)}")
            lines.append("")
            lines.append("Choose action number:")

        # Score
        score = state.get("score")
        if score is not None:
            lines.append(f"\nCurrent score: {score}")

        return "\n".join(lines)

    @staticmethod
    def _format_action(action: dict[str, Any] | str) -> str:
        """Format a single valid action for display."""
        if isinstance(action, str):
            return action
        action_type = action.get("action_type", action.get("type", "unknown"))

        # Normalize to uppercase for display
        display_type = action_type.upper().replace("_", " ")

        detail_parts = []
        if action.get("location_id"):
            detail_parts.append(f'at "{action["location_id"]}"')
        if action.get("card_name"):
            card = action["card_name"]
            source = action.get("source", "")
            source_hint = f" from {source}" if source else ""
            free_hint = " (free!)" if action.get("is_free") else ""
            detail_parts.append(f'"{card}"{source_hint}{free_hint}')
        if action.get("meadow_index") is not None:
            detail_parts.append(f"meadow slot {action['meadow_index'] + 1}")

        detail = " " + " ".join(detail_parts) if detail_parts else ""
        return f"{display_type}{detail}"
