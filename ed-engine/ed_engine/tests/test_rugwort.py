"""Tests for the Rugwort solo AI opponent."""

from __future__ import annotations

import random

import pytest

from ed_engine.cards import build_deck
from ed_engine.engine.deck import DeckManager
from ed_engine.engine.events import EventManager
from ed_engine.engine.locations import LocationManager
from ed_engine.engine.rugwort import RugwortAI
from ed_engine.models.card import Card
from ed_engine.models.enums import CardCategory, CardType, Season
from ed_engine.models.resources import ResourceBank


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_card(name: str = "TestCard", card_type: CardType = CardType.TAN_TRAVELER, **kw) -> Card:
    defaults = {
        "name": name,
        "card_type": card_type,
        "category": CardCategory.CRITTER,
        "base_points": 1,
    }
    defaults.update(kw)
    return Card(**defaults)


def _make_deck_mgr(seed: int = 42) -> DeckManager:
    return DeckManager(build_deck(), seed=seed)


def _make_location_mgr(player_count: int = 2, seed: int = 42) -> LocationManager:
    # Reset ALL_FOREST_LOCATIONS workers lists to avoid cross-test contamination
    # (LocationManager.model_copy is shallow, so workers lists are shared)
    from ed_engine.engine.locations import ALL_FOREST_LOCATIONS
    for loc in ALL_FOREST_LOCATIONS:
        loc.workers = []
    return LocationManager(player_count, seed=seed)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


class TestSetup:
    def test_initial_state(self):
        ai = RugwortAI(year=1, seed=0)
        assert ai.year == 1
        assert ai.city_cards == []
        assert ai.workers_on_meadow == []
        assert ai.achieved_events == []
        assert ai.journey_points == 0
        assert ai.point_tokens == 0
        assert ai.current_season == Season.WINTER

    def test_invalid_year(self):
        with pytest.raises(ValueError, match="Year must be 1, 2, or 3"):
            RugwortAI(year=0)
        with pytest.raises(ValueError, match="Year must be 1, 2, or 3"):
            RugwortAI(year=4)

    def test_setup_places_workers(self):
        ai = RugwortAI(year=1, seed=0)
        loc_mgr = _make_location_mgr()
        events = ai.setup(loc_mgr)

        # Should have placed on a forest location and the 3-twig basic
        assert ai.forest_worker_location is not None
        assert ai.forest_worker_location.startswith("forest_")
        assert ai.roaming_worker_location == "basic_3twigs"

        # Locations should be blocked
        forest_loc = loc_mgr.get_location(ai.forest_worker_location)
        assert RugwortAI.RUGWORT_ID in forest_loc.workers

        twig_loc = loc_mgr.get_location("basic_3twigs")
        assert RugwortAI.RUGWORT_ID in twig_loc.workers

        assert len(events) == 2

    def test_setup_specific_forest(self):
        ai = RugwortAI(year=1, seed=0)
        loc_mgr = _make_location_mgr()
        # Get the actual forest locations available
        forest_ids = [
            loc.id for loc in loc_mgr.all_locations if loc.id.startswith("forest_")
        ]
        assert len(forest_ids) >= 1
        target = forest_ids[-1]  # pick the last one

        ai.setup(loc_mgr, forest_location_id=target)
        assert ai.forest_worker_location == target


# ---------------------------------------------------------------------------
# Die Roll / Meadow Card
# ---------------------------------------------------------------------------


