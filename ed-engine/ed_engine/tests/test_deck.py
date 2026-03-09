import random

import pytest

from ed_engine.engine.deck import (
    HAND_LIMIT,
    MEADOW_SIZE,
    DeckManager,
    build_deck,
    deal_to_player,
    discard_cards,
    draw_cards,
    fill_meadow,
    setup_game,
    shuffle_deck,
    take_from_meadow,
)
from ed_engine.models.card import Card
from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.game import GameState
from ed_engine.models.player import Player


def _make_cards(n: int) -> list[Card]:
    """Create n simple test cards."""
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
# DeckManager (mutable class) tests
# ---------------------------------------------------------------------------
class TestDeckManager:
    def test_init_shuffles_and_fills_meadow(self) -> None:
        cards = _make_cards(20)
        dm = DeckManager(cards, seed=42)
        assert len(dm.meadow) == 8
        assert dm.deck_size == 12

    def test_draw_one(self) -> None:
        dm = DeckManager(_make_cards(20), seed=42)
        initial_deck = dm.deck_size
        drawn = dm.draw(1)
        assert len(drawn) == 1
        assert dm.deck_size == initial_deck - 1

    def test_draw_multiple(self) -> None:
        dm = DeckManager(_make_cards(20), seed=42)
        drawn = dm.draw(3)
        assert len(drawn) == 3

    def test_draw_from_empty_deck_shuffles_discard(self) -> None:
        cards = _make_cards(10)
        dm = DeckManager(cards, seed=42)
        assert dm.deck_size == 2
        dm.draw(2)
        assert dm.deck_size == 0
        dm.discard(_make_cards(5))
        assert dm.discard_size == 5
        drawn = dm.draw(3)
        assert len(drawn) == 3
        assert dm.discard_size == 0

    def test_draw_more_than_available(self) -> None:
        dm = DeckManager(_make_cards(10), seed=42)
        drawn = dm.draw(5)
        assert len(drawn) == 2

    def test_draw_from_meadow(self) -> None:
        dm = DeckManager(_make_cards(20), seed=42)
        meadow_before = dm.meadow
        card = dm.draw_from_meadow(0)
        assert card == meadow_before[0]
        assert len(dm.meadow) == 8
        assert dm.deck_size == 11

    def test_draw_from_meadow_invalid_index(self) -> None:
        dm = DeckManager(_make_cards(20), seed=42)
        with pytest.raises(IndexError):
            dm.draw_from_meadow(10)

    def test_draw_from_meadow_negative_index(self) -> None:
        dm = DeckManager(_make_cards(20), seed=42)
        with pytest.raises(IndexError):
            dm.draw_from_meadow(-1)

    def test_discard(self) -> None:
        dm = DeckManager(_make_cards(20), seed=42)
        discarded = _make_cards(3)
        dm.discard(discarded)
        assert dm.discard_size == 3

    def test_meadow_property_returns_copy(self) -> None:
        dm = DeckManager(_make_cards(20), seed=42)
        m1 = dm.meadow
        m2 = dm.meadow
        assert m1 is not m2

    def test_seed_reproducibility(self) -> None:
        cards = _make_cards(20)
        dm1 = DeckManager(list(cards), seed=99)
        dm2 = DeckManager(list(cards), seed=99)
        assert [c.name for c in dm1.meadow] == [c.name for c in dm2.meadow]

    def test_replenish_meadow_partial(self) -> None:
        dm = DeckManager(_make_cards(9), seed=42)
        assert len(dm.meadow) == 8
        assert dm.deck_size == 1
        dm.draw_from_meadow(0)
        assert len(dm.meadow) == 8

    def test_empty_deck_and_discard(self) -> None:
        dm = DeckManager(_make_cards(8), seed=42)
        assert dm.deck_size == 0
        assert dm.discard_size == 0
        drawn = dm.draw(1)
        assert len(drawn) == 0


# ---------------------------------------------------------------------------
# Functional (GameState-based) tests
# ---------------------------------------------------------------------------
class TestBuildDeckEngine:
    def test_build_deck_returns_cards(self) -> None:
        deck = build_deck()
        assert len(deck) > 0
        assert all(isinstance(c, Card) for c in deck)

    def test_has_critters_and_constructions(self) -> None:
        deck = build_deck()
        critters = [c for c in deck if c.category == CardCategory.CRITTER]
        constructions = [c for c in deck if c.category == CardCategory.CONSTRUCTION]
        assert len(critters) > 0
        assert len(constructions) > 0

    def test_all_five_card_types_present(self) -> None:
        deck = build_deck()
        types = {c.card_type for c in deck}
        assert types == {
            CardType.TAN_TRAVELER,
            CardType.GREEN_PRODUCTION,
            CardType.RED_DESTINATION,
            CardType.BLUE_GOVERNANCE,
            CardType.PURPLE_PROSPERITY,
        }


