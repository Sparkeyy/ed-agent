"""All Everdell critter card definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ed_engine.cards import register
from ed_engine.cards.base import (
    DestinationCard,
    GovernanceCard,
    ProductionCard,
    ProsperityCard,
    TravelerCard,
)
from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.resources import ResourceBank

if TYPE_CHECKING:
    from ed_engine.models.card import Card
    from ed_engine.models.game import GameState
    from ed_engine.models.player import Player


# ---------------------------------------------------------------------------
# Purple / Prosperity critters
# ---------------------------------------------------------------------------


@register
class Architect(ProsperityCard):
    name: str = "Architect"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=4)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Crane"

    def on_score(self, game: GameState, player: Player) -> int:
        """+1 pt per leftover resin and pebble, up to 6."""
        return min(player.resources.resin + player.resources.pebble, 6)


@register
class King(ProsperityCard):
    name: str = "King"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=6)
    base_points: int = 4
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Castle"

    def on_score(self, game: GameState, player: Player) -> int:
        """+1 pt per basic Event, +2 pt per special Event."""
        player_id = str(player.id)
        basic_count = sum(
            1 for edata in game.basic_events.values()
            if (isinstance(edata, dict) and edata.get("claimed_by") == player_id)
            or (hasattr(edata, "claimed_by") and getattr(edata, "claimed_by", None) == player_id)
        )
        special_count = sum(
            1 for edata in game.special_events.values()
            if (isinstance(edata, dict) and edata.get("claimed_by") == player_id)
            or (hasattr(edata, "claimed_by") and getattr(edata, "claimed_by", None) == player_id)
        )
        return basic_count + 2 * special_count


@register
class Gatherer(ProsperityCard):
    name: str = "Gatherer"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 4
    paired_with: str | None = "Farm"

    def on_score(self, game: GameState, player: Player) -> int:
        """+3 pt if paired with Harvester in city."""
        has_harvester = any(c.name == "Harvester" for c in player.city)
        return 3 if has_harvester else 0


# ---------------------------------------------------------------------------
# Green / Production critters
# ---------------------------------------------------------------------------


@register
class BargeToad(ProductionCard):
    name: str = "Barge Toad"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Twig Barge"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Gain 2 twigs per Farm in city."""
        farm_count = sum(1 for c in player.city if c.name == "Farm")
        if farm_count > 0:
            player.resources = player.resources.gain(
                ResourceBank(twig=2 * farm_count)
            )


@register
class ChipSweep(ProductionCard):
    name: str = "Chip Sweep"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Resin Refinery"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Activate any 1 green Production card in city (auto-pick first, skip ChipSweeps to prevent recursion)."""
        for card in player.city:
            if card.card_type == CardType.GREEN_PRODUCTION and card is not self and card.name != "Chip Sweep":
                card.on_production(game, player, ctx=ctx)
                break


@register
class Doctor(ProductionCard):
    name: str = "Doctor"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=4)
    base_points: int = 4
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "University"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Pay up to 3 berries, gain 1 pt per berry paid."""
        pay = min(3, player.resources.berry)
        if pay > 0:
            player.resources = player.resources.spend(ResourceBank(berry=pay))
            player.point_tokens += pay


@register
class Harvester(ProductionCard):
    name: str = "Harvester"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 4
    paired_with: str | None = "Farm"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """If have Farm in city, gain 1 berry (auto-pick as 'any resource')."""
        has_farm = any(c.name == "Farm" for c in player.city)
        if has_farm:
            player.resources = player.resources.gain(ResourceBank(berry=1))


@register
class MinerMole(ProductionCard):
    name: str = "Miner Mole"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Mine"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Copy 1 green Production card from an opponent's city (auto-pick first, skip recursive cards)."""
        skip = {"Chip Sweep", "Miner Mole"}
        for other in game.players:
            if str(other.id) == str(player.id):
                continue
            for card in other.city:
                if card.card_type == CardType.GREEN_PRODUCTION and card.name not in skip:
                    card.on_production(game, player, ctx=ctx)
                    return


@register
class Monk(ProductionCard):
    name: str = "Monk"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=1)
    base_points: int = 0
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Monastery"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Give up to 2 berries to first opponent, gain 2 VP per berry given."""
        give = min(2, player.resources.berry)
        if give > 0:
            player.resources = player.resources.spend(ResourceBank(berry=give))
            # Give to first opponent
            for other in game.players:
                if str(other.id) != str(player.id):
                    other.resources = other.resources.gain(ResourceBank(berry=give))
                    break
            player.point_tokens += 2 * give


@register
class Peddler(ProductionCard):
    name: str = "Peddler"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Ruins"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Trade up to 2 resources for 2 other resources. (Skipped — complex trade logic.)"""
        pass


@register
class Teacher(ProductionCard):
    name: str = "Teacher"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "School"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Draw 2 cards, keep highest VP, give lowest to first opponent."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if not deck_mgr:
            return
        drawn = deck_mgr.draw(2)
        if not drawn:
            return
        drawn.sort(key=lambda c: c.base_points, reverse=True)
        player.hand.append(drawn[0])
        if len(drawn) > 1:
            for other in game.players:
                if str(other.id) != str(player.id):
                    other.hand.append(drawn[1])
                    break
            else:
                deck_mgr.discard([drawn[1]])


@register
class Woodcarver(ProductionCard):
    name: str = "Woodcarver"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Storehouse"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Pay up to 3 twigs, gain 1 pt per twig paid."""
        pay = min(3, player.resources.twig)
        if pay > 0:
            player.resources = player.resources.spend(ResourceBank(twig=pay))
            player.point_tokens += pay


