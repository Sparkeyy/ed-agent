"""Tests for the card type system, registry, and deck building."""

from __future__ import annotations

import pytest

from ed_engine.cards import CardRegistry, build_deck, get_card_definition
from ed_engine.cards.base import (
    DestinationCard,
    GovernanceCard,
    ProductionCard,
    ProsperityCard,
    TravelerCard,
)
from ed_engine.models.card import Card
from ed_engine.models.enums import CardCategory, CardType, Season
from ed_engine.models.game import GameState
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank

# Force registration of all cards
import ed_engine.cards.constructions  # noqa: F401
import ed_engine.cards.critters  # noqa: F401


def _make_player(**kwargs) -> Player:
    defaults = dict(name="Alice", resources=ResourceBank())
    defaults.update(kwargs)
    return Player(**defaults)


def _make_game(**kwargs) -> GameState:
    return GameState(**kwargs)


# ---------------------------------------------------------------------------
# Card creation
# ---------------------------------------------------------------------------


class TestCardCreation:
    def test_farm_fields(self) -> None:
        farm = get_card_definition("Farm")
        assert farm.name == "Farm"
        assert farm.card_type == CardType.GREEN_PRODUCTION
        assert farm.category == CardCategory.CONSTRUCTION
        assert farm.cost == ResourceBank(twig=2, resin=1)
        assert farm.base_points == 1
        assert farm.unique is False
        assert farm.copies_in_deck == 8
        assert farm.paired_with == "Husband"
        assert farm.occupies_city_space is True

    def test_wanderer_no_city_space(self) -> None:
        w = get_card_definition("Wanderer")
        assert w.occupies_city_space is False

    def test_inn_open_destination(self) -> None:
        inn = get_card_definition("Inn")
        assert inn.is_open_destination is True

    def test_post_office_open_destination(self) -> None:
        po = get_card_definition("Post Office")
        assert po.is_open_destination is True

    def test_fool_negative_points(self) -> None:
        fool = get_card_definition("Fool")
        assert fool.base_points == -2

    def test_unique_card_correct_copies(self) -> None:
        """Unique cards have 2 copies, except Clock Tower/Crane/Fair Grounds/
        Historian/Innkeeper/Shopkeeper which have 3."""
        three_copy_uniques = {
            "Clock Tower", "Crane", "Fair Grounds",
            "Historian", "Innkeeper", "Shopkeeper",
        }
        for name, cls in CardRegistry.all().items():
            instance = cls()
            if instance.unique:
                if name in three_copy_uniques:
                    assert instance.copies_in_deck == 3, (
                        f"{name} should have 3 copies"
                    )
                else:
                    assert instance.copies_in_deck == 2, (
                        f"{name} should have 2 copies"
                    )

    def test_common_card_copies(self) -> None:
        """Common cards have specific copy counts: Farm=8, Husband=4, Wife=4,
        others=3."""
        special_counts = {"Farm": 8, "Husband": 4, "Wife": 4}
        for name, cls in CardRegistry.all().items():
            instance = cls()
            if not instance.unique:
                expected = special_counts.get(name, 3)
                assert instance.copies_in_deck == expected, (
                    f"{name} should have {expected} copies, got {instance.copies_in_deck}"
                )


# ---------------------------------------------------------------------------
# Card type subclasses
# ---------------------------------------------------------------------------


