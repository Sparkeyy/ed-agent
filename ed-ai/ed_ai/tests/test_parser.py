from __future__ import annotations

import pytest

from ed_ai.parser import ResponseParser


@pytest.fixture
def parser() -> ResponseParser:
    return ResponseParser()


class TestParseValidJSON:
    def test_plain_json(self, parser: ResponseParser) -> None:
        text = '{"type": "place_worker", "location": "farm"}'
        result = parser.parse(text)
        assert result == {"type": "place_worker", "location": "farm"}

    def test_json_with_surrounding_text(self, parser: ResponseParser) -> None:
        text = 'I think you should do this: {"type": "play_card", "card": "Bard"} because reasons.'
        result = parser.parse(text)
        assert result is not None
        assert result["type"] == "play_card"
        assert result["card"] == "Bard"


class TestParseCodeBlock:
    def test_json_code_block(self, parser: ResponseParser) -> None:
        text = 'Here is my action:\n```json\n{"type": "pass"}\n```\nGood luck!'
        result = parser.parse(text)
        assert result == {"type": "pass"}

    def test_plain_code_block(self, parser: ResponseParser) -> None:
        text = '```\n{"type": "prepare_for_season"}\n```'
        result = parser.parse(text)
        assert result == {"type": "prepare_for_season"}


class TestParseMalformed:
    def test_empty_string(self, parser: ResponseParser) -> None:
        assert parser.parse("") is None

    def test_no_json(self, parser: ResponseParser) -> None:
        assert parser.parse("I have no idea what to do.") is None

    def test_invalid_json(self, parser: ResponseParser) -> None:
        assert parser.parse("{not valid json}") is None

    def test_json_array_ignored(self, parser: ResponseParser) -> None:
        # Arrays are not valid actions
        assert parser.parse('[1, 2, 3]') is None

    def test_nested_braces_falls_back(self, parser: ResponseParser) -> None:
        # Only outermost simple object is matched by fallback regex
        text = 'some text {"type": "draw"} more text'
        result = parser.parse(text)
        assert result is not None
        assert result["type"] == "draw"
