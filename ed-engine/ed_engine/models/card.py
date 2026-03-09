from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, ConfigDict

from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.resources import ResourceBank

if TYPE_CHECKING:
    from ed_engine.models.game import GameState
    from ed_engine.models.player import Player


class Card(BaseModel):
    """Base card model for Everdell.

    Concrete base with no-op default methods. Subclass per card type
    and override the relevant hooks.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    card_type: CardType
    category: CardCategory
    cost: ResourceBank = ResourceBank()
    base_points: int = 0
    paired_with: Optional[str] = None
    unique: bool = False
    copies_in_deck: int = 1
    occupies_city_space: bool = True
    is_open_destination: bool = False

    # --- lifecycle hooks (override in subclasses) ---

    def on_play(self, game: GameState, player: Player) -> None:
        """Called when this card is played into a city."""

    def on_production(self, game: GameState, player: Player) -> None:
        """Called during green production triggers (spring/autumn Prepare for Season)."""

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player
    ) -> None:
        """Called when a worker is placed on this red destination card."""

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card
    ) -> None:
        """Called for blue governance triggers when *any* card is played."""

    def on_score(self, game: GameState, player: Player) -> int:
        """Return bonus points beyond base_points (purple prosperity cards)."""
        return 0