class TestCardTypeSubclasses:
    def test_traveler_card_type(self) -> None:
        card = TravelerCard(
            name="Test", category=CardCategory.CONSTRUCTION
        )
        assert card.card_type == CardType.TAN_TRAVELER

    def test_production_card_type(self) -> None:
        card = ProductionCard(
            name="Test", category=CardCategory.CONSTRUCTION
        )
        assert card.card_type == CardType.GREEN_PRODUCTION

    def test_destination_card_type(self) -> None:
        card = DestinationCard(
            name="Test", category=CardCategory.CONSTRUCTION
        )
        assert card.card_type == CardType.RED_DESTINATION

    def test_governance_card_type(self) -> None:
        card = GovernanceCard(
            name="Test", category=CardCategory.CONSTRUCTION
        )
        assert card.card_type == CardType.BLUE_GOVERNANCE

    def test_prosperity_card_type(self) -> None:
        card = ProsperityCard(
            name="Test", category=CardCategory.CONSTRUCTION
        )
        assert card.card_type == CardType.PURPLE_PROSPERITY

    def test_production_on_play_triggers_production(self) -> None:
        """ProductionCard.on_play should call on_production."""
        farm = get_card_definition("Farm")
        player = _make_player()
        game = _make_game()
        farm.on_play(game, player)
        assert player.resources.berry == 1


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestCardRegistry:
    def test_register_and_lookup(self) -> None:
        cls = CardRegistry.get("Farm")
        assert cls is not None
        assert cls.model_fields["name"].default == "Farm"

    def test_lookup_missing_returns_none(self) -> None:
        assert CardRegistry.get("Nonexistent Card") is None

    def test_get_card_definition(self) -> None:
        card = get_card_definition("Mine")
        assert isinstance(card, Card)
        assert card.name == "Mine"

    def test_get_card_definition_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown card"):
            get_card_definition("Not A Real Card")

    def test_all_registered_cards_have_names(self) -> None:
        for name, cls in CardRegistry.all().items():
            instance = cls()
            assert instance.name == name


# ---------------------------------------------------------------------------
# Deck building
# ---------------------------------------------------------------------------


class TestBuildDeck:
    def test_deck_size_128(self) -> None:
        """Deck should contain exactly 128 cards (standard Everdell base game)."""
        deck = build_deck()
        assert len(deck) == 128, f"Deck has {len(deck)} cards, expected 128"

    def test_construction_copies_total_65(self) -> None:
        """All constructions should sum to 65 copies."""
        deck = build_deck()
        construction_count = sum(
            1 for c in deck if c.category == CardCategory.CONSTRUCTION
        )
        assert construction_count == 65, (
            f"Constructions: {construction_count}, expected 65"
        )

    def test_critter_copies_total_63(self) -> None:
        """All critters should sum to 63 copies."""
        deck = build_deck()
        critter_count = sum(
            1 for c in deck if c.category == CardCategory.CRITTER
        )
        assert critter_count == 63, (
            f"Critters: {critter_count}, expected 63"
        )

    def test_farm_has_8_copies(self) -> None:
        deck = build_deck()
        farm_count = sum(1 for c in deck if c.name == "Farm")
        assert farm_count == 8

    def test_husband_has_4_copies(self) -> None:
        deck = build_deck()
        husband_count = sum(1 for c in deck if c.name == "Husband")
        assert husband_count == 4

    def test_wife_has_4_copies(self) -> None:
        deck = build_deck()
        wife_count = sum(1 for c in deck if c.name == "Wife")
        assert wife_count == 4

    def test_deck_has_constructions_and_critters(self) -> None:
        deck = build_deck()
        categories = {c.category for c in deck}
        assert CardCategory.CONSTRUCTION in categories
        assert CardCategory.CRITTER in categories

    def test_deck_has_all_five_types(self) -> None:
        deck = build_deck()
        types = {c.card_type for c in deck}
        assert types == {
            CardType.TAN_TRAVELER,
            CardType.GREEN_PRODUCTION,
            CardType.RED_DESTINATION,
            CardType.BLUE_GOVERNANCE,
            CardType.PURPLE_PROSPERITY,
        }

    def test_correct_pairings_bidirectional(self) -> None:
        """Every pairing should be bidirectional: if A pairs with B, B pairs with A.

        Special case: Farm pairs with Husband (primary), but Wife also pairs
        with Farm. This many-to-one relationship is expected.
        """
        # Cards where multiple critters pair with one construction
        many_to_one = {"Wife": "Farm"}  # Wife->Farm is valid even though Farm->Husband

        all_cards = CardRegistry.all()
        for name, cls in all_cards.items():
            instance = cls()
            if instance.paired_with is not None:
                partner_name = instance.paired_with
                # Ever Tree pairs with any critter — skip
                if partner_name not in all_cards:
                    continue
                # Skip known many-to-one pairings
                if name in many_to_one:
                    assert many_to_one[name] == partner_name, (
                        f"{name} should pair with {many_to_one[name]}, "
                        f"got {partner_name}"
                    )
                    continue
                partner_cls = all_cards[partner_name]
                partner = partner_cls()
                assert partner.paired_with == name, (
                    f"{name} pairs with {partner_name}, but {partner_name} "
                    f"pairs with {partner.paired_with!r} (expected {name!r})"
                )


