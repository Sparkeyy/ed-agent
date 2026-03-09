"""Serialize game state dict into a compact text prompt (<2K tokens)."""

from __future__ import annotations

from typing import Any


class GameStateSerializer:
    """Convert an Everdell game state dict into a compact text prompt."""

    def serialize(self, state: dict[str, Any]) -> str:
        sections: list[str] = []

        sections.append(f"Season: {state.get('season', '?')}")
        sections.append(f"Workers available: {state.get('workers_available', '?')}")

        # My resources
        res = state.get("resources", {})
        if res:
            parts = [f"{k}: {v}" for k, v in res.items()]
            sections.append(f"Resources: {', '.join(parts)}")

        # My city
        city = state.get("city", [])
        if city:
            names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in city]
            sections.append(f"City ({len(names)}): {', '.join(names)}")
        else:
            sections.append("City: empty")

        # Hand
        hand = state.get("hand", [])
        if hand:
            names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in hand]
            sections.append(f"Hand ({len(names)}): {', '.join(names)}")

        # Meadow
        meadow = state.get("meadow", [])
        if meadow:
            names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in meadow]
            sections.append(f"Meadow: {', '.join(names)}")

        # Valid actions
        actions = state.get("valid_actions", [])
        if actions:
            lines = []
            for i, a in enumerate(actions):
                if isinstance(a, dict):
                    desc = a.get("type", "unknown")
                    detail = {k: v for k, v in a.items() if k != "type"}
                    if detail:
                        desc += f" {detail}"
                    lines.append(f"  {i + 1}. {desc}")
                else:
                    lines.append(f"  {i + 1}. {a}")
            sections.append("Valid actions:\n" + "\n".join(lines))

        # Score
        score = state.get("score")
        if score is not None:
            sections.append(f"Current score: {score}")

        return "\n".join(sections)
