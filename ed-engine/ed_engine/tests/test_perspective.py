"""Tests for perspective-filtered game state serialization."""
from __future__ import annotations

import pytest

from ed_engine.engine.game_manager import GameManager
from ed_engine.engine.perspective import PerspectiveFilter
from ed_engine.models.card import Card
from ed_engine.models.enums import CardCategory, CardType, Season
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gm(names: list[str] | None = None, seed: int = 42) -> GameManager:
    """Create a seeded GameManager for deterministic tests."""
    if names is None:
        names = ["Alice", "Bob"]
    return GameManager(names, seed=seed)


def _player_ids(gm: GameManager) -> list[str]:
    """Return list of GM player UUID strings in order."""
    return [str(p.id) for p in gm.game.players]


# ---------------------------------------------------------------------------
# Card Serialization
# ---------------------------------------------------------------------------


class TestSerializeCard:
    def test_all_fields_present(self) -> None:
        card = Card(
            name="Farm",
            card_type=CardType.GREEN_PRODUCTION,
            category=CardCategory.CONSTRUCTION,
            cost=ResourceBank(twig=2, resin=1),
            base_points=1,
            unique=True,
            paired_with="Harvester",
            occupies_city_space=True,
            is_open_destination=False,
        )
        d = PerspectiveFilter.serialize_card(card)
        assert d["name"] == "Farm"
        assert d["card_type"] == "green_production"
        assert d["category"] == "construction"
        assert d["cost"] == {"twig": 2, "resin": 1, "pebble": 0, "berry": 0}
        assert d["base_points"] == 1
        assert d["unique"] is True
        assert d["paired_with"] == "Harvester"
        assert d["occupies_city_space"] is True
        assert d["is_open_destination"] is False

    def test_default_card_serialization(self) -> None:
        card = Card(
            name="Simple",
            card_type=CardType.TAN_TRAVELER,
            category=CardCategory.CRITTER,
        )
        d = PerspectiveFilter.serialize_card(card)
        assert d["name"] == "Simple"
        assert d["base_points"] == 0
        assert d["paired_with"] is None


# ---------------------------------------------------------------------------
# Player Serialization
# ---------------------------------------------------------------------------


class TestSerializePlayer:
    def test_own_hand_visible(self) -> None:
        gm = _make_gm()
        alice = gm.game.players[0]
        d = PerspectiveFilter.serialize_player(alice, is_self=True)
        assert "hand" in d
        assert len(d["hand"]) == len(alice.hand)
        assert d["hand_size"] == len(alice.hand)

    def test_other_hand_hidden(self) -> None:
        gm = _make_gm()
        bob = gm.game.players[1]
        d = PerspectiveFilter.serialize_player(bob, is_self=False)
        assert "hand" not in d
        assert d["hand_size"] == len(bob.hand)

    def test_public_info_always_visible(self) -> None:
        gm = _make_gm()
        bob = gm.game.players[1]
        d = PerspectiveFilter.serialize_player(bob, is_self=False)
        assert "resources" in d
        assert "city" in d
        assert "workers_total" in d
        assert "workers_placed" in d
        assert "workers_deployed" in d
        assert "season" in d
        assert "name" in d
        assert "id" in d
        assert "score" in d
        assert "has_passed" in d

    def test_resources_are_dict(self) -> None:
        gm = _make_gm()
        alice = gm.game.players[0]
        d = PerspectiveFilter.serialize_player(alice, is_self=True)
        r = d["resources"]
        assert isinstance(r, dict)
        assert set(r.keys()) == {"twig", "resin", "pebble", "berry"}


# ---------------------------------------------------------------------------
# API Serialization (serialize_for_api)
# ---------------------------------------------------------------------------


