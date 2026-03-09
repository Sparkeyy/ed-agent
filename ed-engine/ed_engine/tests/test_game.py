"""Tests for the Season/Turn State Machine (GameManager, SeasonManager, ActionHandler)."""
from __future__ import annotations

import random

import pytest

from ed_engine.engine.actions import ActionHandler, ActionType, GameAction
from ed_engine.engine.deck import DeckManager
from ed_engine.engine.game_manager import GameManager
from ed_engine.engine.locations import LocationManager
from ed_engine.engine.seasons import SeasonManager
from ed_engine.models.card import Card
from ed_engine.models.enums import CardCategory, CardType, Season
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(name: str = "Alice", **overrides) -> Player:
    defaults = {"name": name}
    defaults.update(overrides)
    return Player(**defaults)


def _make_card(name: str = "TestCard", **overrides) -> Card:
    defaults = {
        "name": name,
        "card_type": CardType.TAN_TRAVELER,
        "category": CardCategory.CRITTER,
        "base_points": 1,
    }
    defaults.update(overrides)
    return Card(**defaults)


def _make_cards(n: int) -> list[Card]:
    return [
        Card(
            name=f"Card_{i}",
            card_type=CardType.TAN_TRAVELER,
            category=CardCategory.CRITTER,
            base_points=1,
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Game Creation Tests
# ---------------------------------------------------------------------------


class TestGameCreation:
    def test_create_1_player(self) -> None:
        gm = GameManager(["Alice"], seed=42)
        assert len(gm.game.players) == 1
        assert gm.game.players[0].name == "Alice"

    def test_create_2_players(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        assert len(gm.game.players) == 2

    def test_create_3_players(self) -> None:
        gm = GameManager(["Alice", "Bob", "Charlie"], seed=42)
        assert len(gm.game.players) == 3

    def test_create_4_players(self) -> None:
        gm = GameManager(["Alice", "Bob", "Charlie", "Diana"], seed=42)
        assert len(gm.game.players) == 4

    def test_create_0_players_raises(self) -> None:
        with pytest.raises(ValueError, match="1-4 players"):
            GameManager([], seed=42)

    def test_create_5_players_raises(self) -> None:
        with pytest.raises(ValueError, match="1-4 players"):
            GameManager(["A", "B", "C", "D", "E"], seed=42)

    def test_starting_season_is_winter(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        for p in gm.game.players:
            assert p.season == Season.WINTER

    def test_starting_workers_is_2(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        for p in gm.game.players:
            assert p.workers_total == 2
            assert p.workers_placed == 0

    def test_starting_hands_vary_by_player_order(self) -> None:
        gm = GameManager(["Alice", "Bob", "Charlie", "Diana"], seed=42)
        assert len(gm.game.players[0].hand) == 5  # 1st player
        assert len(gm.game.players[1].hand) == 6  # 2nd player
        assert len(gm.game.players[2].hand) == 7  # 3rd player
        assert len(gm.game.players[3].hand) == 8  # 4th player

    def test_meadow_has_8_cards(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        assert len(gm.game.meadow) == 8

    def test_seed_reproducibility(self) -> None:
        gm1 = GameManager(["Alice", "Bob"], seed=99)
        gm2 = GameManager(["Alice", "Bob"], seed=99)
        hand1 = [c.name for c in gm1.game.players[0].hand]
        hand2 = [c.name for c in gm2.game.players[0].hand]
        assert hand1 == hand2

    def test_current_player_is_first(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        assert gm.current_player.name == "Alice"


# ---------------------------------------------------------------------------
# Turn Order Tests
# ---------------------------------------------------------------------------


class TestTurnOrder:
    def test_clockwise_turn_order(self) -> None:
        gm = GameManager(["Alice", "Bob", "Charlie"], seed=42)

        # Alice places a worker
        alice = gm.current_player
        assert alice.name == "Alice"
        actions = gm.get_valid_actions()
        worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
        assert len(worker_actions) > 0
        gm.perform_action(worker_actions[0])

        # Bob's turn
        assert gm.current_player.name == "Bob"
        actions = gm.get_valid_actions()
        worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
        gm.perform_action(worker_actions[0])

        # Charlie's turn
        assert gm.current_player.name == "Charlie"
        actions = gm.get_valid_actions()
        worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
        gm.perform_action(worker_actions[0])

        # Back to Alice
        assert gm.current_player.name == "Alice"


# ---------------------------------------------------------------------------
# Valid Actions Tests
# ---------------------------------------------------------------------------


class TestValidActions:
    def test_has_place_worker_actions(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        actions = gm.get_valid_actions()
        worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
        assert len(worker_actions) > 0

    def test_has_play_card_actions_when_affordable(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        # Give Alice lots of resources so she can afford cards
        alice = gm.current_player
        alice.resources = ResourceBank(twig=20, resin=20, pebble=20, berry=20)
        actions = gm.get_valid_actions()
        card_actions = [a for a in actions if a.action_type == ActionType.PLAY_CARD]
        # She should be able to play cards from hand or meadow
        assert len(card_actions) > 0

    def test_no_prepare_for_season_with_available_workers(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        actions = gm.get_valid_actions()
        season_actions = [a for a in actions if a.action_type == ActionType.PREPARE_FOR_SEASON]
        # Alice has 2 workers available, shouldn't be able to prepare
        assert len(season_actions) == 0

    def test_prepare_for_season_when_all_workers_deployed(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player
        player_id = str(alice.id)

        # Deploy all workers by placing them
        for _ in range(alice.workers_total):
            actions = gm.get_valid_actions()
            worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
            assert len(worker_actions) > 0
            gm.perform_action(worker_actions[0])
            # Skip Bob's turn by placing a worker for him too
            bob_actions = gm.get_valid_actions()
            bob_worker = [a for a in bob_actions if a.action_type == ActionType.PLACE_WORKER]
            if bob_worker:
                gm.perform_action(bob_worker[0])

        # Now Alice should have prepare_for_season available
        assert gm.current_player.name == "Alice"
        actions = gm.get_valid_actions()
        season_actions = [a for a in actions if a.action_type == ActionType.PREPARE_FOR_SEASON]
        assert len(season_actions) == 1


# ---------------------------------------------------------------------------
# Place Worker Tests
# ---------------------------------------------------------------------------


class TestPlaceWorker:
    def test_place_worker_decrements_available(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player
        initial_placed = alice.workers_placed

        actions = gm.get_valid_actions()
        worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
        gm.perform_action(worker_actions[0])

        assert alice.workers_placed == initial_placed + 1

    def test_place_worker_records_location(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player

        actions = gm.get_valid_actions()
        worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
        loc_id = worker_actions[0].location_id
        gm.perform_action(worker_actions[0])

        assert loc_id in alice.workers_deployed


# ---------------------------------------------------------------------------
# Play Card Tests
# ---------------------------------------------------------------------------


class TestPlayCard:
    def test_play_card_from_hand(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player
        alice.resources = ResourceBank(twig=20, resin=20, pebble=20, berry=20)

        initial_hand_size = len(alice.hand)
        initial_city_size = len(alice.city)

        actions = gm.get_valid_actions()
        card_actions = [
            a for a in actions
            if a.action_type == ActionType.PLAY_CARD and a.source == "hand"
        ]
        if card_actions:
            gm.perform_action(card_actions[0])
            assert len(alice.hand) == initial_hand_size - 1
            assert len(alice.city) == initial_city_size + 1

    def test_play_card_from_meadow(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player
        alice.resources = ResourceBank(twig=20, resin=20, pebble=20, berry=20)

        actions = gm.get_valid_actions()
        meadow_actions = [
            a for a in actions
            if a.action_type == ActionType.PLAY_CARD and a.source == "meadow"
        ]
        if meadow_actions:
            initial_city_size = len(alice.city)
            gm.perform_action(meadow_actions[0])
            assert len(alice.city) == initial_city_size + 1
            # Meadow should still have 8 cards (replenished)
            assert len(gm.game.meadow) == 8

    def test_play_card_costs_resources(self) -> None:
        """Playing a card should deduct its cost from player resources."""
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player
        player_id = str(alice.id)

        # Use a known card: Mine costs (1 twig, 1 resin, 1 pebble)
        # Mine is a green production card that gives 1 pebble on_play
        from ed_engine.cards.constructions import Mine
        mine = Mine()
        alice.hand = [mine]  # replace hand with just Mine
        alice.city = []  # empty city to avoid governance triggers
        alice.resources = ResourceBank(twig=5, resin=5, pebble=5, berry=5)

        actions = gm.get_valid_actions()
        card_actions = [
            a for a in actions
            if a.action_type == ActionType.PLAY_CARD
            and a.source == "hand"
            and a.card_name == "Mine"
        ]
        assert len(card_actions) >= 1

        gm.perform_action(card_actions[0])
        # Cost: twig=1, resin=1, pebble=1. Production on_play gives pebble=1.
        assert alice.resources.twig == 4   # 5 - 1
        assert alice.resources.resin == 4  # 5 - 1
        assert alice.resources.pebble == 5 # 5 - 1 (cost) + 1 (production) = 5
        assert alice.resources.berry == 5  # unchanged

    def test_play_card_free_via_paired_construction(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player
        player_id = str(alice.id)

        # Manually set up a pairing: put Farm in city, Husband in hand
        from ed_engine.cards.constructions import Farm
        from ed_engine.cards.critters import Husband

        farm = Farm()
        alice.city.append(farm)

        husband = Husband()
        alice.hand.append(husband)

        # Alice should not need berries to play Husband via Farm pairing
        alice.resources = ResourceBank()  # zero resources

        actions = gm.get_valid_actions()
        paired_actions = [
            a for a in actions
            if a.action_type == ActionType.PLAY_CARD
            and a.card_name == "Husband"
            and a.use_paired_construction
        ]
        assert len(paired_actions) >= 1

        before_resources = alice.resources.model_copy()
        gm.perform_action(paired_actions[0])

        # Resources should be unchanged (free play)
        assert alice.resources == before_resources
        # Husband should be in city
        assert any(c.name == "Husband" for c in alice.city)


# ---------------------------------------------------------------------------
# Season Progression Tests
# ---------------------------------------------------------------------------


class TestSeasonProgression:
    def test_season_order(self) -> None:
        assert SeasonManager.get_next_season(Season.WINTER) == Season.SPRING
        assert SeasonManager.get_next_season(Season.SPRING) == Season.SUMMER
        assert SeasonManager.get_next_season(Season.SUMMER) == Season.AUTUMN
        assert SeasonManager.get_next_season(Season.AUTUMN) is None

    def test_cannot_prepare_with_available_workers(self) -> None:
        player = _make_player(workers_total=2, workers_placed=0)
        assert SeasonManager.can_prepare_for_season(player) is False

    def test_can_prepare_when_all_deployed(self) -> None:
        player = _make_player(workers_total=2, workers_placed=2)
        assert SeasonManager.can_prepare_for_season(player) is True

    def test_prepare_recalls_workers(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player
        player_id = str(alice.id)

        # Deploy all workers
        for _ in range(alice.workers_total):
            actions = gm.get_valid_actions()
            worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
            gm.perform_action(worker_actions[0])
            # Bob's turn
            bob_actions = gm.get_valid_actions()
            bob_worker = [a for a in bob_actions if a.action_type == ActionType.PLACE_WORKER]
            if bob_worker:
                gm.perform_action(bob_worker[0])

        # Alice prepares for season
        assert gm.current_player.name == "Alice"
        actions = gm.get_valid_actions()
        season_action = next(a for a in actions if a.action_type == ActionType.PREPARE_FOR_SEASON)
        gm.perform_action(season_action)

        # Workers should be recalled
        assert alice.workers_placed == 0
        assert alice.workers_deployed == []

    def test_prepare_advances_season(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player
        assert alice.season == Season.WINTER

        # Deploy all workers then prepare
        for _ in range(alice.workers_total):
            actions = gm.get_valid_actions()
            worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
            gm.perform_action(worker_actions[0])
            bob_actions = gm.get_valid_actions()
            bob_worker = [a for a in bob_actions if a.action_type == ActionType.PLACE_WORKER]
            if bob_worker:
                gm.perform_action(bob_worker[0])

        actions = gm.get_valid_actions()
        season_action = next(a for a in actions if a.action_type == ActionType.PREPARE_FOR_SEASON)
        gm.perform_action(season_action)

        assert alice.season == Season.SPRING

    def test_prepare_gains_workers_spring(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player

        # Deploy all 2 workers
        for _ in range(2):
            actions = gm.get_valid_actions()
            worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
            gm.perform_action(worker_actions[0])
            bob_actions = gm.get_valid_actions()
            bob_worker = [a for a in bob_actions if a.action_type == ActionType.PLACE_WORKER]
            if bob_worker:
                gm.perform_action(bob_worker[0])

        # Prepare for spring
        actions = gm.get_valid_actions()
        season_action = next(a for a in actions if a.action_type == ActionType.PREPARE_FOR_SEASON)
        gm.perform_action(season_action)

        assert alice.season == Season.SPRING
        assert alice.workers_total == 3  # 2 + 1

    def test_production_triggered_in_spring(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.current_player

        # Put a Farm in Alice's city (produces 1 berry)
        from ed_engine.cards.constructions import Farm
        farm = Farm()
        alice.city.append(farm)

        initial_berries = alice.resources.berry

        # Deploy all workers
        for _ in range(alice.workers_total):
            actions = gm.get_valid_actions()
            worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
            gm.perform_action(worker_actions[0])
            bob_actions = gm.get_valid_actions()
            bob_worker = [a for a in bob_actions if a.action_type == ActionType.PLACE_WORKER]
            if bob_worker:
                gm.perform_action(bob_worker[0])

        # Prepare for spring
        actions = gm.get_valid_actions()
        season_action = next(a for a in actions if a.action_type == ActionType.PREPARE_FOR_SEASON)
        gm.perform_action(season_action)

        assert alice.season == Season.SPRING
        assert alice.resources.berry == initial_berries + 1  # Farm produced

    def test_per_player_season_progression(self) -> None:
        """Players progress seasons independently."""
        gm = GameManager(["Alice", "Bob"], seed=42)
        alice = gm.game.players[0]
        bob = gm.game.players[1]

        # Deploy all of Alice's workers
        for _ in range(alice.workers_total):
            actions = gm.get_valid_actions()
            worker_actions = [a for a in actions if a.action_type == ActionType.PLACE_WORKER]
            gm.perform_action(worker_actions[0])
            # Bob just places workers too
            bob_actions = gm.get_valid_actions()
            bob_worker = [a for a in bob_actions if a.action_type == ActionType.PLACE_WORKER]
            if bob_worker:
                gm.perform_action(bob_worker[0])

        # Alice prepares for season
        actions = gm.get_valid_actions()
        season_action = next(a for a in actions if a.action_type == ActionType.PREPARE_FOR_SEASON)
        gm.perform_action(season_action)

        # Alice is now in Spring, Bob is still in Winter
        assert alice.season == Season.SPRING
        assert bob.season == Season.WINTER


# ---------------------------------------------------------------------------
# Game Over Tests
# ---------------------------------------------------------------------------


class TestGameOver:
    def test_game_not_over_initially(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        assert gm.is_game_over() is False
        assert gm.game.game_over is False

    def test_game_over_when_all_passed(self) -> None:
        gm = GameManager(["Alice", "Bob"], seed=42)
        # Force both players to passed state
        for p in gm.game.players:
            p.has_passed = True
        assert gm.is_game_over() is True


# ---------------------------------------------------------------------------
# Full Game Simulation
# ---------------------------------------------------------------------------


class TestFullGame:
    def test_2_player_game_completes(self) -> None:
        """A 2-player game with random legal moves should complete without errors."""
        rng = random.Random(42)
        gm = GameManager(["Alice", "Bob"], seed=42)

        max_turns = 500  # safety valve
        turns = 0

        while not gm.is_game_over() and turns < max_turns:
            player = gm.current_player
            player_id = str(player.id)

            actions = gm.get_valid_actions()

            if not actions:
                # No valid actions — player must pass
                # This shouldn't happen normally since prepare_for_season
                # should always be available when all workers are deployed.
                # Force pass if stuck.
                player.has_passed = True
                gm.advance_turn()
                turns += 1
                continue

            # Pick a random action
            action = rng.choice(actions)
            gm.perform_action(action)
            turns += 1

        assert gm.is_game_over(), f"Game did not end after {max_turns} turns"
        assert turns < max_turns, f"Game took too many turns: {turns}"

        # Calculate scores — should not crash
        scores = gm.calculate_scores()
        assert len(scores) == 2

        # Both players should have passed
        for p in gm.game.players:
            assert p.has_passed is True

    def test_1_player_game_completes(self) -> None:
        """Solo game should also complete."""
        rng = random.Random(123)
        gm = GameManager(["Alice"], seed=123)

        max_turns = 300
        turns = 0

        while not gm.is_game_over() and turns < max_turns:
            actions = gm.get_valid_actions()
            if not actions:
                gm.current_player.has_passed = True
                gm.advance_turn()
                turns += 1
                continue
            action = rng.choice(actions)
            gm.perform_action(action)
            turns += 1

        assert gm.is_game_over()
        scores = gm.calculate_scores()
        assert len(scores) == 1
