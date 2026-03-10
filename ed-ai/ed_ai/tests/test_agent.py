"""Tests for AIPlayer heuristic fallback logic."""

from __future__ import annotations

import pytest

from ed_ai.agent import AIPlayer


@pytest.fixture
def player() -> AIPlayer:
    return AIPlayer(
        game_id="test-game",
        player_token="test-token",
        player_id="test-player",
        difficulty="journeyman",
        engine_url="http://localhost:4242",
    )


SAMPLE_ACTIONS_MIXED = [
    {"action_type": "place_worker", "location_id": "3 Twigs"},
    {"action_type": "play_card", "card_name": "Farm", "base_points": 1, "card_type": "production"},
    {"action_type": "play_card", "card_name": "Castle", "base_points": 4, "card_type": "prosperity"},
    {"action_type": "prepare_for_season"},
]

SAMPLE_ACTIONS_WORKERS_ONLY = [
    {"action_type": "place_worker", "location_id": "3 Twigs"},
    {"action_type": "place_worker", "location_id": "2 Resin"},
    {"action_type": "prepare_for_season"},
]

SAMPLE_ACTIONS_PREPARE_ONLY = [
    {"action_type": "prepare_for_season"},
]


class TestHeuristicFallback:
    def test_prefers_play_card_over_place_worker(self, player: AIPlayer) -> None:
        action = player.heuristic_fallback(SAMPLE_ACTIONS_MIXED, {"season": "spring"})
        assert action["action_type"] == "play_card"

    def test_prefers_production_early_game(self, player: AIPlayer) -> None:
        """In spring, production cards should score higher than prosperity."""
        action = player.heuristic_fallback(SAMPLE_ACTIONS_MIXED, {"season": "spring"})
        assert action["action_type"] == "play_card"
        # Farm (1pt + 3 production bonus) should beat Castle (4pt + 0 bonus) in spring
        assert action["card_name"] == "Farm"

    def test_prefers_prosperity_late_game(self, player: AIPlayer) -> None:
        """In autumn, prosperity cards should score higher."""
        action = player.heuristic_fallback(SAMPLE_ACTIONS_MIXED, {"season": "autumn"})
        assert action["action_type"] == "play_card"
        # Castle (4pt + 3 prosperity bonus) should beat Farm (1pt + 0 bonus) in autumn
        assert action["card_name"] == "Castle"

    def test_prefers_free_plays(self, player: AIPlayer) -> None:
        actions = [
            {"action_type": "play_card", "card_name": "Harvester", "base_points": 2, "is_free": True},
            {"action_type": "play_card", "card_name": "Castle", "base_points": 4},
        ]
        action = player.heuristic_fallback(actions, {"season": "spring"})
        # Free Harvester (2pt + 10 free bonus) beats Castle (4pt)
        assert action["card_name"] == "Harvester"

    def test_falls_back_to_place_worker(self, player: AIPlayer) -> None:
        action = player.heuristic_fallback(SAMPLE_ACTIONS_WORKERS_ONLY, {"season": "spring"})
        assert action["action_type"] == "place_worker"

    def test_prepare_as_last_resort(self, player: AIPlayer) -> None:
        action = player.heuristic_fallback(SAMPLE_ACTIONS_PREPARE_ONLY, {"season": "spring"})
        assert action["action_type"] == "prepare_for_season"

    def test_empty_actions_returns_prepare(self, player: AIPlayer) -> None:
        action = player.heuristic_fallback([], None)
        assert action["action_type"] == "prepare_for_season"

    def test_none_state_uses_spring_default(self, player: AIPlayer) -> None:
        """Should not crash when state is None."""
        action = player.heuristic_fallback(SAMPLE_ACTIONS_MIXED, None)
        assert action["action_type"] == "play_card"


class TestActionValidation:
    def test_exact_match(self, player: AIPlayer) -> None:
        action = {"action_type": "play_card", "card_name": "Farm"}
        valid = [
            {"action_type": "play_card", "card_name": "Farm"},
            {"action_type": "place_worker", "location_id": "3 Twigs"},
        ]
        assert player._is_valid(action, valid) is True

    def test_type_only_match(self, player: AIPlayer) -> None:
        action = {"action_type": "prepare_for_season"}
        valid = [{"action_type": "prepare_for_season"}]
        assert player._is_valid(action, valid) is True

    def test_no_match(self, player: AIPlayer) -> None:
        action = {"action_type": "play_card", "card_name": "Castle"}
        valid = [
            {"action_type": "play_card", "card_name": "Farm"},
        ]
        assert player._is_valid(action, valid) is False

    def test_empty_valid_actions(self, player: AIPlayer) -> None:
        action = {"action_type": "play_card", "card_name": "Farm"}
        assert player._is_valid(action, []) is False

    def test_missing_action_type(self, player: AIPlayer) -> None:
        action = {"card_name": "Farm"}
        valid = [{"action_type": "play_card", "card_name": "Farm"}]
        assert player._is_valid(action, valid) is False
