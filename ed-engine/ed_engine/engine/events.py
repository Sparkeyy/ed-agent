"""Events system for Everdell — Basic and Special Events."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Callable

from pydantic import BaseModel, ConfigDict, Field

from ed_engine.models.enums import CardType

if TYPE_CHECKING:
    from ed_engine.models.player import Player


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class BasicEvent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    name: str
    description: str
    points: int
    condition: Callable[..., bool]  # takes player -> bool
    claimed_by: str | None = None


class SpecialEvent(BaseModel):
    id: str
    name: str
    description: str
    points: int
    required_cards: list[str]  # card names the player must have in city
    claimed_by: str | None = None


# ---------------------------------------------------------------------------
# Condition helpers for Basic Events
# ---------------------------------------------------------------------------


def _count_card_type(player: Player, card_type: CardType) -> int:
    return sum(1 for c in player.city if c.card_type == card_type)


def _has_governance_3(player: Player) -> bool:
    return _count_card_type(player, CardType.BLUE_GOVERNANCE) >= 3


def _has_destination_3(player: Player) -> bool:
    return _count_card_type(player, CardType.RED_DESTINATION) >= 3


def _has_traveler_3(player: Player) -> bool:
    return _count_card_type(player, CardType.TAN_TRAVELER) >= 3


def _has_production_3(player: Player) -> bool:
    return _count_card_type(player, CardType.GREEN_PRODUCTION) >= 3


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------

BASIC_EVENT_DEFS: list[dict] = [
    {
        "id": "basic_governance",
        "name": "Governance Mastery",
        "description": "Have 3 or more Governance (Blue) cards in your city",
        "points": 3,
        "condition": _has_governance_3,
    },
    {
        "id": "basic_destination",
        "name": "Grand Tour",
        "description": "Have 3 or more Destination (Red) cards in your city",
        "points": 3,
        "condition": _has_destination_3,
    },
    {
        "id": "basic_traveler",
        "name": "Well Traveled",
        "description": "Have 3 or more Traveler (Tan) cards in your city",
        "points": 3,
        "condition": _has_traveler_3,
    },
    {
        "id": "basic_production",
        "name": "A Year of Plenty",
        "description": "Have 3 or more Production (Green) cards in your city",
        "points": 3,
        "condition": _has_production_3,
    },
]


SPECIAL_EVENT_DEFS: list[dict] = [
    {
        "id": "se_brilliant_wedding",
        "name": "A Brilliant Wedding",
        "description": "Have Harvester and Gatherer in your city",
        "points": 3,
        "required_cards": ["Harvester", "Gatherer"],
    },
    {
        "id": "se_performer_in_residence",
        "name": "Performer in Residence",
        "description": "Have Bard and Theater in your city",
        "points": 3,
        "required_cards": ["Bard", "Theater"],
    },
    {
        "id": "se_ancient_discovery",
        "name": "An Ancient Discovery",
        "description": "Have Mine and Historian in your city",
        "points": 3,
        "required_cards": ["Mine", "Historian"],
    },
    {
        "id": "se_tax_relief",
        "name": "Tax Relief",
        "description": "Have Queen and Castle in your city",
        "points": 3,
        "required_cards": ["Queen", "Castle"],
    },
    {
        "id": "se_pristine_chapel_ceiling",
        "name": "Pristine Chapel Ceiling",
        "description": "Have Chapel and Woodcarver in your city",
        "points": 3,
        "required_cards": ["Chapel", "Woodcarver"],
    },
    {
        "id": "se_grand_tour",
        "name": "Grand Tour",
        "description": "Have Inn, Post Office, and Lookout in your city",
        "points": 3,
        "required_cards": ["Inn", "Post Office", "Lookout"],
    },
    {
        "id": "se_minister_to_miscreants",
        "name": "Minister to Miscreants",
        "description": "Have Monk, Dungeon, and Cemetery in your city",
        "points": 3,
        "required_cards": ["Monk", "Dungeon", "Cemetery"],
    },
    {
        "id": "se_completion_ever_tree",
        "name": "Completion of the Ever Tree",
        "description": "Have Ever Tree, Gatherer, and Harvester in your city",
        "points": 3,
        "required_cards": ["Ever Tree", "Gatherer", "Harvester"],
    },
    {
        "id": "se_flying_doctor_service",
        "name": "Flying Doctor Service",
        "description": "Have Doctor and Postal Pigeon in your city",
        "points": 3,
        "required_cards": ["Doctor", "Postal Pigeon"],
    },
    {
        "id": "se_jubilant_alliance",
        "name": "A Jubilant Alliance",
        "description": "Have King and Shepherd in your city",
        "points": 3,
        "required_cards": ["King", "Shepherd"],
    },
    {
        "id": "se_scholarly_mission",
        "name": "A Scholarly Mission",
        "description": "Have Teacher and University in your city",
        "points": 3,
        "required_cards": ["Teacher", "University"],
    },
    {
        "id": "se_small_fortune",
        "name": "A Small Fortune",
        "description": "Have Shopkeeper and Mine in your city",
        "points": 3,
        "required_cards": ["Shopkeeper", "Mine"],
    },
    {
        "id": "se_great_feast",
        "name": "The Great Feast",
        "description": "Have General Store, Farm, and Harvester in your city",
        "points": 3,
        "required_cards": ["General Store", "Farm", "Harvester"],
    },
    {
        "id": "se_remembering_fallen",
        "name": "Remembering the Fallen",
        "description": "Have Cemetery and Shepherd in your city",
        "points": 3,
        "required_cards": ["Cemetery", "Shepherd"],
    },
    {
        "id": "se_unexpected_visitor",
        "name": "An Unexpected Visitor",
        "description": "Have Innkeeper and Fair Grounds in your city",
        "points": 3,
        "required_cards": ["Innkeeper", "Fair Grounds"],
    },
    {
        "id": "se_fine_collection",
        "name": "A Fine Collection",
        "description": "Have Judge and Courthouse in your city",
        "points": 3,
        "required_cards": ["Judge", "Courthouse"],
    },
]


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class EventManager:
    """Manages basic and special events for a game."""

    def __init__(self, seed: int | None = None) -> None:
        """Setup: 4 basic events (always) + 4 random from 16 special events."""
        self.basic_events: list[BasicEvent] = [
            BasicEvent(**d) for d in BASIC_EVENT_DEFS
        ]

        rng = random.Random(seed)
        chosen = rng.sample(SPECIAL_EVENT_DEFS, 4)
        self.special_events: list[SpecialEvent] = [
            SpecialEvent(**d) for d in chosen
        ]

    def _all_events(self) -> list[BasicEvent | SpecialEvent]:
        return self.basic_events + self.special_events  # type: ignore[operator]

    def get_available_events(self, player: Player) -> list[BasicEvent | SpecialEvent]:
        """Events this player can claim (meets conditions, not yet claimed)."""
        available: list[BasicEvent | SpecialEvent] = []
        player_card_names = {c.name for c in player.city}

        for ev in self.basic_events:
            if ev.claimed_by is None and ev.condition(player):
                available.append(ev)

        for ev in self.special_events:
            if ev.claimed_by is None:
                if all(name in player_card_names for name in ev.required_cards):
                    available.append(ev)

        return available

    def claim_event(self, event_id: str, player_id: str) -> bool:
        """Claim an event. Returns True if successful (unclaimed and found)."""
        for ev in self._all_events():
            if ev.id == event_id:
                if ev.claimed_by is not None:
                    return False
                ev.claimed_by = player_id
                return True
        return False

    def get_claimed_events(self, player_id: str) -> list[BasicEvent | SpecialEvent]:
        """All events claimed by this player."""
        return [ev for ev in self._all_events() if ev.claimed_by == player_id]

    def to_game_state_dicts(self) -> tuple[dict, dict]:
        """Export events as dicts suitable for GameState.basic_events / special_events."""
        basic_dict = {}
        for ev in self.basic_events:
            basic_dict[ev.id] = {
                "name": ev.name,
                "description": ev.description,
                "points": ev.points,
                "claimed_by": ev.claimed_by,
            }
        special_dict = {}
        for ev in self.special_events:
            special_dict[ev.id] = {
                "name": ev.name,
                "description": ev.description,
                "points": ev.points,
                "required_cards": ev.required_cards,
                "claimed_by": ev.claimed_by,
            }
        return basic_dict, special_dict
