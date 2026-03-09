from __future__ import annotations

import random
from typing import Any

from ed_ai.ollama_client import OllamaClient
from ed_ai.parser import ResponseParser
from ed_ai.prompts.personas import get_system_prompt
from ed_ai.prompts.serializer import GameStateSerializer


class AIAgent:
    """AI opponent that uses Ollama to choose Everdell actions."""

    MAX_RETRIES = 3
    MODEL = "qwen2.5-coder:7b"

    def __init__(self, ollama_url: str = "http://localhost:11434") -> None:
        self.client = OllamaClient(base_url=ollama_url)
        self.parser = ResponseParser()
        self.serializer = GameStateSerializer()

    async def think(
        self, game_state: dict[str, Any], *, persona: str = "journeyman"
    ) -> dict[str, Any]:
        """Given a game state, return a chosen action dict.

        Reasoning loop: serialize -> prompt Ollama -> parse -> validate.
        Retries up to MAX_RETRIES, then falls back to a random legal action.
        """
        system_prompt = get_system_prompt(persona)
        user_prompt = self.serializer.serialize(game_state)

        last_error = ""
        for attempt in range(self.MAX_RETRIES):
            retry_hint = f"\n\nPrevious attempt failed: {last_error}" if last_error else ""
            raw = await self.client.generate(
                model=self.MODEL,
                prompt=user_prompt + retry_hint,
                system=system_prompt,
            )
            action = self.parser.parse(raw)
            if action is not None and self._validate(action, game_state):
                return {"action": action, "reasoning": raw, "retries": attempt}
            last_error = "could not parse valid action from response"

        # Fallback: pick a random legal action
        action = self._random_legal_action(game_state)
        return {"action": action, "reasoning": "fallback: random legal action", "retries": self.MAX_RETRIES}

    async def evaluate(
        self, game_state: dict[str, Any], action: dict[str, Any]
    ) -> dict[str, Any]:
        """Evaluate the quality of an action given a game state."""
        prompt = (
            f"Rate this Everdell action from 0.0 (terrible) to 1.0 (optimal).\n"
            f"State:\n{self.serializer.serialize(game_state)}\n"
            f"Action: {action}\n"
            f"Reply with JSON: {{\"quality\": <float>, \"explanation\": \"<text>\"}}"
        )
        raw = await self.client.generate(
            model=self.MODEL, prompt=prompt, system="You are an Everdell expert."
        )
        parsed = self.parser.parse(raw)
        if parsed and "quality" in parsed:
            return {
                "quality": max(0.0, min(1.0, float(parsed["quality"]))),
                "explanation": parsed.get("explanation", ""),
            }
        return {"quality": 0.5, "explanation": "could not evaluate"}

    def _validate(self, action: dict[str, Any], game_state: dict[str, Any]) -> bool:
        """Check that the action is in the valid_actions list, if provided."""
        valid = game_state.get("valid_actions")
        if valid is None:
            return True  # No validation info available
        # Simple membership check by action type
        action_type = action.get("type")
        return any(va.get("type") == action_type for va in valid)

    @staticmethod
    def _random_legal_action(game_state: dict[str, Any]) -> dict[str, Any]:
        """Pick a random action from valid_actions, or a pass action."""
        valid = game_state.get("valid_actions", [])
        if valid:
            return random.choice(valid)
        return {"type": "pass"}
