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
    copies_in_deck: int = 1
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
    copies_in_deck: int = 1
    paired_with: str | None = "Castle"

    def on_score(self, game: GameState, player: Player) -> int:
        """+1 pt per basic Event, +2 pt per special Event."""
        # TODO: implement event scoring (needs event tracking on player)
        return 0


@register
class Wife(ProsperityCard):
    name: str = "Wife"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "Farm"

    def on_score(self, game: GameState, player: Player) -> int:
        """+3 pt if paired with Husband in city."""
        has_husband = any(c.name == "Husband" for c in player.city)
        return 3 if has_husband else 0


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

    def on_production(self, game: GameState, player: Player) -> None:
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

    def on_production(self, game: GameState, player: Player) -> None:
        """Activate any 1 green Production card in city."""
        # TODO: implement choice of which green card to activate
        pass


@register
class Doctor(ProductionCard):
    name: str = "Doctor"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=4)
    base_points: int = 4
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "University"

    def on_production(self, game: GameState, player: Player) -> None:
        """Pay up to 3 berries, gain 1 pt per berry paid."""
        # TODO: implement berry payment choice + point gain
        pass


@register
class Husband(ProductionCard):
    name: str = "Husband"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "Farm"

    def on_production(self, game: GameState, player: Player) -> None:
        """If have Farm and paired with Wife, gain 1 any resource."""
        # TODO: implement conditional resource gain
        pass


@register
class MinerMole(ProductionCard):
    name: str = "Miner Mole"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Mine"

    def on_production(self, game: GameState, player: Player) -> None:
        """Copy 1 green Production card from an opponent's city."""
        # TODO: implement opponent card copy
        pass


@register
class Monk(ProductionCard):
    name: str = "Monk"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=1)
    base_points: int = 0
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "Monastery"

    def on_production(self, game: GameState, player: Player) -> None:
        """Give up to 2 berries to opponent, gain 2 pt per berry given."""
        # TODO: implement berry gift + point gain
        pass


@register
class Peddler(ProductionCard):
    name: str = "Peddler"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "General Store"

    def on_production(self, game: GameState, player: Player) -> None:
        """Trade up to 2 resources for 2 other resources."""
        # TODO: implement resource trade choice
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

    def on_production(self, game: GameState, player: Player) -> None:
        """Draw 2 cards, keep 1, give 1 to opponent."""
        # TODO: implement draw + give
        pass


@register
class Woodcarver(ProductionCard):
    name: str = "Woodcarver"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = None  # TODO: confirm pairing

    def on_production(self, game: GameState, player: Player) -> None:
        """Pay up to 3 twigs, gain 1 pt per twig paid."""
        # TODO: implement twig payment choice + point gain
        pass


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
    copies_in_deck: int = 1
    paired_with: str | None = "Palace"

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player
    ) -> None:
        """Play any card from hand/Meadow worth <=3 pt free."""
        # TODO: implement free card play
        pass


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
    copies_in_deck: int = 1
    paired_with: str | None = "School"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card
    ) -> None:
        """Draw 1 card after playing any card."""
        # TODO: implement draw from deck
        pass


@register
class Innkeeper(GovernanceCard):
    name: str = "Innkeeper"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=1)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "Inn"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card
    ) -> None:
        """Discard Innkeeper to decrease Critter cost by 3 berries."""
        # TODO: implement self-discard discount
        pass


@register
class Judge(GovernanceCard):
    name: str = "Judge"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "Courthouse"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card
    ) -> None:
        """Replace 1 resource in cost with 1 other resource."""
        # TODO: implement resource substitution
        pass


@register
class Shopkeeper(GovernanceCard):
    name: str = "Shopkeeper"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "General Store"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card
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
    copies_in_deck: int = 1
    paired_with: str | None = "Theater"

    def on_play(self, game: GameState, player: Player) -> None:
        """Discard up to 5 cards from hand, gain 1 pt per card."""
        # TODO: implement hand discard choice + point gain
        pass


@register
class Fool(TravelerCard):
    name: str = "Fool"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = -2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Fair Grounds"

    def on_play(self, game: GameState, player: Player) -> None:
        """Played into an opponent's city (not your own)."""
        # TODO: implement opponent city placement
        pass


@register
class PostalPigeon(TravelerCard):
    name: str = "Postal Pigeon"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 0
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Post Office"

    def on_play(self, game: GameState, player: Player) -> None:
        """Reveal 2 from deck, play 1 worth <=3 pt free, discard other."""
        # TODO: implement reveal + free play
        pass


@register
class Ranger(TravelerCard):
    name: str = "Ranger"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "Dungeon"

    def on_play(self, game: GameState, player: Player) -> None:
        """Move 1 deployed worker to a new location. Unlocks 2nd Dungeon cell."""
        # TODO: implement worker movement
        pass


@register
class Shepherd(TravelerCard):
    name: str = "Shepherd"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 3
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "Chapel"

    def on_play(self, game: GameState, player: Player) -> None:
        """Gain 3 berries, +1 pt per VP token on Chapel."""
        player.resources = player.resources.gain(ResourceBank(berry=3))
        # TODO: add VP token scoring from Chapel


@register
class Undertaker(TravelerCard):
    name: str = "Undertaker"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 1
    paired_with: str | None = "Cemetery"

    def on_play(self, game: GameState, player: Player) -> None:
        """Discard 3 Meadow cards, replenish, draw 1 Meadow card to hand. Unlocks 2nd Cemetery plot."""
        # TODO: implement meadow manipulation
        pass


@register
class Wanderer(TravelerCard):
    name: str = "Wanderer"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 0
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = None
    occupies_city_space: bool = False

    def on_play(self, game: GameState, player: Player) -> None:
        """Draw 3 cards. Does not occupy a city space."""
        # TODO: implement draw from deck
        pass
