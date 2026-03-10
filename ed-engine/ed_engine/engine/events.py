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
    # Verified against physical card scans 2026-03-10
    {
        "id": "se_performer_in_residence",
        "name": "Performer in Residence",
        "description": "Have Inn and Bard in your city. 3 VP.",
        "points": 3,
        "required_cards": ["Inn", "Bard"],
    },
    {
        "id": "se_ancient_scrolls_discovered",
        "name": "Ancient Scrolls Discovered",
        "description": "Have Cemetery and Historian in your city. 3 VP.",
        "points": 3,
        "required_cards": ["Cemetery", "Historian"],
    },
    {
        "id": "se_unexpected_bounty",
        "name": "An Unexpected Bounty",
        "description": "Place up to 3 resources (berry, resin, pebble) here. 3 VP per resource on this Event.",
        "points": 0,  # variable: up to 9 VP
        "required_cards": ["Harvester", "Farm"],
        "scoring": "variable",
    },
    {
        "id": "se_remembering_fallen",
        "name": "Remembering the Fallen",
        "description": "Place up to 2 Critters from your city beneath this Event. 3 VP per Critter.",
        "points": 0,  # variable: up to 6 VP
        "required_cards": ["Cemetery", "Shepherd"],
        "scoring": "variable",
    },
    {
        "id": "se_brilliant_marketing_plan",
        "name": "A Brilliant Marketing Plan",
        "description": "Give opponents up to 3 of any resource. 2 VP per resource donated.",
        "points": 0,  # variable: up to 6 VP
        "required_cards": ["Shopkeeper", "Post Office"],
        "scoring": "variable",
    },
    {
        "id": "se_under_new_management",
        "name": "Under New Management",
        "description": "Place up to 3 resources here. Berry/twig = 1 VP, resin/pebble = 2 VP.",
        "points": 0,  # variable: up to 6 VP
        "required_cards": ["Peddler", "General Store"],
        "scoring": "variable",
    },
    {
        "id": "se_well_run_city",
        "name": "A Well Run City",
        "description": "Bring back one of your deployed workers. 4 VP.",
        "points": 4,
        "required_cards": ["Chip Sweep", "Clock Tower"],
    },
    {
        "id": "se_tax_relief",
        "name": "Tax Relief",
        "description": "Activate Production. 3 VP.",
        "points": 3,
        "required_cards": ["Judge", "Queen"],
    },
    {
        "id": "se_path_of_pilgrims",
        "name": "Path of the Pilgrims",
        "description": "3 VP for each worker in your Monastery.",
        "points": 0,  # variable
        "required_cards": ["Monastery", "Wanderer"],
        "scoring": "variable",
    },
    {
        "id": "se_ministering_to_miscreants",
        "name": "Ministering to Miscreants",
        "description": "3 VP for each prisoner in your Dungeon.",
        "points": 0,  # variable
        "required_cards": ["Monk", "Dungeon"],
        "scoring": "variable",
    },
    {
        "id": "se_evening_of_fireworks",
        "name": "An Evening of Fireworks",
        "description": "Place up to 3 twigs here. 2 VP per twig on this Event.",
        "points": 0,  # variable: up to 6 VP
        "required_cards": ["Lookout", "Miner Mole"],
        "scoring": "variable",
    },
    {
        "id": "se_pristine_chapel_ceiling",
        "name": "Pristine Chapel Ceiling",
        "description": "Draw 1 card and gain 1 VP per VP token on Chapel. 2 VP per VP token on Chapel.",
        "points": 0,  # variable
        "required_cards": ["Woodcarver", "Chapel"],
        "scoring": "variable",
    },
    {
        "id": "se_graduation_of_scholars",
        "name": "Graduation of Scholars",
        "description": "Place up to 3 Critters from hand beneath this Event. 2 VP per Critter.",
        "points": 0,  # variable: up to 6 VP
        "required_cards": ["Teacher", "University"],
        "scoring": "variable",
    },
    {
        "id": "se_croak_wart_cure",
        "name": "Croak Wart Cure",
        "description": "Pay 2 berries and discard 2 cards from your city. 6 VP.",
        "points": 6,
        "required_cards": ["Undertaker", "Barge Toad"],
    },
    {
        "id": "se_capture_acorn_thieves",
        "name": "Capture of the Acorn Thieves",
        "description": "Place up to 2 Critters from city beneath this Event. 3 VP per Critter.",
        "points": 0,  # variable: up to 6 VP
        "required_cards": ["Courthouse", "Ranger"],
        "scoring": "variable",
    },
    {
        "id": "se_flying_doctor_service",
        "name": "Flying Doctor Service",
        "description": "3 VP for each Harvester/Gatherer pair in every City.",
        "points": 0,  # variable
        "required_cards": ["Doctor", "Postal Pigeon"],
        "scoring": "variable",
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