# ---------------------------------------------------------------------------
# Card type correctness
# ---------------------------------------------------------------------------


class TestCardTypes:
    def test_dungeon_is_governance(self) -> None:
        """Dungeon should be Blue/Governance, not Red/Destination."""
        dungeon = get_card_definition("Dungeon")
        assert dungeon.card_type == CardType.BLUE_GOVERNANCE

    def test_fair_grounds_is_unique(self) -> None:
        fg = get_card_definition("Fair Grounds")
        assert fg.unique is True

    def test_inn_is_common(self) -> None:
        inn = get_card_definition("Inn")
        assert inn.unique is False

    def test_post_office_is_common(self) -> None:
        po = get_card_definition("Post Office")
        assert po.unique is False

    def test_husband_is_common(self) -> None:
        h = get_card_definition("Husband")
        assert h.unique is False

    def test_wife_is_common(self) -> None:
        w = get_card_definition("Wife")
        assert w.unique is False

    def test_woodcarver_is_common(self) -> None:
        wc = get_card_definition("Woodcarver")
        assert wc.unique is False

    def test_fool_is_unique(self) -> None:
        f = get_card_definition("Fool")
        assert f.unique is True


# ---------------------------------------------------------------------------
# Card abilities
# ---------------------------------------------------------------------------


