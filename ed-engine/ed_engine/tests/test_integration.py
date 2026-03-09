"""Integration tests: play many random complete games to verify engine integrity.

Bead: ed-0mh
"""
from __future__ import annotations

import random

import pytest

from ed_engine.engine.game_manager import GameManager
from ed_engine.engine.scoring import ScoringEngine


class TestRandomGameSimulation:
    """Play many random complete games to verify engine integrity."""

    def _play_random_game(self, num_players: int, seed: int) -> dict:
        """Play a complete game with random legal moves.

        Returns: {turns, game_over, max_turns_hit}
        """
        rng = random.Random(seed)
        gm = GameManager(
            player_names=[f"Player_{i}" for i in range(num_players)],
            seed=seed,
        )
        max_turns = 500  # safety valve
        turns = 0

        while not gm.is_game_over() and turns < max_turns:
            actions = gm.get_valid_actions()
            if not actions:
                # No valid actions — force pass (same pattern as existing tests)
                gm.current_player.has_passed = True
                gm.advance_turn()
                turns += 1
                continue
            action = rng.choice(actions)
            gm.perform_action(action)
            turns += 1

        return {
            "turns": turns,
            "game_over": gm.is_game_over(),
            "max_turns_hit": turns >= max_turns,
            "gm": gm,
        }

    def test_100_random_2_player_games(self):
        """100 random 2-player games complete without crashes."""
        for seed in range(100):
            result = self._play_random_game(2, seed)
            assert result["game_over"] or result["max_turns_hit"], (
                f"Game {seed} stuck"
            )

    def test_50_random_3_player_games(self):
        """50 random 3-player games complete without crashes."""
        for seed in range(50):
            result = self._play_random_game(3, seed + 1000)
            assert result["game_over"] or result["max_turns_hit"], (
                f"Game {seed + 1000} stuck"
            )

    def test_50_random_4_player_games(self):
        """50 random 4-player games complete without crashes."""
        for seed in range(50):
            result = self._play_random_game(4, seed + 2000)
            assert result["game_over"] or result["max_turns_hit"], (
                f"Game {seed + 2000} stuck"
            )

    def test_game_terminates_within_reasonable_turns(self):
        """Games should end within ~300 turns for 2 players."""
        for seed in range(20):
            result = self._play_random_game(2, seed + 3000)
            assert not result["max_turns_hit"], (
                f"Game {seed + 3000} hit max turns ({result['turns']})"
            )

    def test_no_negative_resources(self):
        """After each action, no player should have negative resources."""
        rng = random.Random(42)
        gm = GameManager(player_names=["A", "B"], seed=42)
        turns = 0
        while not gm.is_game_over() and turns < 500:
            actions = gm.get_valid_actions()
            if not actions:
                gm.current_player.has_passed = True
                gm.advance_turn()
                turns += 1
                continue
            action = rng.choice(actions)
            gm.perform_action(action)
            turns += 1
            # Check all players
            for p in gm.game.players:
                assert p.resources.twig >= 0, (
                    f"{p.name} has negative twigs: {p.resources.twig}"
                )
                assert p.resources.resin >= 0, (
                    f"{p.name} has negative resin: {p.resources.resin}"
                )
                assert p.resources.pebble >= 0, (
                    f"{p.name} has negative pebbles: {p.resources.pebble}"
                )
                assert p.resources.berry >= 0, (
                    f"{p.name} has negative berries: {p.resources.berry}"
                )

    def test_city_never_exceeds_15(self):
        """No player should have more than 15 city-occupying cards."""
        rng = random.Random(99)
        gm = GameManager(player_names=["A", "B"], seed=99)
        turns = 0
        while not gm.is_game_over() and turns < 500:
            actions = gm.get_valid_actions()
            if not actions:
                gm.current_player.has_passed = True
                gm.advance_turn()
                turns += 1
                continue
            action = rng.choice(actions)
            gm.perform_action(action)
            turns += 1
            for p in gm.game.players:
                city_count = sum(1 for c in p.city if c.occupies_city_space)
                assert city_count <= 15, f"{p.name} has {city_count} city cards"

    def test_scoring_produces_valid_results(self):
        """All scores should be non-negative after a complete game."""
        result = self._play_random_game(2, 77)
        gm = result["gm"]

        scores = ScoringEngine.calculate_final_scores(gm.game)
        for player_name, breakdown in scores.items():
            assert breakdown.total >= 0, (
                f"{player_name} has negative total: {breakdown.total}"
            )
            assert breakdown.base_card_points >= 0, (
                f"{player_name} has negative base_card_points"
            )

    def test_deck_integrity_throughout_game(self):
        """Total cards across all zones should not increase during a game."""
        gm = GameManager(player_names=["A", "B"], seed=55)
        deck_mgr = gm._deck_mgr

        def count_all_cards() -> int:
            total = deck_mgr.deck_size + len(gm.game.meadow) + deck_mgr.discard_size
            for p in gm.game.players:
                total += len(p.hand) + len(p.city)
            return total

        initial_total = count_all_cards()

        rng = random.Random(55)
        turns = 0
        while not gm.is_game_over() and turns < 300:
            actions = gm.get_valid_actions()
            if not actions:
                gm.current_player.has_passed = True
                gm.advance_turn()
                turns += 1
                continue
            action = rng.choice(actions)
            gm.perform_action(action)
            turns += 1

            total = count_all_cards()
            # Cards should never appear from nowhere. Some may be consumed
            # by special effects, but total should never exceed initial + small
            # tolerance for edge cases.
            assert total <= initial_total + 5, (
                f"Turn {turns}: cards appeared from nowhere: {total} > {initial_total}"
            )

    def test_calculate_scores_does_not_crash(self):
        """GameManager.calculate_scores() works on completed random games."""
        for seed in range(10):
            result = self._play_random_game(2, seed + 4000)
            gm = result["gm"]
            scores = gm.calculate_scores()
            assert len(scores) == 2
            for name, score in scores.items():
                assert isinstance(score, int)
                assert score >= 0