class TestShuffleDeck:
    def test_shuffle_preserves_count(self) -> None:
        deck = build_deck()
        shuffled = shuffle_deck(deck)
        assert len(shuffled) == len(deck)

    def test_shuffle_does_not_mutate_original(self) -> None:
        deck = build_deck()
        original_names = [c.name for c in deck]
        shuffle_deck(deck)
        assert [c.name for c in deck] == original_names

    def test_deterministic_with_rng(self) -> None:
        deck = build_deck()
        s1 = shuffle_deck(deck, rng=random.Random(42))
        s2 = shuffle_deck(deck, rng=random.Random(42))
        assert [c.name for c in s1] == [c.name for c in s2]

    def test_different_seeds_give_different_order(self) -> None:
        deck = build_deck()
        s1 = shuffle_deck(deck, rng=random.Random(1))
        s2 = shuffle_deck(deck, rng=random.Random(2))
        assert [c.name for c in s1] != [c.name for c in s2]


class TestDrawCards:
    def _make_game(self, deck_size: int = 10) -> GameState:
        deck = _make_cards(deck_size)
        return GameState(deck=deck)

    def test_draw_reduces_deck(self) -> None:
        game = self._make_game(10)
        game, drawn = draw_cards(game, 3)
        assert len(drawn) == 3
        assert len(game.deck) == 7

    def test_draw_from_top(self) -> None:
        game = self._make_game(10)
        expected_names = [c.name for c in game.deck[:3]]
        game, drawn = draw_cards(game, 3)
        assert [c.name for c in drawn] == expected_names

    def test_draw_empty_deck_reshuffles_discard(self) -> None:
        deck = _make_cards(2)
        discard = _make_cards(5)
        game = GameState(deck=deck, discard=discard)
        game, drawn = draw_cards(game, 4)
        assert len(drawn) == 4
        assert len(game.discard) == 0
        assert len(game.deck) == 3

    def test_draw_more_than_available(self) -> None:
        game = self._make_game(3)
        game, drawn = draw_cards(game, 5)
        assert len(drawn) == 3
        assert len(game.deck) == 0

    def test_draw_from_empty_deck_and_discard(self) -> None:
        game = GameState()
        game, drawn = draw_cards(game, 3)
        assert len(drawn) == 0


class TestMeadow:
    def test_fill_meadow_to_eight(self) -> None:
        deck = _make_cards(20)
        game = GameState(deck=deck)
        game = fill_meadow(game)
        assert len(game.meadow) == MEADOW_SIZE
        assert len(game.deck) == 12

    def test_fill_meadow_partial(self) -> None:
        deck = _make_cards(5)
        game = GameState(deck=deck)
        game = fill_meadow(game)
        assert len(game.meadow) == 5
        assert len(game.deck) == 0

    def test_fill_meadow_already_full(self) -> None:
        cards = _make_cards(20)
        game = GameState(deck=cards[:8], meadow=cards[8:16])
        original_deck_len = len(game.deck)
        game = fill_meadow(game)
        assert len(game.meadow) == MEADOW_SIZE
        assert len(game.deck) == original_deck_len

    def test_take_from_meadow_replenishes(self) -> None:
        cards = _make_cards(20)
        game = GameState(deck=cards[:12], meadow=cards[12:20])
        game, taken = take_from_meadow(game, 0)
        assert taken is not None
        assert len(game.meadow) == MEADOW_SIZE
        assert len(game.deck) == 11

    def test_take_from_meadow_returns_correct_card(self) -> None:
        cards = _make_cards(20)
        meadow = cards[12:20]
        game = GameState(deck=cards[:12], meadow=meadow)
        target_name = meadow[3].name
        game, taken = take_from_meadow(game, 3)
        assert taken.name == target_name

    def test_take_from_meadow_invalid_index(self) -> None:
        cards = _make_cards(8)
        game = GameState(meadow=cards)
        with pytest.raises(IndexError):
            take_from_meadow(game, 10)

    def test_take_from_meadow_negative_index(self) -> None:
        cards = _make_cards(8)
        game = GameState(meadow=cards)
        with pytest.raises(IndexError):
            take_from_meadow(game, -1)


