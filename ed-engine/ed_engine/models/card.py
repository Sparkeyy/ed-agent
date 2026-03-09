from __future__ import annotations

from abc import abstractmethod
from typing import Any, Optional

from pydantic import BaseModel

from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.resources import ResourceBank


class Card(BaseModel):
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
    def on_play(self, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_trigger(self, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_score(self, **kwargs: Any) -> int:
        raise NotImplementedError
