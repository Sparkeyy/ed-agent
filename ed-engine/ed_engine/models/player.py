from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ed_engine.models.card import Card
from ed_engine.models.enums import Season
from ed_engine.models.resources import ResourceBank


class Player(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    resources: ResourceBank = ResourceBank()
    city: list[Card] = Field(default_factory=list)
    hand: list[Card] = Field(default_factory=list)
    workers_total: int = 2
    workers_placed: int = 0
    season: Season = Season.WINTER
    score: int = 0