class TestOnHumanPlaysCard:
    def test_takes_meadow_card(self):
        ai = RugwortAI(year=1, seed=100)
        deck_mgr = _make_deck_mgr(seed=42)
        meadow_before = list(deck_mgr.meadow)
        assert len(meadow_before) == 8

        result = ai.on_human_plays_card(deck_mgr)
        assert result["die_roll"] >= 1
        assert result["die_roll"] <= 8
        assert result["card"] is not None
        assert len(ai.city_cards) == 1
        assert ai.city_cards[0] is result["card"]

        # Meadow should still be 8 (replenished)
        assert len(deck_mgr.meadow) == 8

    def test_die_roll_selects_correct_index(self):
        """With a fixed seed, the die roll should be deterministic."""
        ai = RugwortAI(year=1, seed=999)
        deck_mgr = _make_deck_mgr(seed=42)
        meadow_before = list(deck_mgr.meadow)

        # Get expected die roll
        expected_roll = random.Random(999).randint(1, 8)
        expected_card = meadow_before[expected_roll - 1]

        result = ai.on_human_plays_card(deck_mgr)
        assert result["die_roll"] == expected_roll
        assert result["card"].name == expected_card.name

    def test_blocked_position_skipped(self):
        ai = RugwortAI(year=1, seed=0)
        deck_mgr = _make_deck_mgr(seed=42)

        # Force a known die roll: seed=0 gives a specific value
        test_rng = random.Random(0)
        expected_roll = test_rng.randint(1, 8)
        target_idx = expected_roll - 1

        # Block that index
        ai.workers_on_meadow = [target_idx]
        meadow_before = list(deck_mgr.meadow)

        result = ai.on_human_plays_card(deck_mgr)
        assert result["die_roll"] == expected_roll
        # Should have taken a different card (not the blocked one)
        assert result["blocked"] is True
        assert result["adjusted_index"] != target_idx
        assert result["card"] is not None

    def test_empty_meadow_returns_none(self):
        ai = RugwortAI(year=1, seed=0)
        deck_mgr = _make_deck_mgr(seed=42)
        # Drain the meadow entirely (also drains deck via replenish)
        while deck_mgr.meadow:
            deck_mgr.draw_from_meadow(0)

        result = ai.on_human_plays_card(deck_mgr)
        assert result["card"] is None

    def test_multiple_plays_accumulate_cards(self):
        ai = RugwortAI(year=1, seed=42)
        deck_mgr = _make_deck_mgr(seed=42)

        for i in range(5):
            result = ai.on_human_plays_card(deck_mgr)
            assert result["card"] is not None

        assert len(ai.city_cards) == 5


# ---------------------------------------------------------------------------
# Basic Event Claiming
# ---------------------------------------------------------------------------


class TestBasicEventClaiming:
    def test_can_claim_with_3_of_color(self):
        ai = RugwortAI(year=1, seed=0)
        ai.city_cards = [
            _make_card("Blue1", CardType.BLUE_GOVERNANCE),
            _make_card("Blue2", CardType.BLUE_GOVERNANCE),
            _make_card("Blue3", CardType.BLUE_GOVERNANCE),
        ]
        assert ai.can_claim_basic_event(CardType.BLUE_GOVERNANCE) is True

    def test_cannot_claim_with_2_of_color(self):
        ai = RugwortAI(year=1, seed=0)
        ai.city_cards = [
            _make_card("Blue1", CardType.BLUE_GOVERNANCE),
            _make_card("Blue2", CardType.BLUE_GOVERNANCE),
        ]
        assert ai.can_claim_basic_event(CardType.BLUE_GOVERNANCE) is False

    def test_claims_event_via_event_manager(self):
        ai = RugwortAI(year=1, seed=0)
        ai.city_cards = [
            _make_card("Green1", CardType.GREEN_PRODUCTION),
            _make_card("Green2", CardType.GREEN_PRODUCTION),
            _make_card("Green3", CardType.GREEN_PRODUCTION),
        ]
        event_mgr = EventManager(seed=42)
        loc_mgr = _make_location_mgr()
        ai.setup(loc_mgr)

        ai.on_human_prepares_for_season(Season.SPRING, loc_mgr, event_mgr)

        assert "basic_production" in ai.achieved_events
        # Verify the event manager also marks it claimed
        claimed = event_mgr.get_claimed_events(RugwortAI.RUGWORT_ID)
        assert any(e.id == "basic_production" for e in claimed)

    def test_does_not_double_claim(self):
        ai = RugwortAI(year=1, seed=0)
        ai.city_cards = [
            _make_card("Green1", CardType.GREEN_PRODUCTION),
            _make_card("Green2", CardType.GREEN_PRODUCTION),
            _make_card("Green3", CardType.GREEN_PRODUCTION),
        ]
        event_mgr = EventManager(seed=42)
        loc_mgr = _make_location_mgr()
        ai.setup(loc_mgr)

        ai.on_human_prepares_for_season(Season.SPRING, loc_mgr, event_mgr)
        ai.on_human_prepares_for_season(Season.SUMMER, loc_mgr, event_mgr)

        # Should still only have one claim
        assert ai.achieved_events.count("basic_production") == 1


