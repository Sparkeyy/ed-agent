"""Parse LLM text output into structured Everdell actions."""

from __future__ import annotations

import json
import re
from typing import Any


class ResponseParser:
    """Parse Ollama text output into a structured action dict.

    Extraction strategies (tried in order):
    1. JSON block in markdown code fence
    2. Raw JSON object in text
    3. Numbered choice referencing valid_actions list ("I choose 3")
    4. Action keyword + card/location name matching
    5. Return None if unparseable
    """

    _CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
    _CHOICE_RE = re.compile(
        r"(?:I\s+)?(?:choose|pick|select|go\s+with)\s+(?:action\s+)?#?(\d+)",
        re.IGNORECASE,
    )
    _JUST_NUMBER_RE = re.compile(r"^\s*(\d+)\s*$")
    _ACTION_KEYWORDS = {
        "place_worker": ["place_worker", "place worker", "deploy worker"],
        "play_card": ["play_card", "play card", "play"],
        "prepare_for_season": ["prepare_for_season", "prepare for season", "prepare"],
    }

    def parse(
        self, text: str, valid_actions: list[dict[str, Any]] | None = None
    ) -> dict[str, Any] | None:
        """Extract the first valid action from LLM text output.

        Args:
            text: Raw LLM response text.
            valid_actions: Optional list of valid actions for numbered choice matching.

        Returns:
            Parsed action dict or None if unparseable.
        """
        if not text:
            return None

        # Strategy 1: JSON in code blocks
        for match in self._CODE_BLOCK_RE.finditer(text):
            result = self._try_parse_json(match.group(1).strip())
            if result is not None:
                return result

        # Strategy 2: Whole text as JSON or embedded JSON object
        result = self._try_parse_json(text.strip())
        if result is not None:
            return result

        brace_match = re.search(r"\{[^{}]*\}", text)
        if brace_match:
            result = self._try_parse_json(brace_match.group(0))
            if result is not None:
                return result

        # Strategy 3: Numbered choice ("I choose 3" -> valid_actions[2])
        if valid_actions:
            action = self._try_numbered_choice(text, valid_actions)
            if action is not None:
                return action

        # Strategy 4: Action keywords + card/location names
        if valid_actions:
            action = self._try_keyword_match(text, valid_actions)
            if action is not None:
                return action

        return None

    def _try_numbered_choice(
        self, text: str, valid_actions: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Try to extract a numbered choice from the text."""
        # Try explicit "I choose N" patterns
        match = self._CHOICE_RE.search(text)
        if match:
            return self._get_action_by_number(int(match.group(1)), valid_actions)

        # Try bare number
        match = self._JUST_NUMBER_RE.match(text.strip())
        if match:
            return self._get_action_by_number(int(match.group(1)), valid_actions)

        return None

    @staticmethod
    def _get_action_by_number(
        num: int, valid_actions: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Convert 1-based action number to valid action."""
        if 1 <= num <= len(valid_actions):
            return valid_actions[num - 1]
        return None

    def _try_keyword_match(
        self, text: str, valid_actions: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Try to match action type keywords + card/location names."""
        text_lower = text.lower()

        # Find which action type is mentioned
        matched_type = None
        for action_type, keywords in self._ACTION_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    matched_type = action_type
                    break
            if matched_type:
                break

        if not matched_type:
            return None

        # Filter valid actions to matching type
        candidates = [
            a for a in valid_actions
            if a.get("action_type") == matched_type or a.get("type") == matched_type
        ]
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        # Try to match by card_name or location_id
        for action in candidates:
            for field in ("card_name", "location_id", "card", "location"):
                name = action.get(field, "")
                if name and name.lower() in text_lower:
                    return action

        # Return first matching type candidate as fallback
        return candidates[0]

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, TypeError):
            pass
        return None
