from __future__ import annotations

from typing import Any

import pytest

from ed_engine.cards import register
from ed_engine.models.card import (
    BlueGovernanceCard,
    Card,
    GreenProductionCard,
    PurpleProsperityCard,
    RedDestinationCard,
    TanTravelerCard,
)
from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank


# ---------------------------------------------------------------------------
# Concrete test cards (minimal implementations for each type)
# ---------------------------------------------------------------------------


class _TestTanCard(TanTravelerCard):
    id: str = "tan-test"
    name: str = "Test Wanderer"
    category: CardCategory = CardCategory.CRITTER
    base_points: int = 1
    copies: int = 3

    def on_play(self, player: Player, **kwargs: Any) -> None:
        player.resources = player.resources.gain(ResourceBank(twig=2))


class _TestGreenCard(GreenProductionCard):
    id: str = "green-test"
    name: str = "Test Farm"
    category: CardCategory = CardCategory.CONSTRUCTION
    base_points: int = 1
    copies: int = 3
    cost: ResourceBank = ResourceBank(twig=1, resin=1)

    def on_trigger(self, player: Player, **kwargs: Any) -> None:
        player.resources = player.resources.gain(ResourceBank(berry=1))


class _TestRedCard(RedDestinationCard):
    id: str = "red-test"
    name: str = "Test Inn"
    category: CardCategory = CardCategory.CONSTRUCTION
    base_points: int = 2
    unique: bool = True

    def on_trigger(self, player: Player, **kwargs: Any) -> None:
        player.resources = player.resources.gain(ResourceBank(berry=2))


class _TestBlueCard(BlueGovernanceCard):
    id: str = "blue-test"
    name: str = "Test Judge"
    category: CardCategory = CardCategory.CRITTER
    base_points: int = 2
    unique: bool = True

    def on_score(self, player: Player, **kwargs: Any) -> int:
        # 1 VP per unique construction
        constructions = {c.name for c in player.city if c.category == CardCategory.CONSTRUCTION}
        return self.base_points + len(constructions)


class _TestPurpleCard(PurpleProsperityCard):
    id: str = "purple-test"
    name: str = "Test Palace"
    category: CardCategory = CardCategory.CONSTRUCTION
    base_points: int = 0
    unique: bool = True
    cost: ResourceBank = ResourceBank(twig=2, resin=3, pebble=3)

    def on_score(self, player: Player, **kwargs: Any) -> int:
        # 1 VP per unique construction in city
        constructions = {c.name for c in player.city if c.category == CardCategory.CONSTRUCTION}
        return len(constructions)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(**overrides: Any) -> Player:
    defaults: dict[str, Any] = {"name": "Alice"}
    defaults.update(overrides)
    return Player(**defaults)


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
        card.on_play(player)
        assert player.resources.twig == 2

    def test_on_trigger_is_noop(self) -> None:
        card = _TestTanCard()
        player = _make_player()
        card.on_trigger(player)  # should not raise
        assert player.resources.total() == 0

    def test_on_score_returns_base_points(self) -> None:
        card = _TestTanCard()
        player = _make_player()
        assert card.on_score(player) == 1


class TestGreenProductionCard:
    def test_card_type_is_green(self) -> None:
        card = _TestGreenCard()
        assert card.card_type == CardType.GREEN_PRODUCTION

    def test_on_play_is_noop(self) -> None:
        card = _TestGreenCard()
        player = _make_player()
        card.on_play(player)
        assert player.resources.total() == 0

    def test_on_trigger_produces_resources(self) -> None:
        card = _TestGreenCard()
        player = _make_player()
        card.on_trigger(player)
        assert player.resources.berry == 1

    def test_on_trigger_stacks(self) -> None:
        card = _TestGreenCard()
        player = _make_player()
        card.on_trigger(player)
        card.on_trigger(player)
        assert player.resources.berry == 2

    def test_on_score_returns_base_points(self) -> None:
        card = _TestGreenCard()
        player = _make_player()
        assert card.on_score(player) == 1


