from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ed_engine.models.enums import LocationType
from ed_engine.models.resources import ResourceBank


class Location(BaseModel):
    """A board location where workers can be placed.

    Exclusive locations allow only one worker at a time.
    Shared locations allow unlimited workers.
    """

    id: str
    name: str
    location_type: LocationType
    exclusive: bool = True
    occupants: list[UUID] = Field(default_factory=list)
    rewards: ResourceBank = ResourceBank()
    cards_drawn: int = 0

    def is_occupied(self) -> bool:
        return len(self.occupants) > 0

    def can_place(self, player_id: UUID) -> bool:
        if self.exclusive and self.is_occupied():
            return False
        return True

    def place(self, player_id: UUID) -> Location:
        if not self.can_place(player_id):
            raise ValueError(f"Cannot place worker at {self.name}: location is occupied")
        return self.model_copy(update={"occupants": [*self.occupants, player_id]})

    def remove_player(self, player_id: UUID) -> Location:
        new_occupants = [pid for pid in self.occupants if pid != player_id]
        return self.model_copy(update={"occupants": new_occupants})

    def clear(self) -> Location:
        return self.model_copy(update={"occupants": []})


def create_basic_locations() -> list[Location]:
    """Create the standard board locations available in every game."""
    return [
        # Basic exclusive locations (one worker only)
        Location(
            id="basic_one_twig",
            name="One Twig",
            location_type=LocationType.BASIC,
            exclusive=True,
            rewards=ResourceBank(twig=1),
        ),
        Location(
            id="basic_one_resin",
            name="One Resin",
            location_type=LocationType.BASIC,
            exclusive=True,
            rewards=ResourceBank(resin=1),
        ),
        Location(
            id="basic_one_pebble",
            name="One Pebble",
            location_type=LocationType.BASIC,
            exclusive=True,
            rewards=ResourceBank(pebble=1),
        ),
        Location(
            id="basic_one_berry",
            name="One Berry",
            location_type=LocationType.BASIC,
            exclusive=True,
            rewards=ResourceBank(berry=1),
        ),
        # Shared locations (unlimited workers)
        Location(
            id="basic_two_twigs",
            name="Two Twigs",
            location_type=LocationType.BASIC,
            exclusive=False,
            rewards=ResourceBank(twig=2),
        ),
        Location(
            id="basic_two_resin_one_card",
            name="Two Resin and One Card",
            location_type=LocationType.BASIC,
            exclusive=False,
            rewards=ResourceBank(resin=2),
            cards_drawn=1,
        ),
        Location(
            id="basic_one_pebble_one_card",
            name="One Pebble and One Card",
            location_type=LocationType.BASIC,
            exclusive=False,
            rewards=ResourceBank(pebble=1),
            cards_drawn=1,
        ),
        Location(
            id="basic_one_berry_one_card",
            name="One Berry and One Card",
            location_type=LocationType.BASIC,
            exclusive=False,
            rewards=ResourceBank(berry=1),
            cards_drawn=1,
        ),
    ]


# Forest locations: only a subset are used depending on player count
_ALL_FOREST_LOCATIONS = [
    Location(
        id="forest_two_twig_one_card",
        name="Forest: Two Twig and One Card",
        location_type=LocationType.FOREST,
        exclusive=True,
        rewards=ResourceBank(twig=2),
        cards_drawn=1,
    ),
    Location(
        id="forest_two_resin",
        name="Forest: Two Resin",
        location_type=LocationType.FOREST,
        exclusive=True,
        rewards=ResourceBank(resin=2),
    ),
    Location(
        id="forest_one_twig_one_resin_one_card",
        name="Forest: One Twig, One Resin, and One Card",
        location_type=LocationType.FOREST,
        exclusive=True,
        rewards=ResourceBank(twig=1, resin=1),
        cards_drawn=1,
    ),
    Location(
        id="forest_two_cards_one_point",
        name="Forest: Two Cards and One Point",
        location_type=LocationType.FOREST,
        exclusive=True,
        cards_drawn=2,
    ),
    Location(
        id="forest_three_twig",
        name="Forest: Three Twig",
        location_type=LocationType.FOREST,
        exclusive=True,
        rewards=ResourceBank(twig=3),
    ),
    Location(
        id="forest_two_pebble",
        name="Forest: Two Pebble",
        location_type=LocationType.FOREST,
        exclusive=True,
        rewards=ResourceBank(pebble=2),
    ),
    Location(
        id="forest_one_twig_one_resin_one_pebble",
        name="Forest: One of Each (except Berry)",
        location_type=LocationType.FOREST,
        exclusive=True,
        rewards=ResourceBank(twig=1, resin=1, pebble=1),
    ),
    Location(
        id="forest_three_berry",
        name="Forest: Three Berry",
        location_type=LocationType.FOREST,
        exclusive=True,
        rewards=ResourceBank(berry=3),
    ),
]


def create_forest_locations(player_count: int) -> list[Location]:
    """Select forest locations based on player count.

    Per Everdell rules:
    - 2 players: 3 forest locations
    - 3 players: 4 forest locations
    - 4 players: 4 forest locations (different set than 3p)
    """
    import random

    pool = list(_ALL_FOREST_LOCATIONS)
    random.shuffle(pool)

    if player_count <= 2:
        return pool[:3]
    else:
        return pool[:4]


def create_haven_location() -> Location:
    """Create the Haven location.

    Haven allows a player to discard cards from hand to gain resources
    (one resource of any type per two cards discarded).
    Shared location — any number of workers can be placed here.
    """
    return Location(
        id="haven",
        name="Haven",
        location_type=LocationType.HAVEN,
        exclusive=False,
        rewards=ResourceBank(),  # Dynamic — handled by action logic
    )