class TestCardAbilities:
    def test_farm_production_gives_berry(self) -> None:
        farm = get_card_definition("Farm")
        player = _make_player()
        game = _make_game()
        farm.on_production(game, player)
        assert player.resources.berry == 1

    def test_mine_production_gives_pebble(self) -> None:
        mine = get_card_definition("Mine")
        player = _make_player()
        game = _make_game()
        mine.on_production(game, player)
        assert player.resources.pebble == 1

    def test_twig_barge_production_gives_twigs(self) -> None:
        tb = get_card_definition("Twig Barge")
        player = _make_player()
        game = _make_game()
        tb.on_production(game, player)
        assert player.resources.twig == 2

    def test_resin_refinery_production_gives_resin(self) -> None:
        rr = get_card_definition("Resin Refinery")
        player = _make_player()
        game = _make_game()
        rr.on_production(game, player)
        assert player.resources.resin == 1

    def test_general_store_without_farm(self) -> None:
        gs = get_card_definition("General Store")
        player = _make_player()
        game = _make_game()
        gs.on_production(game, player)
        assert player.resources.berry == 1

    def test_general_store_with_farm(self) -> None:
        gs = get_card_definition("General Store")
        farm = get_card_definition("Farm")
        player = _make_player(city=[farm])
        game = _make_game()
        gs.on_production(game, player)
        assert player.resources.berry == 2

    def test_shepherd_gives_berries(self) -> None:
        shep = get_card_definition("Shepherd")
        player = _make_player()
        game = _make_game()
        shep.on_play(game, player)
        assert player.resources.berry == 3

    def test_barge_toad_with_farms(self) -> None:
        bt = get_card_definition("Barge Toad")
        farm1 = get_card_definition("Farm")
        farm2 = get_card_definition("Farm")
        player = _make_player(city=[farm1, farm2])
        game = _make_game()
        bt.on_production(game, player)
        assert player.resources.twig == 4  # 2 twigs per Farm

    def test_barge_toad_without_farms(self) -> None:
        bt = get_card_definition("Barge Toad")
        player = _make_player()
        game = _make_game()
        bt.on_production(game, player)
        assert player.resources.twig == 0

    def test_shopkeeper_on_critter_play(self) -> None:
        sk = get_card_definition("Shopkeeper")
        player = _make_player()
        game = _make_game()
        critter = get_card_definition("Wanderer")  # a critter
        sk.on_card_played(game, player, critter)
        assert player.resources.berry == 1

    def test_shopkeeper_on_construction_play(self) -> None:
        sk = get_card_definition("Shopkeeper")
        player = _make_player()
        game = _make_game()
        construction = get_card_definition("Farm")  # a construction
        sk.on_card_played(game, player, construction)
        assert player.resources.berry == 0  # no berry for construction

    # --- Prosperity scoring ---

    def test_castle_scores_common_constructions(self) -> None:
        castle = get_card_definition("Castle")
        farm = get_card_definition("Farm")
        mine = get_card_definition("Mine")
        player = _make_player(city=[castle, farm, mine])
        game = _make_game()
        assert castle.on_score(game, player) == 2

    def test_palace_scores_unique_constructions(self) -> None:
        palace = get_card_definition("Palace")
        chapel = get_card_definition("Chapel")
        player = _make_player(city=[palace, chapel])
        game = _make_game()
        # palace + chapel are unique constructions = 2
        assert palace.on_score(game, player) == 2

    def test_school_scores_common_critters(self) -> None:
        school = get_card_definition("School")
        wanderer = get_card_definition("Wanderer")
        teacher = get_card_definition("Teacher")
        player = _make_player(city=[school, wanderer, teacher])
        game = _make_game()
        assert school.on_score(game, player) == 2

    def test_theater_scores_unique_critters(self) -> None:
        theater = get_card_definition("Theater")
        queen = get_card_definition("Queen")
        king = get_card_definition("King")
        player = _make_player(city=[theater, queen, king])
        game = _make_game()
        assert theater.on_score(game, player) == 2

    def test_ever_tree_scores_prosperity_cards(self) -> None:
        et = get_card_definition("Ever Tree")
        castle = get_card_definition("Castle")
        wife = get_card_definition("Wife")
        player = _make_player(city=[et, castle, wife])
        game = _make_game()
        # et + castle + wife = 3 purple prosperity cards
        assert et.on_score(game, player) == 3

    def test_architect_scores_resin_pebble(self) -> None:
        arch = get_card_definition("Architect")
        player = _make_player(resources=ResourceBank(resin=3, pebble=4))
        game = _make_game()
        assert arch.on_score(game, player) == 6  # capped at 6

    def test_architect_scores_capped(self) -> None:
        arch = get_card_definition("Architect")
        player = _make_player(resources=ResourceBank(resin=5, pebble=5))
        game = _make_game()
        assert arch.on_score(game, player) == 6

    def test_wife_scores_with_husband(self) -> None:
        wife = get_card_definition("Wife")
        husband = get_card_definition("Husband")
        player = _make_player(city=[wife, husband])
        game = _make_game()
        assert wife.on_score(game, player) == 3

    def test_wife_scores_without_husband(self) -> None:
        wife = get_card_definition("Wife")
        player = _make_player(city=[wife])
        game = _make_game()
        assert wife.on_score(game, player) == 0

    def test_base_card_on_score_returns_zero(self) -> None:
        """Non-prosperity cards return 0 from on_score."""
        farm = get_card_definition("Farm")
        player = _make_player()
        game = _make_game()
        assert farm.on_score(game, player) == 0
