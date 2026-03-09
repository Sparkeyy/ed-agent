from __future__ import annotations

import random

from ed_engine.models.card import Card


class DeckManager:
    """Manages the draw deck, meadow (8 face-up cards), and discard pile."""

    MEADOW_SIZE = 8

    def __init__(self, cards: list[Card], seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._deck: list[Card] = list(cards)
        self._rng.shuffle(self._deck)
        self._meadow: list[Card] = []
        self._discard: list[Card] = []
        # Fill the initial meadow
        self.replenish_meadow()

    def draw(self, n: int = 1) -> list[Card]:
        """Draw n cards from the top of the deck. If deck runs out, shuffle discard in."""
        drawn: list[Card] = []
        for _ in range(n):
            if not self._deck and self._discard:
                self._deck = self._discard
                self._discard = []
                self._rng.shuffle(self._deck)
            if self._deck:
                drawn.append(self._deck.pop())
            else:
                break
        return drawn

    def draw_from_meadow(self, index: int) -> Card:
        """Take a card from the meadow at the given index, then replenish."""
        if index < 0 or index >= len(self._meadow):
            raise IndexError(f"Meadow index {index} out of range")
        card = self._meadow.pop(index)
        self.replenish_meadow()
        return card

    def replenish_meadow(self) -> None:
        """Fill the meadow back up to 8 cards from the deck."""
        while len(self._meadow) < self.MEADOW_SIZE:
            cards = self.draw(1)
            if not cards:
                break
            self._meadow.append(cards[0])

    def discard(self, cards: list[Card]) -> None:
        """Add cards to the discard pile."""
        self._discard.extend(cards)

    @property
    def meadow(self) -> list[Card]:
        return list(self._meadow)

    @property
    def deck_size(self) -> int:
        return len(self._deck)

    @property
    def discard_size(self) -> int:
        return len(self._discard)
