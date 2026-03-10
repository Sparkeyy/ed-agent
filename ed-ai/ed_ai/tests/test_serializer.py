"""Tests for GameStateSerializer compact output format."""

from __future__ import annotations

import pytest

from ed_ai.prompts.serializer import GameStateSerializer


@pytest.fixture
def serializer() -> GameStateSerializer:
    return GameStateSerializer()


FULL_STATE = {
    "season": "Spring",
    "turn_number": 5,
    "player_name": "AI Bob",
    "resources": {"twig": 3, "resin": 2, "pebble": 1, "berry": 4},
    "workers_available": 2,
    "workers_total": 4,
    "city": [
        {"name": "Farm", "base_points": 1},
        {"name": "Twig Barge", "base_points": 1},
        {"name": "Chapel", "base_points": 2},
    ],
    "hand": [
        {"name": "Castle", "base_points": 4, "cost_twig": 2, "cost_resin": 3, "cost_pebble": 3},
        {"name": "Bard", "base_points": 0, "cost_berry": 3},
    ],
    "meadow": [
        {"name": "Farm"},
        {"name": "Inn"},
        {"name": "Queen"},
    ],
    "opponents": [
        {
            "name": "Alice",
            "resources": {"twig": 4, "resin": 1, "pebble": 0, "berry": 2},
            "workers_available": 1,
            "workers_total": 3,
            "city": [{"name": "Mine"}, {"name": "Resin Refinery"}, {"name": "Crane"}, {"name": "Bard"}],
        },
    ],
    "valid_actions": [
        {"action_type": "place_worker", "location_id": "3 Twigs"},
        {"action_type": "play_card", "card_name": "Harvester", "source": "hand", "is_free": True},
        {"action_type": "prepare_for_season"},
    ],
    "score": 12,
}


class TestSerializerOutput:
    def test_header(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "=== EVERDELL - YOUR TURN ===" in output
        assert "Spring" in output
        assert "Turn: 5" in output
        assert '"AI Bob"' in output

    def test_resources(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "MY RESOURCES:" in output
        # Check emoji resource format
        assert "3\U0001fab5" in output  # 3 twig
        assert "2\U0001f4a7" in output  # 2 resin
        assert "1\U0001faa8" in output  # 1 pebble
        assert "4\U0001fad0" in output  # 4 berry

    def test_workers(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "MY WORKERS: 2/4 available" in output

    def test_city(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "MY CITY (3/15):" in output
        assert "Farm" in output
        assert "Twig Barge" in output
        assert "Chapel" in output

    def test_hand(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "MY HAND (2):" in output
        assert "[1]" in output
        assert "Castle" in output
        assert "[2]" in output
        assert "Bard" in output

    def test_meadow(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "MEADOW:" in output
        assert "[1]" in output
        assert "Inn" in output
        assert "Queen" in output

    def test_opponents(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "OPPONENTS:" in output
        assert "Alice" in output
        assert "Workers 1/3" in output
        assert "City 4/15" in output

    def test_valid_actions(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "VALID ACTIONS:" in output
        assert "PLACE WORKER" in output
        assert '"3 Twigs"' in output
        assert "PLAY CARD" in output
        assert '"Harvester"' in output
        assert "(free!)" in output
        assert "PREPARE FOR SEASON" in output

    def test_score(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "Current score: 12" in output

    def test_choose_prompt(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize(FULL_STATE)
        assert "Choose action number:" in output


class TestSerializerEdgeCases:
    def test_empty_state(self, serializer: GameStateSerializer) -> None:
        output = serializer.serialize({})
        assert "=== EVERDELL" in output
        assert "MY CITY (0/15): empty" in output
        assert "MY HAND: empty" in output

    def test_string_cards(self, serializer: GameStateSerializer) -> None:
        """Cards can be plain strings instead of dicts."""
        state = {"hand": ["Farm", "Inn"], "city": ["Crane"]}
        output = serializer.serialize(state)
        assert "Farm" in output
        assert "Inn" in output
        assert "Crane" in output

    def test_no_valid_actions(self, serializer: GameStateSerializer) -> None:
        state = {"season": "Winter"}
        output = serializer.serialize(state)
        assert "VALID ACTIONS:" not in output
        assert "Choose action number:" not in output

    def test_no_opponents(self, serializer: GameStateSerializer) -> None:
        state = {"season": "Spring"}
        output = serializer.serialize(state)
        assert "OPPONENTS:" not in output