# ---------------------------------------------------------------------------
# Season Progression
# ---------------------------------------------------------------------------


class TestSeasonProgression:
    def test_spring_blocks_meadow_1_moves_to_2resin(self):
        ai = RugwortAI(year=1, seed=0)
        loc_mgr = _make_location_mgr()
        ai.setup(loc_mgr)

        events = ai.on_human_prepares_for_season(Season.SPRING, loc_mgr)

        assert 0 in ai.workers_on_meadow  # meadow slot 1 (0-indexed)
        assert ai.roaming_worker_location == "basic_2resin"

        # Old location should be free
        twig_loc = loc_mgr.get_location("basic_3twigs")
        assert RugwortAI.RUGWORT_ID not in twig_loc.workers

        # New location should be occupied
        resin_loc = loc_mgr.get_location("basic_2resin")
        assert RugwortAI.RUGWORT_ID in resin_loc.workers

    def test_summer_blocks_meadow_2_moves_to_1pebble(self):
        ai = RugwortAI(year=1, seed=0)
        loc_mgr = _make_location_mgr()
        ai.setup(loc_mgr)

        # Go through spring first
        ai.on_human_prepares_for_season(Season.SPRING, loc_mgr)
        ai.on_human_prepares_for_season(Season.SUMMER, loc_mgr)

        assert 1 in ai.workers_on_meadow  # meadow slot 2
        assert ai.roaming_worker_location == "basic_1pebble"

    def test_autumn_blocks_meadow_3_and_4_journey_and_forest(self):
        ai = RugwortAI(year=1, seed=0)
        loc_mgr = _make_location_mgr()
        ai.setup(loc_mgr)
        forest_loc_id = ai.forest_worker_location

        ai.on_human_prepares_for_season(Season.SPRING, loc_mgr)
        ai.on_human_prepares_for_season(Season.SUMMER, loc_mgr)
        ai.on_human_prepares_for_season(Season.AUTUMN, loc_mgr)

        assert 2 in ai.workers_on_meadow  # meadow slot 3
        assert 3 in ai.workers_on_meadow  # meadow slot 4
        assert ai.roaming_worker_location == "basic_1berry_1card"

        # Forest worker removed
        assert ai.forest_worker_location is None
        forest_loc = loc_mgr.get_location(forest_loc_id)
        assert RugwortAI.RUGWORT_ID not in forest_loc.workers

        # Journey worker placed
        journey_loc = loc_mgr.get_location("journey_3pt")
        assert RugwortAI.RUGWORT_ID in journey_loc.workers
        assert ai.journey_points == 3  # year 1


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