class TestSerializeForApi:
    def test_own_hand_visible_others_hidden(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        alice_id = ids[0]

        state = PerspectiveFilter.serialize_for_api(gm, player_id=alice_id)
        players = state["players"]

        # Alice should have hand
        alice_view = next(p for p in players if p["id"] == alice_id)
        assert "hand" in alice_view

        # Bob should NOT have hand
        bob_view = next(p for p in players if p["id"] != alice_id)
        assert "hand" not in bob_view
        assert "hand_size" in bob_view

    def test_spectator_view_hides_all_hands(self) -> None:
        gm = _make_gm()
        state = PerspectiveFilter.serialize_for_api(gm, player_id=None)
        for p in state["players"]:
            assert "hand" not in p
            assert "hand_size" in p

    def test_deck_order_hidden(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        state = PerspectiveFilter.serialize_for_api(gm, player_id=ids[0])
        # Should have deck_size, not a deck list
        assert "deck_size" in state
        assert isinstance(state["deck_size"], int)
        assert state["deck_size"] > 0
        assert "deck" not in state

    def test_discard_size_present(self) -> None:
        gm = _make_gm()
        state = PerspectiveFilter.serialize_for_api(gm, player_id=None)
        assert "discard_size" in state
        assert isinstance(state["discard_size"], int)

    def test_meadow_visible(self) -> None:
        gm = _make_gm()
        state = PerspectiveFilter.serialize_for_api(gm, player_id=None)
        assert "meadow" in state
        assert len(state["meadow"]) == 8
        # Each meadow card should be serialized
        for card in state["meadow"]:
            assert "name" in card
            assert "cost" in card

    def test_valid_actions_only_for_current_player(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        alice_id = ids[0]
        bob_id = ids[1]

        # Alice is current player (idx 0)
        assert gm.current_player.name == "Alice"

        # Alice's view should have valid_actions
        alice_state = PerspectiveFilter.serialize_for_api(gm, player_id=alice_id)
        assert len(alice_state["valid_actions"]) > 0

        # Bob's view should have no valid_actions (not his turn)
        bob_state = PerspectiveFilter.serialize_for_api(gm, player_id=bob_id)
        assert len(bob_state["valid_actions"]) == 0

    def test_game_id_and_metadata(self) -> None:
        gm = _make_gm()
        state = PerspectiveFilter.serialize_for_api(gm, player_id=None)
        assert "game_id" in state
        assert "turn_number" in state
        assert "current_player_id" in state
        assert "game_over" in state
        assert state["game_over"] is False
        assert state["turn_number"] == 1

    def test_events_present(self) -> None:
        gm = _make_gm()
        state = PerspectiveFilter.serialize_for_api(gm, player_id=None)
        assert "events" in state
        assert "basic_events" in state["events"]
        assert "special_events" in state["events"]

    def test_locations_present(self) -> None:
        gm = _make_gm()
        state = PerspectiveFilter.serialize_for_api(gm, player_id=None)
        assert "forest_locations" in state
        assert "basic_locations" in state
        assert len(state["basic_locations"]) > 0
        assert len(state["forest_locations"]) > 0

    def test_all_public_info_visible(self) -> None:
        """Cities, resources, workers should be visible for all players."""
        gm = _make_gm(["Alice", "Bob", "Charlie"])
        ids = _player_ids(gm)
        state = PerspectiveFilter.serialize_for_api(gm, player_id=ids[0])
        for p in state["players"]:
            assert "city" in p
            assert "resources" in p
            assert "workers_total" in p
            assert "workers_placed" in p
            assert "workers_deployed" in p
            assert "season" in p


# ---------------------------------------------------------------------------
# filter_state (dict-based filtering)
# ---------------------------------------------------------------------------


class TestFilterState:
    def test_deck_replaced_with_size(self) -> None:
        raw = {"deck": [1, 2, 3], "discard": [4], "players": []}
        filtered = PerspectiveFilter.filter_state(raw, player_id=None)
        assert "deck" not in filtered
        assert filtered["deck_size"] == 3
        assert "discard" not in filtered
        assert filtered["discard_size"] == 1

    def test_own_hand_kept(self) -> None:
        raw = {
            "players": [
                {"id": "aaa", "hand": ["c1", "c2"]},
                {"id": "bbb", "hand": ["c3"]},
            ]
        }
        filtered = PerspectiveFilter.filter_state(raw, player_id="aaa")
        alice = next(p for p in filtered["players"] if p["id"] == "aaa")
        bob = next(p for p in filtered["players"] if p["id"] == "bbb")
        assert "hand" in alice
        assert alice["hand_size"] == 2
        assert "hand" not in bob
        assert bob["hand_size"] == 1

    def test_spectator_hides_all_hands(self) -> None:
        raw = {
            "players": [
                {"id": "aaa", "hand": ["c1"]},
                {"id": "bbb", "hand": ["c2", "c3"]},
            ]
        }
        filtered = PerspectiveFilter.filter_state(raw, player_id=None)
        for p in filtered["players"]:
            assert "hand" not in p
            assert "hand_size" in p


# ---------------------------------------------------------------------------
# AI Serialization
# ---------------------------------------------------------------------------


class TestSerializeForAi:
    def test_compact_format(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        text = PerspectiveFilter.serialize_for_ai(gm, ids[0])
        assert "=== MY STATE ===" in text
        assert "=== MEADOW ===" in text
        assert "=== OPPONENTS ===" in text
        assert "=== VALID ACTIONS ===" in text

    def test_token_count_under_limit(self) -> None:
        """AI format should be compact — rough proxy: under 8000 chars."""
        gm = _make_gm()
        ids = _player_ids(gm)
        text = PerspectiveFilter.serialize_for_ai(gm, ids[0])
        # 2K tokens ~ 8K chars. Give generous headroom.
        assert len(text) < 10000, f"AI serialization too long: {len(text)} chars"

    def test_resources_format(self) -> None:
        gm = _make_gm()
        alice = gm.game.players[0]
        alice.resources = ResourceBank(twig=3, resin=2, pebble=1, berry=4)
        ids = _player_ids(gm)
        text = PerspectiveFilter.serialize_for_ai(gm, ids[0])
        assert "3T 2R 1P 4B" in text

    def test_hand_shown_for_self(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        alice = gm.game.players[0]
        text = PerspectiveFilter.serialize_for_ai(gm, ids[0])
        assert f"Hand ({len(alice.hand)}):" in text
        # Should contain at least one card name from hand
        if alice.hand:
            assert alice.hand[0].name in text

    def test_opponent_hand_size_only(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        bob = gm.game.players[1]
        text = PerspectiveFilter.serialize_for_ai(gm, ids[0])
        assert f"Hand {len(bob.hand)}" in text
        # Bob's actual card names should NOT appear in the opponent section
        # (they might coincidentally appear in meadow, so we check the opponents section)
        opp_section = text.split("=== OPPONENTS ===")[1].split("=== VALID ACTIONS ===")[0]
        for card in bob.hand:
            # Card names shouldn't be listed in opponent section
            assert f"[{card.name}]" not in opp_section

    def test_not_your_turn(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        # Bob is not current player
        text = PerspectiveFilter.serialize_for_ai(gm, ids[1])
        assert "(not your turn)" in text

    def test_valid_actions_listed(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        text = PerspectiveFilter.serialize_for_ai(gm, ids[0])
        assert "PLACE_WORKER" in text or "PLAY_CARD" in text or "PREPARE_FOR_SEASON" in text

    def test_unknown_player_returns_error(self) -> None:
        gm = _make_gm()
        text = PerspectiveFilter.serialize_for_ai(gm, "nonexistent-uuid")
        assert "ERROR" in text

    def test_season_shown(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        text = PerspectiveFilter.serialize_for_ai(gm, ids[0])
        assert "Season: Winter" in text

    def test_workers_shown(self) -> None:
        gm = _make_gm()
        ids = _player_ids(gm)
        text = PerspectiveFilter.serialize_for_ai(gm, ids[0])
        assert "Workers: 2/2 available" in text
