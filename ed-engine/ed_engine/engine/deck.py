"""Deck, Meadow, and discard pile management for Everdell.

Rules (from rulebook):
- Deck: 128 shuffled cards. Draw from the top.
- Meadow: 8 face-up cards. When a card is taken, immediately replace it
  from the deck.
- Discard pile: cards discarded face-down. If the deck runs out, shuffle
  the discard pile to form a new deck.
- Hand limit: 8 cards. Cannot exceed this when drawing.
- Setup: deal 8 cards to meadow, then 5/6/7/8 to players by turn order.
"""

from __future__ import annotations

import random
from typing import Any
from uuid import uuid4

from ed_engine.cards.card_data import ALL_CARD_DEFS, CardDef
from ed_engine.models.card import Card
from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.game import GameState
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank

MEADOW_SIZE = 8
HAND_LIMIT = 8
# Cards dealt per player by turn order (1st player gets fewest)
STARTING_HAND_SIZES = [5, 6, 7, 8]


class _ConcreteCard(Card):
    """Instantiable Card with stub ability methods.

    Used to populate the deck from card data definitions. Individual card
    ability implementations will override these stubs in future work.
    """

    def on_play(self, **kwargs: Any) -> None:
        pass

    def on_trigger(self, **kwargs: Any) -> None:
        pass

    def on_score(self, **kwargs: Any) -> int:
        return 0


def _card_from_def(card_def: CardDef, copy_index: int) -> _ConcreteCard:
    """Create a card instance from a card definition."""
    return _ConcreteCard(
        id=f"{card_def['name'].lower().replace(' ', '_')}_{copy_index}",
        name=card_def["name"],
        card_type=CardType(card_def["card_type"]),
        category=CardCategory(card_def["category"]),
        cost=ResourceBank(
            twig=card_def["cost_twig"],
            resin=card_def["cost_resin"],
            pebble=card_def["cost_pebble"],
            berry=card_def["cost_berry"],
        ),
        base_points=card_def["base_points"],
        paired_with=card_def["paired_with"],
        unique=card_def["unique"],
        copies=card_def["copies"],
    )


def build_deck() -> list[Card]:
    """Create all 128 cards (unshuffled)."""
    deck: list[Card] = []
    for card_def in ALL_CARD_DEFS:
        for i in range(card_def["copies"]):
            deck.append(_card_from_def(card_def, i))
    return deck


def shuffle_deck(deck: list[Card], rng: random.Random | None = None) -> list[Card]:
    """Return a new shuffled copy of the deck."""
    shuffled = list(deck)
    if rng is not None:
        rng.shuffle(shuffled)
    else:
        random.shuffle(shuffled)
    return shuffled


def draw_cards(game: GameState, count: int) -> tuple[GameState, list[Card]]:
    """Draw cards from the deck, reshuffling discard if needed.

    Returns (updated_game_state, drawn_cards). If both deck and discard
    are empty, returns as many cards as available.
    """
    deck = list(game.deck)
    discard = list(game.discard)
    drawn: list[Card] = []

    for _ in range(count):
        if not deck:
            if not discard:
                break  # No cards left anywhere
            # Reshuffle discard into deck
            deck = discard
            random.shuffle(deck)
            discard = []
        drawn.append(deck.pop(0))

    return (
        game.model_copy(update={"deck": deck, "discard": discard}),
        drawn,
    )


def deal_to_player(
    game: GameState, player_idx: int, count: int
) -> GameState:
    """Deal cards from the deck to a player's hand, respecting hand limit.

    Cards that would exceed HAND_LIMIT are discarded instead.
    """
    game, drawn = draw_cards(game, count)
    player = game.players[player_idx]
    space = HAND_LIMIT - len(player.hand)
    to_hand = drawn[:space]
    to_discard = drawn[space:]

    updated_player = player.model_copy(
        update={"hand": list(player.hand) + to_hand}
    )
    players = list(game.players)
    players[player_idx] = updated_player

    return game.model_copy(
        update={
            "players": players,
            "discard": list(game.discard) + to_discard,
        }
    )


def fill_meadow(game: GameState) -> GameState:
    """Fill the meadow to MEADOW_SIZE cards from the deck.

    If the deck and discard are both empty, meadow may have fewer than 8.
    """
    meadow = list(game.meadow)
    needed = MEADOW_SIZE - len(meadow)
    if needed <= 0:
        return game

    game, drawn = draw_cards(game, needed)
    return game.model_copy(update={"meadow": list(game.meadow) + drawn})


def take_from_meadow(game: GameState, card_index: int) -> tuple[GameState, Card]:
    """Remove a card from the meadow by index and replenish.

    Returns (updated_game_state, taken_card).
    Raises IndexError if card_index is out of range.
    """
    meadow = list(game.meadow)
    if card_index < 0 or card_index >= len(meadow):
        raise IndexError(
            f"Meadow index {card_index} out of range (meadow has {len(meadow)} cards)"
        )
    taken = meadow.pop(card_index)
    game = game.model_copy(update={"meadow": meadow})
    game = fill_meadow(game)
    return game, taken


def discard_cards(game: GameState, cards: list[Card]) -> GameState:
    """Add cards to the discard pile."""
    return game.model_copy(
        update={"discard": list(game.discard) + cards}
    )


def setup_game(player_names: list[str], rng: random.Random | None = None) -> GameState:
    """Set up a new game: build deck, shuffle, deal meadow and hands.

    Args:
        player_names: 1-4 player names.
        rng: Optional random source for deterministic shuffling (tests).

    Returns:
        Fully initialized GameState ready to play.
    """
    if not (1 <= len(player_names) <= 4):
        raise ValueError("Everdell supports 1-4 players")

    # Build and shuffle deck
    deck = build_deck()
    deck = shuffle_deck(deck, rng=rng)

    # Create players
    players = [Player(name=name) for name in player_names]

    # Initialize game state
    game = GameState(players=players, deck=deck)

    # Fill meadow (8 cards)
    game = fill_meadow(game)

    # Deal starting hands (5/6/7/8 cards by turn order)
    for i, player in enumerate(players):
        hand_size = STARTING_HAND_SIZES[i] if i < len(STARTING_HAND_SIZES) else 5
        game = deal_to_player(game, i, hand_size)

    return game


class DeckManager:
    """Mutable deck manager for use outside GameState operations.

    Wraps the same deck/meadow/discard logic in a stateful class.
    """

    MEADOW_SIZE = MEADOW_SIZE

    def __init__(self, cards: list[Card], seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._deck: list[Card] = list(cards)
        self._rng.shuffle(self._deck)
        self._meadow: list[Card] = []
        self._discard: list[Card] = []
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
