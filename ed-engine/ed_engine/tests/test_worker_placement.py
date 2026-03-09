"""Tests for the worker placement system."""

from uuid import uuid4

import pytest

from ed_engine.engine.actions import ActionHandler
from ed_engine.engine.seasons import WORKERS_BY_SEASON, SeasonManager
from ed_engine.models.enums import CardType, LocationType, Season
from ed_engine.models.game import GameState
from ed_engine.models.location import (
    Location,
    create_basic_locations,
    create_forest_locations,
    create_haven_location,
)
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank


# --- Location model tests ---


class TestLocation:
    def test_exclusive_location_blocks_second_worker(self):
        p1 = uuid4()
        p2 = uuid4()
        loc = Location(
            id="test", name="Test", location_type=LocationType.BASIC, exclusive=True
        )
        loc = loc.place(p1)
        assert not loc.can_place(p2)

    def test_shared_location_allows_multiple(self):
        p1 = uuid4()
        p2 = uuid4()
        loc = Location(
            id="test", name="Test", location_type=LocationType.BASIC, exclusive=False
        )
        loc = loc.place(p1)
        assert loc.can_place(p2)
        loc = loc.place(p2)
        assert len(loc.occupants) == 2

    def test_remove_player(self):
        p1 = uuid4()
        loc = Location(
            id="test", name="Test", location_type=LocationType.BASIC, exclusive=True
        )
        loc = loc.place(p1)
        loc = loc.remove_player(p1)
        assert not loc.is_occupied()

    def test_clear(self):
        p1 = uuid4()
        p2 = uuid4()
        loc = Location(
            id="test", name="Test", location_type=LocationType.BASIC, exclusive=False
        )
        loc = loc.place(p1).place(p2)
        loc = loc.clear()
        assert not loc.is_occupied()

    def test_place_on_occupied_exclusive_raises(self):
        p1 = uuid4()
        p2 = uuid4()
        loc = Location(
            id="test", name="Test", location_type=LocationType.BASIC, exclusive=True
        )
        loc = loc.place(p1)
        with pytest.raises(ValueError, match="occupied"):
            loc.place(p2)


class TestCreateLocations:
    def test_basic_locations_count(self):
        basics = create_basic_locations()
        assert len(basics) == 8

    def test_basic_locations_have_correct_types(self):
        basics = create_basic_locations()
        for loc in basics:
            assert loc.location_type == LocationType.BASIC

    def test_forest_locations_2_players(self):
        forests = create_forest_locations(2)
        assert len(forests) == 3
        for loc in forests:
            assert loc.location_type == LocationType.FOREST
            assert loc.exclusive is True

    def test_forest_locations_3_players(self):
        forests = create_forest_locations(3)
        assert len(forests) == 4

    def test_forest_locations_4_players(self):
        forests = create_forest_locations(4)
        assert len(forests) == 4

    def test_haven_is_shared(self):
        haven = create_haven_location()
        assert haven.location_type == LocationType.HAVEN
        assert haven.exclusive is False


# --- Helpers ---


def _make_game(player_count: int = 2) -> GameState:
    players = [Player(name=f"Player {i+1}") for i in range(player_count)]
    return GameState(
        players=players,
        board_locations=GameState.create_board(player_count),
    )


# --- ActionHandler.place_worker tests ---