class TestScoring:
    def test_basic_card_scoring(self):
        ai = RugwortAI(year=1, seed=0)
        ai.city_cards = [
            _make_card("Tan1", CardType.TAN_TRAVELER),
            _make_card("Green1", CardType.GREEN_PRODUCTION),
            _make_card("Blue1", CardType.BLUE_GOVERNANCE),
        ]
        # 3 non-purple cards = 3 * 2 = 6
        score = ai.calculate_score(human_special_events=[], total_special_events=0)
        assert score == 6

    def test_purple_cards_worth_3(self):
        ai = RugwortAI(year=1, seed=0)
        ai.city_cards = [
            _make_card("Purple1", CardType.PURPLE_PROSPERITY),
            _make_card("Purple2", CardType.PURPLE_PROSPERITY),
            _make_card("Tan1", CardType.TAN_TRAVELER),
        ]
        # 2 purple (3 each) + 1 non-purple (2) = 8
        score = ai.calculate_score(human_special_events=[], total_special_events=0)
        assert score == 8

    def test_basic_event_scoring(self):
        ai = RugwortAI(year=1, seed=0)
        ai.achieved_events = ["basic_production", "basic_governance"]
        score = ai.calculate_score(human_special_events=[], total_special_events=0)
        assert score == 6  # 2 * 3

    def test_unachieved_special_events_year1(self):
        ai = RugwortAI(year=1, seed=0)
        # Human achieved 1 of 4 special events
        score = ai.calculate_score(
            human_special_events=["se_brilliant_wedding"],
            total_special_events=4,
        )
        # 3 unachieved * 3 points = 9
        assert score == 9

    def test_unachieved_special_events_year2(self):
        ai = RugwortAI(year=2, seed=0)
        score = ai.calculate_score(
            human_special_events=["se_brilliant_wedding"],
            total_special_events=4,
        )
        # 3 unachieved * 6 points = 18
        assert score == 18

    def test_journey_points(self):
        ai = RugwortAI(year=1, seed=0)
        ai.journey_points = 3
        score = ai.calculate_score(human_special_events=[], total_special_events=0)
        assert score == 3

    def test_journey_value_by_year(self):
        assert RugwortAI(year=1).journey_value == 3
        assert RugwortAI(year=2).journey_value == 4
        assert RugwortAI(year=3).journey_value == 5

    def test_point_tokens(self):
        ai = RugwortAI(year=1, seed=0)
        ai.add_point_tokens(5)
        score = ai.calculate_score(human_special_events=[], total_special_events=0)
        assert score == 5

    def test_full_score_calculation(self):
        """Combined scoring with all components."""
        ai = RugwortAI(year=2, seed=0)
        ai.city_cards = [
            _make_card("Tan1", CardType.TAN_TRAVELER),
            _make_card("Purple1", CardType.PURPLE_PROSPERITY),
        ]
        ai.achieved_events = ["basic_production"]
        ai.journey_points = 4
        ai.point_tokens = 2

        score = ai.calculate_score(
            human_special_events=["se_brilliant_wedding"],
            total_special_events=4,
        )
        # Cards: 2 + 3 = 5
        # Events: 1 * 3 = 3
        # Unachieved special: 3 * 6 = 18
        # Journey: 4
        # Tokens: 2
        # Total: 32
        assert score == 32


# ---------------------------------------------------------------------------
# Year 3: Kidnap
# ---------------------------------------------------------------------------


class TestYear3Kidnap:
    def test_no_kidnap_year1(self):
        ai = RugwortAI(year=1, seed=0)
        result = ai.kidnap_worker(["forest_01"])
        assert result is None

    def test_no_kidnap_year2(self):
        ai = RugwortAI(year=2, seed=0)
        result = ai.kidnap_worker(["forest_01"])
        assert result is None

    def test_kidnap_year3(self):
        ai = RugwortAI(year=3, seed=0)
        result = ai.kidnap_worker(["forest_01", "basic_3twigs"])
        assert result == "forest_01"

    def test_kidnap_no_workers(self):
        ai = RugwortAI(year=3, seed=0)
        result = ai.kidnap_worker([])
        assert result is None


# ---------------------------------------------------------------------------
# Complete Solo Game Simulation
# ---------------------------------------------------------------------------


