"""Move evaluation logic for Everdell AI."""

from __future__ import annotations

import json
import logging
from typing import Any

from ed_ai.ollama_client import OllamaClient

logger = logging.getLogger("ed_ai.evaluator")

# Quality ratings ordered from best to worst
QUALITY_RATINGS = ("brilliant", "good", "inaccuracy", "mistake", "blunder")

QUALITY_SCORES: dict[str, float] = {
    "brilliant": 1.0,
    "good": 0.75,
    "inaccuracy": 0.5,
    "mistake": 0.25,
    "blunder": 0.0,
}

_EVAL_SYSTEM_PROMPT = """\
You are an expert Everdell game analyst. Evaluate the quality of a player's move.

Rate the move using chess-style quality labels:
- brilliant: exceptional move that gains significant advantage
- good: solid move, reasonable in context
- inaccuracy: slightly suboptimal, a better move existed
- mistake: clearly worse than available alternatives
- blunder: terrible move, wastes resources or misses an obvious play

Respond ONLY with valid JSON (no markdown fences):
{
  "quality": "<brilliant|good|inaccuracy|mistake|blunder>",
  "alternatives": [
    {"action_index": <1-based index from valid_actions>, "reason": "<brief reason>"}
  ],
  "explanation": "<1-2 sentence explanation>"
}

Include 2-3 alternatives if the move is suboptimal, or 0-1 if it was good/brilliant.
The action_index refers to the position in the valid_actions list (1-based).
"""


def _build_eval_prompt(
    game_state: dict[str, Any] | str,
    action_taken: dict[str, Any],
    valid_actions: list[dict[str, Any]],
    difficulty: str,
) -> str:
    """Build the user prompt for move evaluation."""
    state_str = game_state if isinstance(game_state, str) else json.dumps(game_state, indent=2, default=str)
    lines = [
        f"Difficulty level: {difficulty}",
        "",
        state_str,
        "",
        "ACTION TAKEN BY PLAYER:",
        json.dumps(action_taken, indent=2),
        "",
        "ALL VALID ACTIONS WERE:",
    ]
    for i, action in enumerate(valid_actions, 1):
        lines.append(f"  {i}. {json.dumps(action)}")
    lines.append("")
    lines.append("Evaluate the action taken. Respond with JSON only.")
    return "\n".join(lines)


def _parse_eval_response(
    raw: str,
    valid_actions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Parse the LLM evaluation response into a structured dict."""
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    quality = data.get("quality", "").lower().strip()
    if quality not in QUALITY_SCORES:
        return None

    # Build alternatives with resolved action dicts
    alternatives: list[dict[str, Any]] = []
    for alt in data.get("alternatives", [])[:3]:
        idx = alt.get("action_index")
        reason = alt.get("reason", "")
        if isinstance(idx, int) and 1 <= idx <= len(valid_actions):
            alternatives.append({
                "action": valid_actions[idx - 1],
                "reason": reason,
                "score_delta": 0,
            })

    return {
        "quality": quality,
        "score": QUALITY_SCORES[quality],
        "alternatives": alternatives,
        "explanation": data.get("explanation", ""),
    }


def heuristic_evaluate(
    action_taken: dict[str, Any],
    valid_actions: list[dict[str, Any]],
    game_state: dict[str, Any] | str,
) -> dict[str, Any]:
    """Fallback heuristic evaluation when Ollama is unavailable."""
    action_type = action_taken.get("action_type", action_taken.get("type", ""))

    # Check for prepare_for_season when resources are low
    if action_type == "prepare_for_season":
        # See if there were card-play options available (meaning prepare was premature)
        has_card_plays = any(
            a.get("action_type", a.get("type", "")) == "play_card"
            for a in valid_actions
        )
        if has_card_plays:
            card_alts = [
                a for a in valid_actions
                if a.get("action_type", a.get("type", "")) == "play_card"
            ][:2]
            return {
                "quality": "inaccuracy",
                "score": QUALITY_SCORES["inaccuracy"],
                "alternatives": [
                    {"action": a, "reason": "Playing a card builds your city", "score_delta": 0}
                    for a in card_alts
                ],
                "explanation": (
                    "Preparing for season when card plays were available "
                    "may waste tempo."
                ),
            }
        return {
            "quality": "good",
            "score": QUALITY_SCORES["good"],
            "alternatives": [],
            "explanation": "No better options available; preparing for season is reasonable.",
        }

    # Playing a high-point card is generally good
    if action_type == "play_card":
        points = action_taken.get("base_points", action_taken.get("points", 0)) or 0
        if points >= 3:
            return {
                "quality": "good",
                "score": QUALITY_SCORES["good"],
                "alternatives": [],
                "explanation": f"Playing a {points}-point card is a solid move.",
            }

    # Only one valid action means any choice is fine
    if len(valid_actions) <= 1:
        return {
            "quality": "good",
            "score": QUALITY_SCORES["good"],
            "alternatives": [],
            "explanation": "Only move available.",
        }

    # Default fallback
    return {
        "quality": "inaccuracy",
        "score": QUALITY_SCORES["inaccuracy"],
        "alternatives": [
            {"action": valid_actions[0], "reason": "Consider this alternative", "score_delta": 0}
        ] if valid_actions else [],
        "explanation": "Move quality unclear without deeper analysis.",
    }


async def evaluate_move(
    ollama: OllamaClient,
    game_state: dict[str, Any] | str,
    action_taken: dict[str, Any],
    valid_actions: list[dict[str, Any]],
    difficulty: str = "journeyman",
) -> dict[str, Any]:
    """Evaluate a move using Ollama with heuristic fallback.

    Returns:
        dict with keys: quality, score, alternatives, explanation
    """
    ollama_available = await ollama.is_available()
    if ollama_available:
        prompt = _build_eval_prompt(game_state, action_taken, valid_actions, difficulty)
        try:
            raw = await ollama.generate(prompt=prompt, system=_EVAL_SYSTEM_PROMPT)
            result = _parse_eval_response(raw, valid_actions)
            if result is not None:
                logger.info("Ollama evaluation: %s (score=%.2f)", result["quality"], result["score"])
                return result
            logger.warning("Failed to parse Ollama evaluation response")
        except Exception as exc:
            logger.warning("Ollama evaluation failed: %s", exc)

    logger.info("Using heuristic evaluation fallback")
    return heuristic_evaluate(action_taken, valid_actions, game_state)
