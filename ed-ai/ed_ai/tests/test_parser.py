from __future__ import annotations

import pytest

from ed_ai.parser import ResponseParser


@pytest.fixture
def parser() -> ResponseParser:
    return ResponseParser()


SAMPLE_VALID_ACTIONS = [
    {"action_type": "place_worker", "location_id": "3 Twigs"},
    {"action_type": "play_card", "card_name": "Harvester", "source": "hand", "is_free": True},
    {"action_type": "play_card", "card_name": "Bard", "source": "hand"},
    {"action_type": "prepare_for_season"},
]


class TestParseValidJSON:
    def test_plain_json(self, parser: ResponseParser) -> None:
        text = '{"action_type": "place_worker", "location_id": "farm"}'
        result = parser.parse(text)
        assert result == {"action_type": "place_worker", "location_id": "farm"}

    def test_json_with_surrounding_text(self, parser: ResponseParser) -> None:
        text = 'I think you should do this: {"action_type": "play_card", "card_name": "Bard"} because reasons.'
        result = parser.parse(text)
        assert result is not None
        assert result["action_type"] == "play_card"
        assert result["card_name"] == "Bard"


class TestParseCodeBlock:
    def test_json_code_block(self, parser: ResponseParser) -> None:
        text = 'Here is my action:\n```json\n{"action_type": "prepare_for_season"}\n```\nGood luck!'
        result = parser.parse(text)
        assert result == {"action_type": "prepare_for_season"}

    def test_plain_code_block(self, parser: ResponseParser) -> None:
        text = '```\n{"action_type": "prepare_for_season"}\n```'
        result = parser.parse(text)
        assert result == {"action_type": "prepare_for_season"}


class TestParseNumberedChoice:
    def test_choose_number(self, parser: ResponseParser) -> None:
        result = parser.parse("I choose 2", valid_actions=SAMPLE_VALID_ACTIONS)
        assert result == SAMPLE_VALID_ACTIONS[1]

    def test_pick_number(self, parser: ResponseParser) -> None:
        result = parser.parse("I pick action 4", valid_actions=SAMPLE_VALID_ACTIONS)
        assert result == SAMPLE_VALID_ACTIONS[3]

    def test_select_number(self, parser: ResponseParser) -> None:
        result = parser.parse("select 1", valid_actions=SAMPLE_VALID_ACTIONS)
        assert result == SAMPLE_VALID_ACTIONS[0]

    def test_bare_number(self, parser: ResponseParser) -> None:
        result = parser.parse("3", valid_actions=SAMPLE_VALID_ACTIONS)
        assert result == SAMPLE_VALID_ACTIONS[2]

    def test_number_out_of_range(self, parser: ResponseParser) -> None:
        result = parser.parse("I choose 99", valid_actions=SAMPLE_VALID_ACTIONS)
        assert result is None

    def test_no_valid_actions_ignores_number(self, parser: ResponseParser) -> None:
        # Without valid_actions, numbered choice is not attempted
        result = parser.parse("I choose 2")
        assert result is None


class TestParseKeywordMatch:
    def test_play_card_keyword(self, parser: ResponseParser) -> None:
        result = parser.parse(
            "I want to play card Harvester from hand",
            valid_actions=SAMPLE_VALID_ACTIONS,
        )
        assert result is not None
        assert result["card_name"] == "Harvester"

    def test_place_worker_keyword(self, parser: ResponseParser) -> None:
        result = parser.parse(
            "Let me place worker at 3 Twigs",
            valid_actions=SAMPLE_VALID_ACTIONS,
        )
        assert result is not None
        assert result["location_id"] == "3 Twigs"

    def test_prepare_keyword(self, parser: ResponseParser) -> None:
        result = parser.parse(
            "I'll prepare for season",
            valid_actions=SAMPLE_VALID_ACTIONS,
        )
        assert result is not None
        assert result["action_type"] == "prepare_for_season"


class TestParseMalformed:
    def test_empty_string(self, parser: ResponseParser) -> None:
        assert parser.parse("") is None

    def test_no_json(self, parser: ResponseParser) -> None:
        assert parser.parse("I have no idea what to do.") is None

    def test_invalid_json(self, parser: ResponseParser) -> None:
        assert parser.parse("{not valid json}") is None

    def test_json_array_ignored(self, parser: ResponseParser) -> None:
        assert parser.parse("[1, 2, 3]") is None

    def test_nested_braces_falls_back(self, parser: ResponseParser) -> None:
        text = 'some text {"action_type": "draw"} more text'
        result = parser.parse(text)
        assert result is not None
        assert result["action_type"] == "draw"


class TestParseJSONPreference:
    """JSON should take priority over numbered choice."""

    def test_json_beats_number(self, parser: ResponseParser) -> None:
        text = 'I choose 1\n```json\n{"action_type": "play_card", "card_name": "Bard"}\n```'
        result = parser.parse(text, valid_actions=SAMPLE_VALID_ACTIONS)
        # JSON should win since code blocks are tried first
        assert result is not None
        assert result["card_name"] == "Bard"
