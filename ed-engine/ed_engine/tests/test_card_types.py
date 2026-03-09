"""Tests for the card type system, registry, and pairing."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import pytest

from ed_engine.cards import register
from ed_engine.cards.base import (
    DestinationCard,
    GovernanceCard,
    ProductionCard,
    ProsperityCard,
    TravelerCard,
)
from ed_engine.models.card import Card
from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.game import GameState
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank


# ---------------------------------------------------------------------------
# Concrete test cards (minimal implementations for each type)
# ---------------------------------------------------------------------------


class _TestTanCard(TravelerCard):
    name: str = "Test Wanderer"
    category: CardCategory = CardCategory.CRITTER
    base_points: int = 1
    copies_in_deck: int = 3

    def on_play(self, game: GameState, player: Player) -> None:
        player.resources = player.resources.gain(ResourceBank(twig=2))


class _TestGreenCard(ProductionCard):
    name: str = "Test Farm"
    category: CardCategory = CardCategory.CONSTRUCTION
    base_points: int = 1
    copies_in_deck: int = 3
    cost: ResourceBank = ResourceBank(twig=1, resin=1)

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        player.resources = player.resources.gain(ResourceBank(berry=1))


class _TestRedCard(DestinationCard):
    name: str = "Test Inn"
    category: CardCategory = CardCategory.CONSTRUCTION
    base_points: int = 2
    unique: bool = True

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player
    ) -> None:
        player.resources = player.resources.gain(ResourceBank(berry=2))


class _TestBlueCard(GovernanceCard):
    name: str = "Test Judge"
    category: CardCategory = CardCategory.CRITTER
    base_points: int = 2
    unique: bool = True

    def on_score(self, game: GameState, player: Player) -> int:
        constructions = {
            c.name for c in player.city if c.category == CardCategory.CONSTRUCTION
        }
        return len(constructions)


class _TestPurpleCard(ProsperityCard):
    name: str = "Test Palace"
    category: CardCategory = CardCategory.CONSTRUCTION
    base_points: int = 0
    unique: bool = True
    cost: ResourceBank = ResourceBank(twig=2, resin=3, pebble=3)

    def on_score(self, game: GameState, player: Player) -> int:
        constructions = {
            c.name for c in player.city if c.category == CardCategory.CONSTRUCTION
        }
        return len(constructions)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(**overrides: Any) -> Player:
    defaults: dict[str, Any] = {"name": "Alice"}
    defaults.update(overrides)
    return Player(**defaults)


def _make_game(**overrides: Any) -> GameState:
    return GameState(**overrides)


# ---------------------------------------------------------------------------
# Tests — Card type defaults
# ---------------------------------------------------------------------------


class TestTanTravelerCard:
    def test_card_type_is_tan(self) -> None:
        card = _TestTanCard()
        assert card.card_type == CardType.TAN_TRAVELER

    def test_on_play_fires_effect(self) -> None:
        card = _TestTanCard()
        player = _make_player()
        game = _make_game()
        card.on_play(game, player)
        assert player.resources.twig == 2

    def test_on_score_returns_zero_by_default(self) -> None:
        card = _TestTanCard()
        player = _make_player()
        game = _make_game()
        assert card.on_score(game, player) == 0


class TestGreenProductionCard:
    def test_card_type_is_green(self) -> None:
        card = _TestGreenCard()
        assert card.card_type == CardType.GREEN_PRODUCTION

    def test_on_play_triggers_production(self) -> None:
        card = _TestGreenCard()
        player = _make_player()
        game = _make_game()
        card.on_play(game, player)
        assert player.resources.berry == 1

    def test_on_production_produces_resources(self) -> None:
        card = _TestGreenCard()
        player = _make_player()
        game = _make_game()
        card.on_production(game, player)
        assert player.resources.berry == 1

    def test_on_production_stacks(self) -> None:
        card = _TestGreenCard()
        player = _make_player()
        game = _make_game()
        card.on_production(game, player)
        card.on_production(game, player)
        assert player.resources.berry == 2


class TestRedDestinationCard:
    def test_card_type_is_red(self) -> None:
        card = _TestRedCard()
        assert card.card_type == CardType.RED_DESTINATION

    def test_on_worker_placed_fires_effect(self) -> None:
        card = _TestRedCard()
        player = _make_player()
        game = _make_game()
        card.on_worker_placed(game, player, player)
        assert player.resources.berry == 2


class TestBlueGovernanceCard:
    def test_card_type_is_blue(self) -> None:
        card = _TestBlueCard()
        assert card.card_type == CardType.BLUE_GOVERNANCE

    def test_on_score_with_constructions(self) -> None:
        farm = _TestGreenCard()
        inn = _TestRedCard()
        blue = _TestBlueCard()
        player = _make_player(city=[farm, inn, blue])
        game = _make_game()
        # 2 constructions (farm, inn)
        assert blue.on_score(game, player) == 2

    def test_on_score_no_constructions(self) -> None:
        blue = _TestBlueCard()
        player = _make_player(city=[blue])
        game = _make_game()
        assert blue.on_score(game, player) == 0


class TestPurpleProsperityCard:
    def test_card_type_is_purple(self) -> None:
        card = _TestPurpleCard()
        assert card.card_type == CardType.PURPLE_PROSPERITY

    def test_on_score_counts_constructions(self) -> None:
        farm = _TestGreenCard()
        inn = _TestRedCard()
        palace = _TestPurpleCard()
        player = _make_player(city=[farm, inn, palace])
        game = _make_game()
        # 3 constructions (farm, inn, palace)
        assert palace.on_score(game, player) == 3

    def test_on_score_empty_city(self) -> None:
        palace = _TestPurpleCard()
        player = _make_player(city=[])
        game = _make_game()
        assert palace.on_score(game, player) == 0


# ---------------------------------------------------------------------------
# Tests — Card pairing system
# ---------------------------------------------------------------------------


class TestCardPairing:
    def test_critter_paired_with_construction(self) -> None:
        card = _TestTanCard(paired_with="Test Farm")
        assert card.paired_with == "Test Farm"
        assert card.category == CardCategory.CRITTER

    def test_construction_paired_with_critter(self) -> None:
        card = _TestGreenCard(paired_with="Test Wanderer")
        assert card.paired_with == "Test Wanderer"
        assert card.category == CardCategory.CONSTRUCTION

    def test_unpaired_card(self) -> None:
        card = _TestTanCard()
        assert card.paired_with is None


# ---------------------------------------------------------------------------
# Tests — Card registration
# ---------------------------------------------------------------------------


class TestCardRegistration:
    def test_register_card(self) -> None:
        @register
        class _RegisteredCard(TravelerCard):
            name: str = "Registered Wanderer"
            category: CardCategory = CardCategory.CRITTER

        from ed_engine.cards import CardRegistry, _registry

        assert CardRegistry.get("Registered Wanderer") is _RegisteredCard

        # Clean up to avoid polluting other tests that call build_deck()
        _registry.pop("Registered Wanderer", None)


# ---------------------------------------------------------------------------
# Tests — Card uniqueness and copies
# ---------------------------------------------------------------------------


class TestCardAttributes:
    def test_unique_default_false(self) -> None:
        card = _TestTanCard()
        assert card.unique is False

    def test_unique_set_true(self) -> None:
        card = _TestRedCard()
        assert card.unique is True

    def test_copies_in_deck_default(self) -> None:
        card = _TestRedCard()
        assert card.copies_in_deck == 1

    def test_copies_in_deck_custom(self) -> None:
        card = _TestTanCard()
        assert card.copies_in_deck == 3

    def test_cost(self) -> None:
        card = _TestGreenCard()
        assert card.cost == ResourceBank(twig=1, resin=1)