class TestDiscard:
    def test_discard_adds_to_pile(self) -> None:
        cards = _make_cards(5)
        game = GameState()
        game = discard_cards(game, cards[:3])
        assert len(game.discard) == 3

    def test_discard_appends_to_existing(self) -> None:
        cards = _make_cards(5)
        game = GameState(discard=cards[:2])
        game = discard_cards(game, cards[2:5])
        assert len(game.discard) == 5

    def test_discard_does_not_mutate_original(self) -> None:
        game = GameState()
        cards = _make_cards(3)
        new_game = discard_cards(game, cards)
        assert len(game.discard) == 0
        assert len(new_game.discard) == 3


class TestDealToPlayer:
    def test_deal_cards_to_hand(self) -> None:
        deck = _make_cards(20)
        player = Player(name="Alice")
        game = GameState(deck=deck, players=[player])
        game = deal_to_player(game, 0, 5)
        assert len(game.players[0].hand) == 5
        assert len(game.deck) == 15

    def test_deal_respects_hand_limit(self) -> None:
        deck = _make_cards(20)
        player = Player(name="Alice")
        game = GameState(deck=deck, players=[player])
        game = deal_to_player(game, 0, 10)
        assert len(game.players[0].hand) == HAND_LIMIT
        assert len(game.discard) == 2

    def test_deal_adds_to_existing_hand(self) -> None:
        cards = _make_cards(20)
        hand = cards[:3]
        player = Player(name="Alice", hand=hand)
        game = GameState(deck=cards[3:], players=[player])
        game = deal_to_player(game, 0, 2)
        assert len(game.players[0].hand) == 5


class TestSetupGame:
    def test_setup_two_players(self) -> None:
        game = setup_game(["Alice", "Bob"], rng=random.Random(42))
        assert len(game.players) == 2
        assert len(game.meadow) == MEADOW_SIZE
        assert game.players[0].name == "Alice"
        assert game.players[1].name == "Bob"
        assert len(game.players[0].hand) == 5
        assert len(game.players[1].hand) == 6
        # Total cards minus meadow and hands
        deck = build_deck()
        expected_deck = len(deck) - 8 - 5 - 6
        assert len(game.deck) == expected_deck

    def test_setup_four_players(self) -> None:
        game = setup_game(["A", "B", "C", "D"], rng=random.Random(42))
        assert len(game.players) == 4
        assert len(game.meadow) == MEADOW_SIZE
        assert len(game.players[0].hand) == 5
        assert len(game.players[1].hand) == 6
        assert len(game.players[2].hand) == 7
        assert len(game.players[3].hand) == 8

    def test_setup_one_player(self) -> None:
        game = setup_game(["Solo"], rng=random.Random(42))
        assert len(game.players) == 1
        assert len(game.players[0].hand) == 5

    def test_setup_invalid_player_count(self) -> None:
        with pytest.raises(ValueError, match="1-4 players"):
            setup_game([])
        with pytest.raises(ValueError, match="1-4 players"):
            setup_game(["A", "B", "C", "D", "E"])

    def test_setup_deterministic(self) -> None:
        g1 = setup_game(["A", "B"], rng=random.Random(99))
        g2 = setup_game(["A", "B"], rng=random.Random(99))
        assert [c.name for c in g1.deck] == [c.name for c in g2.deck]
        assert [c.name for c in g1.meadow] == [c.name for c in g2.meadow]
        for i in range(2):
            assert [c.name for c in g1.players[i].hand] == [
                c.name for c in g2.players[i].hand
            ]

    def test_setup_total_cards_preserved(self) -> None:
        game = setup_game(["A", "B", "C"], rng=random.Random(42))
        total = (
            len(game.deck)
            + len(game.meadow)
            + len(game.discard)
            + sum(len(p.hand) for p in game.players)
        )
        expected = len(build_deck())
        assert total == expected


class TestDeckReshuffle:
    def test_reshuffle_on_draw_through_deck(self) -> None:
        """When deck runs out mid-draw, discard becomes new deck."""
        small_deck = _make_cards(2)
        discard = _make_cards(5)
        game = GameState(deck=small_deck, discard=discard)
        game, drawn = draw_cards(game, 5)
        assert len(drawn) == 5
        assert len(game.deck) == 2
        assert len(game.discard) == 0
