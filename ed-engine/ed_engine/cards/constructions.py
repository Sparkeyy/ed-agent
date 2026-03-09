"""All Everdell construction card definitions."""

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
# Purple / Prosperity constructions
# ---------------------------------------------------------------------------


@register
class Castle(ProsperityCard):
    name: str = "Castle"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=2, resin=3, pebble=3)
    base_points: int = 4
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "King"

    def on_score(self, game: GameState, player: Player) -> int:
        """+ 1 pt per Common Construction in city."""
        return sum(
            1
            for c in player.city
            if c.category == CardCategory.CONSTRUCTION and not c.unique
        )


@register
class EverTree(ProsperityCard):
    name: str = "Ever Tree"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=3, resin=3, pebble=3)
    base_points: int = 5
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = None  # grants free Critter; no single pair

    def on_score(self, game: GameState, player: Player) -> int:
        """+ 1 pt per Purple/Prosperity card in city."""
        return sum(
            1
            for c in player.city
            if c.card_type == CardType.PURPLE_PROSPERITY
        )


@register
class Palace(ProsperityCard):
    name: str = "Palace"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=2, resin=3, pebble=3)
    base_points: int = 4
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Queen"

    def on_score(self, game: GameState, player: Player) -> int:
        """+ 1 pt per Unique Construction in city."""
        return sum(
            1
            for c in player.city
            if c.category == CardCategory.CONSTRUCTION and c.unique
        )


@register
class School(ProsperityCard):
    name: str = "School"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=2, resin=2)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Teacher"

    def on_score(self, game: GameState, player: Player) -> int:
        """+ 1 pt per Common Critter in city."""
        return sum(
            1
            for c in player.city
            if c.category == CardCategory.CRITTER and not c.unique
        )


@register
class Theater(ProsperityCard):
    name: str = "Theater"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=3, resin=1, pebble=1)
    base_points: int = 3
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Bard"

    def on_score(self, game: GameState, player: Player) -> int:
        """+ 1 pt per Unique Critter in city."""
        return sum(
            1
            for c in player.city
            if c.category == CardCategory.CRITTER and c.unique
        )


# ---------------------------------------------------------------------------
# Green / Production constructions
# ---------------------------------------------------------------------------


@register
class FairGrounds(ProductionCard):
    name: str = "Fair Grounds"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=1, resin=2, pebble=1)
    base_points: int = 3
    unique: bool = True
    copies_in_deck: int = 3
    paired_with: str | None = "Fool"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Draw 2 cards."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if deck_mgr:
            drawn = deck_mgr.draw(2)
            player.hand.extend(drawn)


@register
class Farm(ProductionCard):
    name: str = "Farm"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=2, resin=1)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 8
    paired_with: str | None = "Harvester"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Gain 1 berry."""
        player.resources = player.resources.gain(ResourceBank(berry=1))


@register
class GeneralStore(ProductionCard):
    name: str = "General Store"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(resin=1, pebble=1)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Shopkeeper"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Gain 1 berry, or 2 if player has a Farm."""
        has_farm = any(c.name == "Farm" for c in player.city)
        amount = 2 if has_farm else 1
        player.resources = player.resources.gain(ResourceBank(berry=amount))


@register
class Mine(ProductionCard):
    name: str = "Mine"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=1, resin=1, pebble=1)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Miner Mole"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Gain 1 pebble."""
        player.resources = player.resources.gain(ResourceBank(pebble=1))


@register
class ResinRefinery(ProductionCard):
    name: str = "Resin Refinery"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(resin=1, pebble=1)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Chip Sweep"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Gain 1 resin."""
        player.resources = player.resources.gain(ResourceBank(resin=1))


@register
class Storehouse(ProductionCard):
    name: str = "Storehouse"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=1, resin=1, pebble=1)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Woodcarver"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Place 3 twigs OR 2 resin OR 1 pebble OR 2 berries on card (auto-pick 3 twigs)."""
        player.resources = player.resources.gain(ResourceBank(twig=3))


@register
class TwigBarge(ProductionCard):
    name: str = "Twig Barge"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=1, pebble=1)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Barge Toad"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Gain 2 twigs."""
        player.resources = player.resources.gain(ResourceBank(twig=2))


# ---------------------------------------------------------------------------
# Red / Destination constructions
# ---------------------------------------------------------------------------