class TestRedDestinationCard:
    def test_card_type_is_red(self) -> None:
        card = _TestRedCard()
        assert card.card_type == CardType.RED_DESTINATION

    def test_on_play_is_noop(self) -> None:
        card = _TestRedCard()
        player = _make_player()
        card.on_play(player)
        assert player.resources.total() == 0

    def test_place_worker(self) -> None:
        card = _TestRedCard()
        card.place_worker("p1")
        assert card.occupied_by == "p1"

    def test_place_worker_when_occupied_raises(self) -> None:
        card = _TestRedCard()
        card.place_worker("p1")
        with pytest.raises(ValueError, match="already occupied"):
            card.place_worker("p2")

    def test_recall_worker(self) -> None:
        card = _TestRedCard()
        card.place_worker("p1")
        card.recall_worker()
        assert card.occupied_by is None

    def test_on_trigger_fires_on_worker_placement(self) -> None:
        card = _TestRedCard()
        player = _make_player()
        card.on_trigger(player)
        assert player.resources.berry == 2

    def test_on_score_returns_base_points(self) -> None:
        card = _TestRedCard()
        player = _make_player()
        assert card.on_score(player) == 2


class TestBlueGovernanceCard:
    def test_card_type_is_blue(self) -> None:
        card = _TestBlueCard()
        assert card.card_type == CardType.BLUE_GOVERNANCE

    def test_on_play_is_noop(self) -> None:
        card = _TestBlueCard()
        player = _make_player()
        card.on_play(player)
        assert player.resources.total() == 0

    def test_on_trigger_is_noop(self) -> None:
        card = _TestBlueCard()
        player = _make_player()
        card.on_trigger(player)
        assert player.resources.total() == 0

    def test_on_score_with_constructions(self) -> None:
        farm = _TestGreenCard()
        inn = _TestRedCard()
        blue = _TestBlueCard()
        player = _make_player(city=[farm, inn, blue])
        # 2 base + 2 unique constructions (farm, inn)
        assert blue.on_score(player) == 4

    def test_on_score_no_constructions(self) -> None:
        blue = _TestBlueCard()
        player = _make_player(city=[blue])
        # 2 base + 0 constructions
        assert blue.on_score(player) == 2


class TestPurpleProsperityCard:
    def test_card_type_is_purple(self) -> None:
        card = _TestPurpleCard()
        assert card.card_type == CardType.PURPLE_PROSPERITY

    def test_on_play_is_noop(self) -> None:
        card = _TestPurpleCard()
        player = _make_player()
        card.on_play(player)
        assert player.resources.total() == 0

    def test_on_trigger_is_noop(self) -> None:
        card = _TestPurpleCard()
        player = _make_player()
        card.on_trigger(player)
        assert player.resources.total() == 0

    def test_on_score_counts_constructions(self) -> None:
        farm = _TestGreenCard()
        inn = _TestRedCard()
        palace = _TestPurpleCard()
        player = _make_player(city=[farm, inn, palace])
        # 3 unique constructions (farm, inn, palace)
        assert palace.on_score(player) == 3

    def test_on_score_empty_city(self) -> None:
        palace = _TestPurpleCard()
        player = _make_player(city=[])
        assert palace.on_score(player) == 0


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
        class _RegisteredCard(TanTravelerCard):
            id: str = "reg-test"
            name: str = "Registered Wanderer"
            category: CardCategory = CardCategory.CRITTER

            def on_play(self, player: Player, **kwargs: Any) -> None:
                pass

        from ed_engine.cards import CardRegistry

        assert CardRegistry.get("Registered Wanderer") is _RegisteredCard


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

    def test_copies_default(self) -> None:
        card = _TestRedCard()
        assert card.copies == 1

    def test_copies_custom(self) -> None:
        card = _TestTanCard()
        assert card.copies == 3

    def test_cost(self) -> None:
        card = _TestGreenCard()
        assert card.cost == ResourceBank(twig=1, resin=1)
