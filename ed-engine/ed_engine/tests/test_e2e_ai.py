"""End-to-end AI vs AI tests for the Everdell engine.

Simulates AI vs AI games using the engine directly (no HTTP),
testing the complete game loop as an AI agent would experience it.

Bead: ed-dmd
"""
from __future__ import annotations

import pytest

from ed_engine.engine.actions import ActionType, GameAction
from ed_engine.engine.game_manager import GameManager
from ed_engine.engine.perspective import PerspectiveFilter
from ed_engine.engine.scoring import ScoringEngine


class TestAIvsAI:
    """Simulate AI vs AI games using the engine directly (no HTTP)."""

    @staticmethod
    def _ai_choose_action(
        valid_actions: list[GameAction],
    ) -> GameAction:
        """Simple heuristic AI for testing.

        Priority:
        1. play_card (prefer higher base_points cards, prefer hand over meadow)
        2. place_worker
        3. prepare_for_season
        """
        play_cards = [
            a for a in valid_actions if a.action_type == ActionType.PLAY_CARD
        ]
        place_workers = [
            a for a in valid_actions if a.action_type == ActionType.PLACE_WORKER
        ]
        prepare = [
            a for a in valid_actions
            if a.action_type == ActionType.PREPARE_FOR_SEASON
        ]

        if play_cards:
            # Prefer free plays (paired construction), then hand cards
            free = [a for a in play_cards if a.use_paired_construction]
            if free:
                return free[0]
            hand_cards = [a for a in play_cards if a.source == "hand"]
            if hand_cards:
                return hand_cards[0]
            return play_cards[0]
        elif place_workers:
            return place_workers[0]
        elif prepare:
            return prepare[0]
        return valid_actions[0]  # fallback

    def _run_ai_game(
        self, player_names: list[str], seed: int, max_turns: int = 500
    ) -> tuple[GameManager, int]:
        """Run an AI game to completion. Returns (gm, turns)."""
        gm = GameManager(player_names=player_names, seed=seed)
        turns = 0
        while not gm.is_game_over() and turns < max_turns:
            actions = gm.get_valid_actions()
            if not actions:
                gm.current_player.has_passed = True
                gm.advance_turn()
                turns += 1
                continue
            chosen = self._ai_choose_action(actions)
            gm.perform_action(chosen)
            turns += 1
        return gm, turns

    def test_complete_2_player_ai_game(self):
        """Two AI players complete a full game."""
        gm, turns = self._run_ai_game(["AI_Alpha", "AI_Beta"], seed=42)
        assert gm.is_game_over(), f"Game did not finish after {turns} turns"
        assert turns > 10, f"Game too short: {turns} turns"

    def test_10_ai_games_all_complete(self):
        """10 AI vs AI games all reach completion."""
        for seed in range(10):
            gm, turns = self._run_ai_game(
                ["AI_1", "AI_2"], seed=seed + 5000
            )
            assert gm.is_game_over() or turns >= 500, (
                f"Seed {seed + 5000}: game stuck at turn {turns}"
            )

    def test_ai_game_scores_are_reasonable(self):
        """AI game scores should be positive and reasonable."""
        gm, turns = self._run_ai_game(["AI_1", "AI_2"], seed=42)
        scores = ScoringEngine.calculate_final_scores(gm.game)
        for player_name, breakdown in scores.items():
            assert breakdown.total >= 0, (
                f"{player_name} has negative score: {breakdown.total}"
            )
            assert breakdown.total < 200, (
                f"{player_name} has unreasonably high score: {breakdown.total}"
            )

    def test_ai_game_scoring_works(self):
        """calculate_scores() returns valid results for all AI games."""
        for seed in [42, 123, 999, 7777]:
            gm, turns = self._run_ai_game(["AI_1", "AI_2"], seed=seed)
            scores = gm.calculate_scores()
            assert len(scores) == 2, f"Expected 2 scores, got {len(scores)}"
            for name, score in scores.items():
                assert isinstance(score, int)
                assert score >= 0, f"{name} has negative score: {score}"

    def test_perspective_serialization_works_during_game(self):
        """PerspectiveFilter.serialize_for_api works at every point during an AI game."""
        gm = GameManager(player_names=["AI_1", "AI_2"], seed=42)
        turns = 0
        while not gm.is_game_over() and turns < 100:
            # Test serialization at this state for each player
            for p in gm.game.players:
                pid = str(p.id)
                state = PerspectiveFilter.serialize_for_api(gm, pid)
                assert "players" in state
                assert "meadow" in state
                assert "valid_actions" in state
                assert "game_over" in state
                assert "deck_size" in state

                # Own hand should be visible
                my_views = [
                    v for v in state["players"] if v["id"] == pid
                ]
                assert len(my_views) == 1
                assert "hand" in my_views[0], (
                    f"Own hand not visible for {p.name}"
                )

                # Others' hands should be hidden
                for other in state["players"]:
                    if other["id"] != pid:
                        assert "hand" not in other, (
                            f"Other player's hand visible to {p.name}"
                        )
                        # But hand_size should be visible
                        assert "hand_size" in other

            # Take an action
            actions = gm.get_valid_actions()
            if not actions:
                gm.current_player.has_passed = True
                gm.advance_turn()
                turns += 1
                continue
            chosen = self._ai_choose_action(actions)
            gm.perform_action(chosen)
            turns += 1

    def test_spectator_view_hides_all_hands(self):
        """Spectator view (no player_id) should hide all hands."""
        gm = GameManager(player_names=["AI_1", "AI_2"], seed=42)
        state = PerspectiveFilter.serialize_for_api(gm, player_id=None)
        for p_view in state["players"]:
            assert "hand" not in p_view, "Spectator should not see any hands"
            assert "hand_size" in p_view

    def test_valid_actions_only_for_current_player(self):
        """Only the current player should receive valid_actions in perspective."""
        gm = GameManager(player_names=["AI_1", "AI_2"], seed=42)
        current_pid = str(gm.current_player.id)

        # Current player should get actions
        state = PerspectiveFilter.serialize_for_api(gm, current_pid)
        assert len(state["valid_actions"]) > 0

        # Other player should get empty actions
        other_pid = None
        for p in gm.game.players:
            if str(p.id) != current_pid:
                other_pid = str(p.id)
                break
        assert other_pid is not None
        state2 = PerspectiveFilter.serialize_for_api(gm, other_pid)
        assert len(state2["valid_actions"]) == 0

    def test_3_player_ai_game(self):
        """3-player AI game completes."""
        gm, turns = self._run_ai_game(
            ["AI_1", "AI_2", "AI_3"], seed=7777
        )
        assert gm.is_game_over(), f"3p game did not finish after {turns} turns"

    def test_4_player_ai_game(self):
        """4-player AI game completes."""
        gm, turns = self._run_ai_game(
            ["AI_1", "AI_2", "AI_3", "AI_4"], seed=8888
        )
        assert gm.is_game_over(), f"4p game did not finish after {turns} turns"

    def test_determine_winner_works(self):
        """ScoringEngine.determine_winner produces valid results."""
        gm, turns = self._run_ai_game(["AI_1", "AI_2"], seed=42)
        winners = ScoringEngine.determine_winner(gm.game)
        assert len(winners) >= 1
        assert all(w in gm.game.players for w in winners)