@register
class Cemetery(DestinationCard):
    name: str = "Cemetery"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(pebble=2)
    base_points: int = 0
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Undertaker"

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player, *, ctx: dict | None = None
    ) -> None:
        """Reveal 4 from deck/discard, play 1 free."""
        # TODO: implement reveal + play logic
        pass


@register
class Chapel(DestinationCard):
    name: str = "Chapel"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=2, resin=1, pebble=1)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Shepherd"

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player, *, ctx: dict | None = None
    ) -> None:
        """Place 1 VP token on Chapel, draw 2 cards per VP token on it."""
        # TODO: implement VP token tracking + draw
        pass


@register
class Inn(DestinationCard):
    name: str = "Inn"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=2, resin=1)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Innkeeper"
    is_open_destination: bool = True

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player, *, ctx: dict | None = None
    ) -> None:
        """Play Critter/Construction from Meadow for 3 less any resource."""
        # TODO: implement meadow discount play
        pass


@register
class Lookout(DestinationCard):
    name: str = "Lookout"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=1, resin=1, pebble=1)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Wanderer"

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player, *, ctx: dict | None = None
    ) -> None:
        """Copy any basic or Forest location."""
        # TODO: implement location copy
        pass


@register
class Monastery(DestinationCard):
    name: str = "Monastery"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=1, resin=1, pebble=1)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Monk"

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player, *, ctx: dict | None = None
    ) -> None:
        """Give 2 resources to opponent, gain 4 points. Permanent worker."""
        # TODO: implement resource gift + points + permanent worker
        pass


@register
class PostOffice(DestinationCard):
    name: str = "Post Office"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=1, resin=2)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Postal Pigeon"
    is_open_destination: bool = True

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player, *, ctx: dict | None = None
    ) -> None:
        """Give opponent 2 cards, discard any, draw to hand limit."""
        # TODO: implement card exchange
        pass


@register
class University(DestinationCard):
    name: str = "University"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(resin=1, pebble=2)
    base_points: int = 3
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Doctor"

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player, *, ctx: dict | None = None
    ) -> None:
        """Discard 1 card from city, get cost back, +1 any resource +1 point. Permanent worker."""
        # TODO: implement city card discard + refund + bonus
        pass


# ---------------------------------------------------------------------------
# Blue / Governance constructions
# ---------------------------------------------------------------------------


@register
class ClockTower(GovernanceCard):
    name: str = "Clock Tower"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=3, pebble=1)
    base_points: int = 0
    unique: bool = True
    copies_in_deck: int = 3
    paired_with: str | None = "Historian"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """3 VP tokens; before Prepare for Season remove 1 and activate a location."""
        # TODO: implement token / season mechanic
        pass


@register
class Courthouse(GovernanceCard):
    name: str = "Courthouse"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(twig=1, resin=1, pebble=2)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Judge"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Gain 1 twig/resin/pebble when playing a Construction (auto-pick twig)."""
        if played_card.category == CardCategory.CONSTRUCTION:
            player.resources = player.resources.gain(ResourceBank(twig=1))


@register
class Crane(GovernanceCard):
    name: str = "Crane"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(pebble=1)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 3
    paired_with: str | None = "Architect"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Discard Crane to decrease Construction cost by 3 any resource."""
        # TODO: implement self-discard discount
        pass


@register
class Dungeon(GovernanceCard):
    name: str = "Dungeon"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank(resin=1, pebble=2)
    base_points: int = 0
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Ranger"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Place city Critter beneath to decrease played card cost by 3."""
        # TODO: implement prisoner mechanic
        pass


# ---------------------------------------------------------------------------
# Tan / Traveler constructions
# ---------------------------------------------------------------------------


@register
class Ruins(TravelerCard):
    name: str = "Ruins"
    category: CardCategory = CardCategory.CONSTRUCTION
    cost: ResourceBank = ResourceBank()
    base_points: int = 0
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Peddler"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Discard a Construction from city, gain its cost back, draw 2 cards."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        # Find cheapest construction to discard (auto-pick)
        constructions = [c for c in player.city if c.category == CardCategory.CONSTRUCTION and c is not self]
        if constructions:
            target = min(constructions, key=lambda c: c.base_points)
            player.city.remove(target)
            player.resources = player.resources.gain(target.cost)
            if deck_mgr:
                deck_mgr.discard([target])
        if deck_mgr:
            drawn = deck_mgr.draw(2)
            player.hand.extend(drawn)