class TestPlaceWorker:
    def setup_method(self):
        self.handler = ActionHandler()

    def test_place_worker_grants_resources(self):
        game = _make_game()
        player = game.players[0]
        game = self.handler.place_worker(game, player, "basic_one_twig")
        updated = game.find_player(player.id)
        assert updated.resources.twig == 1
        assert updated.workers_placed == 1

    def test_place_worker_exclusive_blocks_second(self):
        game = _make_game()
        p1 = game.players[0]
        p2 = game.players[1]
        game = self.handler.place_worker(game, p1, "basic_one_twig")
        with pytest.raises(ValueError, match="occupied"):
            self.handler.place_worker(game, p2, "basic_one_twig")

    def test_place_worker_shared_allows_multiple(self):
        game = _make_game()
        p1 = game.players[0]
        p2 = game.players[1]
        game = self.handler.place_worker(game, p1, "basic_two_twigs")
        game = self.handler.place_worker(game, p2, "basic_two_twigs")
        p1_updated = game.find_player(p1.id)
        p2_updated = game.find_player(p2.id)
        assert p1_updated.resources.twig == 2
        assert p2_updated.resources.twig == 2

    def test_place_worker_no_workers_available(self):
        game = _make_game()
        player = game.players[0]
        # Place all 2 workers
        game = self.handler.place_worker(game, player, "basic_one_twig")
        player = game.find_player(player.id)
        game = self.handler.place_worker(game, player, "basic_one_resin")
        player = game.find_player(player.id)
        with pytest.raises(ValueError, match="No available workers"):
            self.handler.place_worker(game, player, "basic_one_pebble")

    def test_place_worker_invalid_location(self):
        game = _make_game()
        player = game.players[0]
        with pytest.raises(ValueError, match="not found"):
            self.handler.place_worker(game, player, "nonexistent")

    def test_place_worker_draws_cards(self):
        game = _make_game()
        # Add some cards to the deck
        from ed_engine.models.card import TanTravelerCard
        from ed_engine.models.enums import CardCategory

        class DummyCard(TanTravelerCard):
            def on_play(self, player, **kwargs):
                pass

        deck_cards = [
            DummyCard(
                id=f"card_{i}",
                name=f"Card {i}",
                category=CardCategory.CRITTER,
            )
            for i in range(5)
        ]
        game = game.model_copy(update={"deck": deck_cards})

        player = game.players[0]
        # basic_two_resin_one_card draws 1 card
        game = self.handler.place_worker(game, player, "basic_two_resin_one_card")
        updated = game.find_player(player.id)
        assert len(updated.hand) == 1
        assert len(game.deck) == 4

    def test_place_worker_on_forest(self):
        game = _make_game()
        player = game.players[0]
        forest = [
            loc
            for loc in game.board_locations
            if loc.location_type == LocationType.FOREST
        ][0]
        game = self.handler.place_worker(game, player, forest.id)
        updated = game.find_player(player.id)
        assert updated.workers_placed == 1

    def test_place_worker_on_haven(self):
        game = _make_game()
        p1 = game.players[0]
        p2 = game.players[1]
        game = self.handler.place_worker(game, p1, "haven")
        game = self.handler.place_worker(game, p2, "haven")
        # Both should be placed (haven is shared)
        haven = game.find_location("haven")
        assert len(haven.occupants) == 2


# --- GameState board management tests ---


class TestGameStateBoard:
    def test_create_board_2_players(self):
        board = GameState.create_board(2)
        types = [loc.location_type for loc in board]
        assert types.count(LocationType.BASIC) == 8
        assert types.count(LocationType.FOREST) == 3
        assert types.count(LocationType.HAVEN) == 1

    def test_create_board_4_players(self):
        board = GameState.create_board(4)
        types = [loc.location_type for loc in board]
        assert types.count(LocationType.BASIC) == 8
        assert types.count(LocationType.FOREST) == 4
        assert types.count(LocationType.HAVEN) == 1

    def test_find_location(self):
        game = _make_game()
        loc = game.find_location("basic_one_twig")
        assert loc is not None
        assert loc.name == "One Twig"

    def test_find_location_missing(self):
        game = _make_game()
        assert game.find_location("nonexistent") is None

    def test_recall_workers(self):
        game = _make_game()
        handler = ActionHandler()
        player = game.players[0]
        game = handler.place_worker(game, player, "basic_one_twig")
        player = game.find_player(player.id)
        game = handler.place_worker(game, player, "basic_two_twigs")

        # Recall
        game = game.recall_workers(player.id)
        updated = game.find_player(player.id)
        assert updated.workers_placed == 0

        # Locations should be clear of this player
        twig = game.find_location("basic_one_twig")
        assert player.id not in twig.occupants
        twigs = game.find_location("basic_two_twigs")
        assert player.id not in twigs.occupants


# --- SeasonManager tests ---


class TestSeasonManager:
    def setup_method(self):
        self.manager = SeasonManager()
        self.handler = ActionHandler()

    def test_advance_winter_to_spring(self):
        game = _make_game()
        player = game.players[0]
        game = self.manager.advance_season(game, player)
        updated = game.find_player(player.id)
        assert updated.season == Season.SPRING
        assert updated.workers_total == WORKERS_BY_SEASON[Season.SPRING]
        assert updated.workers_placed == 0

    def test_advance_recalls_workers(self):
        game = _make_game()
        player = game.players[0]
        game = self.handler.place_worker(game, player, "basic_one_twig")
        player = game.find_player(player.id)
        game = self.handler.place_worker(game, player, "basic_one_resin")

        game = self.manager.advance_season(game, player)
        updated = game.find_player(player.id)
        assert updated.workers_placed == 0
        assert updated.workers_total == 3  # Spring

        # Locations cleared
        twig = game.find_location("basic_one_twig")
        assert not twig.is_occupied()

    def test_advance_past_autumn_raises(self):
        game = _make_game()
        player = game.players[0].model_copy(update={"season": Season.AUTUMN})
        game = game.update_player(player)
        with pytest.raises(ValueError, match="Cannot advance past autumn"):
            self.manager.advance_season(game, player)

    def test_full_season_cycle(self):
        game = _make_game()
        player = game.players[0]

        for expected_season, expected_workers in [
            (Season.SPRING, 3),
            (Season.SUMMER, 4),
            (Season.AUTUMN, 6),
        ]:
            game = self.manager.advance_season(game, player)
            player = game.find_player(player.id)
            assert player.season == expected_season
            assert player.workers_total == expected_workers
