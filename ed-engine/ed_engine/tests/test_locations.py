import pytest

from ed_engine.engine.locations import (
    BasicLocation,
    ForestLocation,
    HavenLocation,
    JourneyLocation,
    LocationManager,
)
from ed_engine.models.enums import LocationType, Season
from ed_engine.models.game import GameState
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank
from ed_engine.engine.deck import DeckManager
from ed_engine.engine.actions import ActionHandler, GameAction, ActionType
from ed_engine.cards import build_deck


class TestLocationAvailability:
    def test_exclusive_location_empty(self) -> None:
        loc = BasicLocation(id="test", name="Test", exclusive=True)
        assert loc.is_available("p1") is True

    def test_exclusive_location_occupied(self) -> None:
        loc = BasicLocation(id="test", name="Test", exclusive=True)
        loc.place_worker("p1")
        assert loc.is_available("p2") is False

    def test_shared_location_multiple_players(self) -> None:
        loc = BasicLocation(id="test", name="Test", exclusive=False)
        loc.place_worker("p1")
        assert loc.is_available("p2") is True

    def test_shared_location_same_player_blocked(self) -> None:
        loc = BasicLocation(id="test", name="Test", exclusive=False)
        loc.place_worker("p1")
        assert loc.is_available("p1") is False

    def test_place_worker_on_unavailable_raises(self) -> None:
        loc = BasicLocation(id="test", name="Test", exclusive=True)
        loc.place_worker("p1")
        with pytest.raises(ValueError):
            loc.place_worker("p2")

    def test_remove_worker(self) -> None:
        loc = BasicLocation(id="test", name="Test", exclusive=True)
        loc.place_worker("p1")
        loc.remove_worker("p1")
        assert loc.is_available("p1") is True

    def test_remove_nonexistent_worker_noop(self) -> None:
        loc = BasicLocation(id="test", name="Test", exclusive=True)
        loc.remove_worker("p1")  # should not raise


class TestHavenLocation:
    def test_haven_is_shared(self) -> None:
        loc = HavenLocation(id="haven", name="Haven")
        assert loc.exclusive is False
        assert loc.location_type == LocationType.HAVEN

    def test_haven_multiple_players(self) -> None:
        loc = HavenLocation(id="haven", name="Haven")
        loc.place_worker("p1")
        loc.place_worker("p2")
        assert len(loc.workers) == 2


class TestJourneyLocation:
    def test_journey_exclusive(self) -> None:
        loc = JourneyLocation(id="j3", name="Journey 3pt", exclusive=True, point_value=3)
        loc.place_worker("p1")
        assert loc.is_available("p2") is False

    def test_journey_shared(self) -> None:
        loc = JourneyLocation(id="j2", name="Journey 2pt", exclusive=False, point_value=2)
        loc.place_worker("p1")
        assert loc.is_available("p2") is True


class TestLocationManager:
    def test_basic_locations_2_player(self) -> None:
        mgr = LocationManager(player_count=2, seed=42)
        basics = [l for l in mgr.all_locations if l.location_type == LocationType.BASIC]
        assert len(basics) == 8  # 7 + 1 copy of 2-any

    def test_basic_locations_4_player(self) -> None:
        mgr = LocationManager(player_count=4, seed=42)
        basics = [l for l in mgr.all_locations if l.location_type == LocationType.BASIC]
        assert len(basics) == 8  # Same 8 basic locations regardless of player count

    def test_forest_locations_2_player(self) -> None:
        mgr = LocationManager(player_count=2, seed=42)
        forests = [l for l in mgr.all_locations if l.location_type == LocationType.FOREST]
        assert len(forests) == 3

    def test_forest_locations_3_player(self) -> None:
        mgr = LocationManager(player_count=3, seed=42)
        forests = [l for l in mgr.all_locations if l.location_type == LocationType.FOREST]
        assert len(forests) == 4

    def test_haven_exists(self) -> None:
        mgr = LocationManager(player_count=2, seed=42)
        haven = mgr.get_location("haven")
        assert haven is not None
        assert haven.location_type == LocationType.HAVEN

    def test_journey_locations_exist(self) -> None:
        mgr = LocationManager(player_count=2, seed=42)
        journeys = [l for l in mgr.all_locations if l.location_type == LocationType.JOURNEY]
        assert len(journeys) == 4

    def test_journey_not_available_before_autumn(self) -> None:
        mgr = LocationManager(player_count=2, seed=42)
        available = mgr.get_available_locations("p1", Season.WINTER)
        journey_ids = [l.id for l in available if l.location_type == LocationType.JOURNEY]
        assert len(journey_ids) == 0

    def test_journey_available_in_autumn(self) -> None:
        mgr = LocationManager(player_count=2, seed=42)
        available = mgr.get_available_locations("p1", Season.AUTUMN)
        journey_ids = [l.id for l in available if l.location_type == LocationType.JOURNEY]
        assert len(journey_ids) == 4

    def test_place_worker_and_recall(self) -> None:
        mgr = LocationManager(player_count=2, seed=42)
        mgr.place_worker("basic_3twigs", "p1")
        loc = mgr.get_location("basic_3twigs")
        assert "p1" in loc.workers
        # Recall
        recalled = mgr.recall_all_workers("p1")
        assert any(l.id == "basic_3twigs" for l in recalled)
        assert "p1" not in loc.workers

    def test_place_worker_unknown_location_raises(self) -> None:
        mgr = LocationManager(player_count=2, seed=42)
        with pytest.raises(ValueError, match="Unknown location"):
            mgr.place_worker("nonexistent", "p1")

    def test_get_available_excludes_occupied_exclusive(self) -> None:
        mgr = LocationManager(player_count=2, seed=42)
        mgr.place_worker("basic_3twigs", "p1")
        available = mgr.get_available_locations("p2", Season.WINTER)
        assert all(l.id != "basic_3twigs" for l in available)

    def test_seed_reproducibility(self) -> None:
        mgr1 = LocationManager(player_count=2, seed=42)
        mgr2 = LocationManager(player_count=2, seed=42)
        forests1 = sorted(l.id for l in mgr1.all_locations if l.location_type == LocationType.FOREST)
        forests2 = sorted(l.id for l in mgr2.all_locations if l.location_type == LocationType.FOREST)
        assert forests1 == forests2