class TestSoloGameSimulation:
    def test_full_game_flow(self):
        """Simulate a complete solo game with Rugwort through all seasons."""
        ai = RugwortAI(year=1, seed=42)
        deck_mgr = _make_deck_mgr(seed=100)
        loc_mgr = _make_location_mgr(seed=100)
        event_mgr = EventManager(seed=100)

        # Setup
        setup_events = ai.setup(loc_mgr)
        assert len(setup_events) == 2
        assert ai.forest_worker_location is not None
        assert ai.roaming_worker_location == "basic_3twigs"

        # Simulate winter: human plays some cards, Rugwort responds
        for _ in range(3):
            result = ai.on_human_plays_card(deck_mgr)
            assert result["card"] is not None

        assert len(ai.city_cards) == 3

        # Human prepares for spring -> Rugwort follows
        spring_events = ai.on_human_prepares_for_season(
            Season.SPRING, loc_mgr, event_mgr
        )
        assert ai.roaming_worker_location == "basic_2resin"
        assert 0 in ai.workers_on_meadow

        # Simulate spring plays
        for _ in range(4):
            result = ai.on_human_plays_card(deck_mgr)
            assert result["card"] is not None

        assert len(ai.city_cards) == 7

        # Human prepares for summer
        summer_events = ai.on_human_prepares_for_season(
            Season.SUMMER, loc_mgr, event_mgr
        )
        assert ai.roaming_worker_location == "basic_1pebble"
        assert 1 in ai.workers_on_meadow

        # Simulate summer plays
        for _ in range(5):
            result = ai.on_human_plays_card(deck_mgr)
            assert result["card"] is not None

        assert len(ai.city_cards) == 12

        # Human prepares for autumn
        autumn_events = ai.on_human_prepares_for_season(
            Season.AUTUMN, loc_mgr, event_mgr
        )
        assert ai.roaming_worker_location == "basic_1berry_1card"
        assert ai.forest_worker_location is None
        assert ai.journey_points == 3
        assert 2 in ai.workers_on_meadow
        assert 3 in ai.workers_on_meadow

        # Final scoring
        score = ai.calculate_score(
            human_special_events=[],
            total_special_events=4,
        )
        # Should have: 12 cards (at least 24 points) + events + 12 unachieved + 3 journey
        assert score >= 24 + 12 + 3  # minimum with no purple cards, no basic events

    def test_deterministic_with_seed(self):
        """Same seed should produce identical game outcomes."""
        results = []
        for _ in range(2):
            ai = RugwortAI(year=1, seed=77)
            deck_mgr = _make_deck_mgr(seed=55)
            loc_mgr = _make_location_mgr(seed=55)

            ai.setup(loc_mgr)
            cards = []
            for _ in range(5):
                r = ai.on_human_plays_card(deck_mgr)
                cards.append(r["card"].name if r["card"] else None)
            results.append(cards)

        assert results[0] == results[1]

    def test_year2_higher_unachieved_penalty(self):
        """Year 2 should give 6 points per unachieved special event."""
        ai1 = RugwortAI(year=1, seed=0)
        ai2 = RugwortAI(year=2, seed=0)

        s1 = ai1.calculate_score(human_special_events=[], total_special_events=4)
        s2 = ai2.calculate_score(human_special_events=[], total_special_events=4)

        # Year 1: 4 * 3 = 12, Year 2: 4 * 6 = 24
        assert s1 == 12
        assert s2 == 24

    def test_year2_journey_value(self):
        """Year 2 journey should be worth 4 points."""
        ai = RugwortAI(year=2, seed=0)
        loc_mgr = _make_location_mgr()
        ai.setup(loc_mgr)

        ai.on_human_prepares_for_season(Season.SPRING, loc_mgr)
        ai.on_human_prepares_for_season(Season.SUMMER, loc_mgr)
        ai.on_human_prepares_for_season(Season.AUTUMN, loc_mgr)

        assert ai.journey_points == 4

    def test_year3_journey_value(self):
        """Year 3 journey should be worth 5 points."""
        ai = RugwortAI(year=3, seed=0)
        loc_mgr = _make_location_mgr()
        ai.setup(loc_mgr)

        ai.on_human_prepares_for_season(Season.SPRING, loc_mgr)
        ai.on_human_prepares_for_season(Season.SUMMER, loc_mgr)
        ai.on_human_prepares_for_season(Season.AUTUMN, loc_mgr)

        assert ai.journey_points == 5
