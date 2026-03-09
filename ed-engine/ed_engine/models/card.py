from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel

from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.resources import ResourceBank

if TYPE_CHECKING:
    from ed_engine.models.player import Player


class Card(BaseModel):
    """Base class for all Everdell cards.

    Subclass one of the five type-specific bases instead of this directly.
    """

    id: str
    name: str
    card_type: CardType
    category: CardCategory
    cost: ResourceBank = ResourceBank()
    base_points: int = 0
    paired_with: Optional[str] = None
    unique: bool = False
    copies: int = 1

    @abstractmethod
    def on_play(self, player: Player, **kwargs: Any) -> None:
        """Called when the card is played into a player's city."""
        raise NotImplementedError

    @abstractmethod
    def on_trigger(self, player: Player, **kwargs: Any) -> None:
        """Called when the card is triggered (e.g. during production)."""
        raise NotImplementedError

    @abstractmethod
    def on_score(self, player: Player, **kwargs: Any) -> int:
        """Return the total VP this card contributes at end-of-game."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Type-specific base classes
# ---------------------------------------------------------------------------


class TanTravelerCard(Card):
    """Tan / Traveler — one-time effect when played, then inert.

    Subclasses MUST override ``on_play`` to define the one-time effect.
    ``on_trigger`` is a no-op; ``on_score`` returns ``base_points``.
    """

    card_type: CardType = CardType.TAN_TRAVELER

    @abstractmethod
    def on_play(self, player: Player, **kwargs: Any) -> None:  # type: ignore[override]
        raise NotImplementedError

    def on_trigger(self, player: Player, **kwargs: Any) -> None:
        pass  # Travelers have no recurring trigger

    def on_score(self, player: Player, **kwargs: Any) -> int:
        return self.base_points


class GreenProductionCard(Card):
    """Green / Production — triggers each Prepare for Season (spring & autumn).

    Subclasses MUST override ``on_trigger`` to define the production effect.
    ``on_play`` is a no-op; ``on_score`` returns ``base_points``.
    """

    card_type: CardType = CardType.GREEN_PRODUCTION

    def on_play(self, player: Player, **kwargs: Any) -> None:
        pass  # Production cards have no immediate play effect

    @abstractmethod
    def on_trigger(self, player: Player, **kwargs: Any) -> None:  # type: ignore[override]
        raise NotImplementedError

    def on_score(self, player: Player, **kwargs: Any) -> int:
        return self.base_points


class RedDestinationCard(Card):
    """Red / Destination — acts as a worker-placement location in the player's city.

    Only the owning player (or sharing rules) can place a worker here.
    ``on_trigger`` fires when a worker is placed on the card.
    ``on_play`` is a no-op; ``on_score`` returns ``base_points``.
    """

    card_type: CardType = CardType.RED_DESTINATION
    occupied_by: Optional[str] = None  # player id that placed a worker here

    def on_play(self, player: Player, **kwargs: Any) -> None:
        pass  # Destination cards have no immediate play effect

    @abstractmethod
    def on_trigger(self, player: Player, **kwargs: Any) -> None:  # type: ignore[override]
        """Effect when a worker is placed on this destination."""
        raise NotImplementedError

    def on_score(self, player: Player, **kwargs: Any) -> int:
        return self.base_points

    def place_worker(self, player_id: str) -> None:
        if self.occupied_by is not None:
            raise ValueError(f"{self.name} is already occupied")
        self.occupied_by = player_id

    def recall_worker(self) -> None:
        self.occupied_by = None


class BlueGovernanceCard(Card):
    """Blue / Governance — grants an ongoing rule or end-of-game scoring bonus.

    Subclasses SHOULD override ``on_score`` when the card has conditional VP.
    ``on_play`` and ``on_trigger`` are no-ops by default.
    """

    card_type: CardType = CardType.BLUE_GOVERNANCE

    def on_play(self, player: Player, **kwargs: Any) -> None:
        pass

    def on_trigger(self, player: Player, **kwargs: Any) -> None:
        pass  # Governance cards don't trigger during production

    @abstractmethod
    def on_score(self, player: Player, **kwargs: Any) -> int:  # type: ignore[override]
        raise NotImplementedError


class PurpleProsperityCard(Card):
    """Purple / Prosperity — worth variable bonus VP at end of game.

    Subclasses MUST override ``on_score`` to compute the conditional bonus.
    ``on_play`` and ``on_trigger`` are no-ops.
    """

    card_type: CardType = CardType.PURPLE_PROSPERITY

    def on_play(self, player: Player, **kwargs: Any) -> None:
        pass

    def on_trigger(self, player: Player, **kwargs: Any) -> None:
        pass  # Prosperity cards don't trigger during production

    @abstractmethod
    def on_score(self, player: Player, **kwargs: Any) -> int:  # type: ignore[override]
        raise NotImplementedError
