from __future__ import annotations

import json
import re
from typing import Any


class ResponseParser:
    """Parse Ollama text output into a structured action dict.

    Handles:
    - Raw JSON objects
    - JSON inside markdown code blocks (```json ... ```)
    - JSON inside plain code blocks (``` ... ```)
    """

    _CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)

    def parse(self, text: str) -> dict[str, Any] | None:
        """Extract the first valid JSON object from text. Returns None on failure."""
        # Try extracting from code blocks first
        for match in self._CODE_BLOCK_RE.finditer(text):
            result = self._try_parse_json(match.group(1).strip())
            if result is not None:
                return result

        # Try the whole text as JSON
        result = self._try_parse_json(text.strip())
        if result is not None:
            return result

        # Try to find a JSON object anywhere in the text
        brace_match = re.search(r"\{[^{}]*\}", text)
        if brace_match:
            result = self._try_parse_json(brace_match.group(0))
            if result is not None:
                return result

        return None

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, TypeError):
            pass
        return None