# ---------------------------------------------------------------------------
# Red / Destination critters
# ---------------------------------------------------------------------------


@register
class Queen(DestinationCard):
    name: str = "Queen"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=5)
    base_points: int = 4
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Palace"

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player, *, ctx: dict | None = None
    ) -> None:
        """Play any card from hand/Meadow worth <=3 pt free (auto-pick first eligible)."""
        from ed_engine.engine.actions import MAX_CITY_SIZE
        city_size = sum(1 for c in player.city if c.occupies_city_space)
        city_names = {c.name for c in player.city}

        def _eligible(card):
            if card.base_points > 3:
                return False
            if card.unique and card.name in city_names:
                return False
            if card.occupies_city_space and city_size >= MAX_CITY_SIZE:
                return False
            return True

        # Try hand first
        for i, card in enumerate(player.hand):
            if _eligible(card):
                played = player.hand.pop(i)
                player.city.append(played)
                played.on_play(game, player, ctx=ctx)
                return
        # Try meadow
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if deck_mgr:
            for i, card in enumerate(deck_mgr.meadow):
                if _eligible(card):
                    played = deck_mgr.draw_from_meadow(i)
                    player.city.append(played)
                    played.on_play(game, player, ctx=ctx)
                    return


# ---------------------------------------------------------------------------
# Blue / Governance critters
# ---------------------------------------------------------------------------


@register
class Historian(GovernanceCard):
    name: str = "Historian"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 3
    paired_with: str | None = "Clock Tower"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Draw 1 card after playing any card."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if deck_mgr:
            drawn = deck_mgr.draw(1)
            player.hand.extend(drawn)


@register
class Innkeeper(GovernanceCard):
    name: str = "Innkeeper"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=1)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 3
    paired_with: str | None = "Inn"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Discard Innkeeper to decrease Critter cost by 3 berries. (Deferred — requires pre-play hook.)"""
        pass


@register
class Judge(GovernanceCard):
    name: str = "Judge"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Courthouse"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Replace 1 resource in cost with 1 other resource. (Deferred — requires cost modification hook.)"""
        pass


@register
class Shopkeeper(GovernanceCard):
    name: str = "Shopkeeper"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 3
    paired_with: str | None = "General Store"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Gain 1 berry after playing a Critter."""
        if played_card.category == CardCategory.CRITTER:
            player.resources = player.resources.gain(ResourceBank(berry=1))


# ---------------------------------------------------------------------------
# Tan / Traveler critters
# ---------------------------------------------------------------------------


@register
class Bard(TravelerCard):
    name: str = "Bard"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 0
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Theater"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Discard up to 5 cards from hand (lowest VP), gain 1 VP per card."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        hand = sorted(player.hand, key=lambda c: c.base_points)
        to_discard = hand[:min(5, len(hand))]
        for card in to_discard:
            player.hand.remove(card)
        player.point_tokens += len(to_discard)
        if deck_mgr and to_discard:
            deck_mgr.discard(to_discard)


@register
class Fool(TravelerCard):
    name: str = "Fool"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = -2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Fair Grounds"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Played into an opponent's city (not your own). Move from player's city to first opponent."""
        # Card was already added to player.city by _play_card — move it
        for other in game.players:
            if str(other.id) != str(player.id):
                # Remove from player's city, add to opponent's
                if self in player.city:
                    player.city.remove(self)
                other.city.append(self)
                return


@register
class PostalPigeon(TravelerCard):
    name: str = "Postal Pigeon"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 0
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Post Office"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Reveal 2 from deck, play 1 worth <=3 pt free, discard other."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if not deck_mgr:
            return
        drawn = deck_mgr.draw(2)
        if not drawn:
            return
        city_names = {c.name for c in player.city}
        # Find first eligible card (base_points <= 3, respects uniqueness)
        played = None
        for card in drawn:
            if card.base_points <= 3:
                if card.unique and card.name in city_names:
                    continue
                played = card
                break
        if played:
            drawn.remove(played)
            player.city.append(played)
            played.on_play(game, player, ctx=ctx)
        # Discard the rest
        if drawn:
            deck_mgr.discard(drawn)


@register
class Ranger(TravelerCard):
    name: str = "Ranger"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Dungeon"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Move 1 deployed worker to a new location. (Deferred — complex worker movement.)"""
        pass


@register
class Shepherd(TravelerCard):
    name: str = "Shepherd"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Chapel"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Gain 3 berries, +1 pt per VP token on Chapel."""
        player.resources = player.resources.gain(ResourceBank(berry=3))


@register
class Undertaker(TravelerCard):
    name: str = "Undertaker"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Cemetery"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Discard 3 Meadow cards, replenish, draw 1 Meadow card to hand."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if not deck_mgr:
            return
        # Discard up to 3 from meadow
        discarded = 0
        for _ in range(3):
            if deck_mgr.meadow:
                card = deck_mgr.draw_from_meadow(0)
                deck_mgr.discard([card])
                discarded += 1
        # Draw 1 meadow card to hand
        if deck_mgr.meadow:
            card = deck_mgr.draw_from_meadow(0)
            player.hand.append(card)


@register
class Wanderer(TravelerCard):
    name: str = "Wanderer"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Lookout"
    occupies_city_space: bool = False

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Draw 3 cards. Does not occupy a city space."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if deck_mgr:
            drawn = deck_mgr.draw(3)
            player.hand.extend(drawn)
