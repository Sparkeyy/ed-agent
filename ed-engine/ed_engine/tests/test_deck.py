import pytest

from ed_engine.engine.deck import DeckManager
from ed_engine.models.card import Card
from ed_engine.models.enums import CardCategory, CardType


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


class TestDeckManager:
    def test_init_shuffles_and_fills_meadow(self) -> None:
        cards = _make_cards(20)
        dm = DeckManager(cards, seed=42)
        assert len(dm.meadow) == 8
        assert dm.deck_size == 12  # 20 - 8

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
        # Meadow takes 8, deck has 2
        assert dm.deck_size == 2
        # Draw remaining 2
        dm.draw(2)
        assert dm.deck_size == 0
        # Add some to discard
        dm.discard(_make_cards(5))
        assert dm.discard_size == 5
        # Drawing should shuffle discard into deck
        drawn = dm.draw(3)
        assert len(drawn) == 3
        assert dm.discard_size == 0

    def test_draw_more_than_available(self) -> None:
        dm = DeckManager(_make_cards(10), seed=42)
        # 2 in deck, 0 in discard
        drawn = dm.draw(5)
        assert len(drawn) == 2

    def test_draw_from_meadow(self) -> None:
        dm = DeckManager(_make_cards(20), seed=42)
        meadow_before = dm.meadow
        card = dm.draw_from_meadow(0)
        assert card == meadow_before[0]
        # Meadow should still be 8 (replenished)
        assert len(dm.meadow) == 8
        assert dm.deck_size == 11  # one drawn to replenish

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
        assert m1 is not m2  # different list objects

    def test_seed_reproducibility(self) -> None:
        cards = _make_cards(20)
        dm1 = DeckManager(list(cards), seed=99)
        dm2 = DeckManager(list(cards), seed=99)
        assert [c.name for c in dm1.meadow] == [c.name for c in dm2.meadow]

    def test_replenish_meadow_partial(self) -> None:
        """If deck is nearly empty, meadow may have fewer than 8."""
        dm = DeckManager(_make_cards(9), seed=42)
        # 8 in meadow, 1 in deck
        assert len(dm.meadow) == 8
        assert dm.deck_size == 1
        # Take from meadow
        dm.draw_from_meadow(0)
        # Replenished from the 1 remaining card
        assert len(dm.meadow) == 8

    def test_empty_deck_and_discard(self) -> None:
        dm = DeckManager(_make_cards(8), seed=42)
        # All 8 in meadow, 0 in deck
        assert dm.deck_size == 0
        assert dm.discard_size == 0
        drawn = dm.draw(1)
        assert len(drawn) == 0