class TestForest08CopyBasicLocation:
    """Forest 08: Copy any Basic location and draw 1 card."""

    def _setup(self):
        game = GameState()
        player = Player(name="Alice", resources=ResourceBank())
        deck_mgr = DeckManager(build_deck(), seed=42)
        loc = ForestLocation(id="forest_08", name="Copy any Basic location and draw 1 card")
        return game, player, deck_mgr, loc

    def test_sets_pending_choice_with_8_options(self) -> None:
        game, player, deck_mgr, loc = self._setup()
        loc.on_activate(game, player, deck_mgr=deck_mgr)
        assert game.pending_choice is not None
        assert game.pending_choice["choice_type"] == "select_basic_location"
        assert len(game.pending_choice["options"]) == 8

    def test_draws_1_card(self) -> None:
        game, player, deck_mgr, loc = self._setup()
        assert len(player.hand) == 0
        loc.on_activate(game, player, deck_mgr=deck_mgr)
        assert len(player.hand) == 1

    def test_resolve_3_twigs(self) -> None:
        """Choosing '3 Twigs' should grant 3 twigs."""
        game, player, deck_mgr, loc = self._setup()
        mgr = LocationManager(player_count=2, seed=42)
        loc.on_activate(game, player, deck_mgr=deck_mgr)
        # Simulate resolving the choice via ActionHandler

        action = GameAction(
            action_type=ActionType.RESOLVE_CHOICE,
            player_id=str(player.id),
            choice_index=0,  # "3 Twigs"
        )
        events = ActionHandler._resolve_choice(game, player, action, deck_mgr, mgr)
        assert player.resources.twig == 3
        assert game.pending_choice is None
        assert any("copied" in e.lower() or "3 Twigs" in e for e in events)

    def test_resolve_1_pebble(self) -> None:
        """Choosing '1 Pebble' should grant 1 pebble."""
        game, player, deck_mgr, loc = self._setup()
        mgr = LocationManager(player_count=2, seed=42)
        loc.on_activate(game, player, deck_mgr=deck_mgr)
        action = GameAction(
            action_type=ActionType.RESOLVE_CHOICE,
            player_id=str(player.id),
            choice_index=5,  # "1 Pebble"
        )

        ActionHandler._resolve_choice(game, player, action, deck_mgr, mgr)
        assert player.resources.pebble == 1
        assert game.pending_choice is None

    def test_resolve_2twigs_1card_draws_extra(self) -> None:
        """Choosing '2 Twigs + 1 Card' should grant 2 twigs and draw another card."""
        game, player, deck_mgr, loc = self._setup()
        mgr = LocationManager(player_count=2, seed=42)
        loc.on_activate(game, player, deck_mgr=deck_mgr)
        cards_after_activate = len(player.hand)  # Should be 1 from forest_08 draw
        action = GameAction(
            action_type=ActionType.RESOLVE_CHOICE,
            player_id=str(player.id),
            choice_index=1,  # "2 Twigs + 1 Card"
        )

        ActionHandler._resolve_choice(game, player, action, deck_mgr, mgr)
        assert player.resources.twig == 2
        assert len(player.hand) == cards_after_activate + 1  # Extra card from basic location
