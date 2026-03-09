"""Tests for the Everdell AI benchmark script."""

import asyncio
import pytest

from ed_ai.benchmark import SAMPLE_PROMPT, SYSTEM_PROMPT, benchmark_model


class TestSamplePrompt:
    """Validate the sample prompt is well-formed."""

    def test_has_valid_actions_section(self):
        assert "VALID ACTIONS:" in SAMPLE_PROMPT

    def test_has_numbered_actions(self):
        for n in range(1, 9):
            assert f"  {n}." in SAMPLE_PROMPT, f"Missing action {n}"

    def test_has_game_state_sections(self):
        for section in ["MY RESOURCES:", "MY WORKERS:", "MY CITY", "MY HAND", "MEADOW:", "OPPONENTS:"]:
            assert section in SAMPLE_PROMPT, f"Missing section: {section}"

    def test_has_season_and_turn(self):
        assert "Season:" in SAMPLE_PROMPT
        assert "Turn:" in SAMPLE_PROMPT

    def test_ends_with_action_request(self):
        assert SAMPLE_PROMPT.strip().endswith("the number):")

    def test_system_prompt_not_empty(self):
        assert len(SYSTEM_PROMPT.strip()) > 0


class TestBenchmarkModel:
    """Test benchmark_model handles errors gracefully."""

    def test_connection_refused(self):
        """benchmark_model should handle unreachable host without raising."""
        result = asyncio.run(
            benchmark_model("http://localhost:1", "fake-model", num_runs=1)
        )
        assert result['model'] == 'fake-model'
        assert result['errors'] == 1
        assert len(result['runs']) == 1
        assert 'error' in result['runs'][0]

    def test_aggregates_none_on_all_errors(self):
        """When every run errors, aggregates should be None/0."""
        result = asyncio.run(
            benchmark_model("http://localhost:1", "fake-model", num_runs=2)
        )
        assert result['avg_latency_s'] is None
        assert result['avg_tokens_per_sec'] is None
        assert result['validity_rate'] == 0
        assert result['errors'] == 2
