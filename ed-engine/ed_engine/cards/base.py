from __future__ import annotations

from typing import TYPE_CHECKING

from ed_engine.models.card import Card
from ed_engine.models.enums import CardType

if TYPE_CHECKING:
    from ed_engine.models.game import GameState
    from ed_engine.models.player import Player


class TravelerCard(Card):
    """Tan/Traveler: activates ONCE immediately when played. Never again."""

    card_type: CardType = CardType.TAN_TRAVELER

    # Override on_play in concrete card subclasses.


class ProductionCard(Card):
    """Green/Production: activates on play AND during spring/autumn Prepare for Season."""

    card_type: CardType = CardType.GREEN_PRODUCTION

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """By default, playing a production card fires its production hook."""
        self.on_production(game, player, ctx=ctx)

    # Override on_production in concrete card subclasses.


class DestinationCard(Card):
    """Red/Destination: activates when a worker is placed on it."""

    card_type: CardType = CardType.RED_DESTINATION

    # Override on_worker_placed in concrete card subclasses.


class GovernanceCard(Card):
    """Blue/Governance: triggers when certain card types are played."""

    card_type: CardType = CardType.BLUE_GOVERNANCE

    # Override on_card_played in concrete card subclasses.


class ProsperityCard(Card):
    """Purple/Prosperity: base points + bonus from on_score at end of game."""

    card_type: CardType = CardType.PURPLE_PROSPERITY

    # Override on_score in concrete card subclasses.
