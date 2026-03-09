from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ed_engine.models.card import Card
from ed_engine.models.player import Player
from ed_engine.models.resources import SupplyPool


class GameState(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    players: list[Player] = Field(default_factory=list)
    supply: SupplyPool = Field(default_factory=SupplyPool)
    deck: list[Card] = Field(default_factory=list)
    meadow: list[Card] = Field(default_factory=list, max_length=8)
    discard: list[Card] = Field(default_factory=list)
    current_player_idx: int = 0
    turn_number: int = 1
    basic_events: dict[str, Any] = Field(default_factory=dict)
    special_events: dict[str, Any] = Field(default_factory=dict)
    forest_locations: list[Any] = Field(default_factory=list)
    game_over: bool = False
