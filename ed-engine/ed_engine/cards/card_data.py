"""Card definitions for all 128 Everdell base game cards.

Each entry defines a card type with its game data. The deck is built by
creating `copies` instances of each card type.

Card type mapping:
  TAN_TRAVELER     - activates once when played
  GREEN_PRODUCTION - activates on play and during Prepare for Season
  RED_DESTINATION  - activates when a worker is placed on it
  BLUE_GOVERNANCE  - ongoing bonuses for playing card types
  PURPLE_PROSPERITY - base points + end-game bonus
"""

from __future__ import annotations

from typing import Any, TypedDict


class CardDef(TypedDict):
    name: str
    card_type: str  # CardType value
    category: str  # CardCategory value
    cost_twig: int
    cost_resin: int
    cost_pebble: int
    cost_berry: int
    base_points: int
    unique: bool
    copies: int
    paired_with: str | None


# fmt: off
CRITTER_DEFS: list[CardDef] = [
    # --- TAN TRAVELERS (activate once when played) ---
    {"name": "Bard",          "card_type": "tan_traveler",       "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 3, "base_points": 0, "unique": False, "copies": 3, "paired_with": "Theater"},
    {"name": "Fool",          "card_type": "tan_traveler",       "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 3, "base_points": -2, "unique": False, "copies": 3, "paired_with": "Fair Grounds"},
    {"name": "Postal Pigeon", "card_type": "tan_traveler",       "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 2, "base_points": 0, "unique": False, "copies": 3, "paired_with": "Post Office"},
    {"name": "Ranger",        "card_type": "tan_traveler",       "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 2, "base_points": 2, "unique": True,  "copies": 2, "paired_with": "Dungeon"},
    {"name": "Shepherd",      "card_type": "tan_traveler",       "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 3, "base_points": 3, "unique": True,  "copies": 2, "paired_with": "Chapel"},
    {"name": "Undertaker",    "card_type": "tan_traveler",       "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 2, "base_points": 1, "unique": True,  "copies": 2, "paired_with": "Cemetery"},
    {"name": "Wanderer",      "card_type": "tan_traveler",       "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 2, "base_points": 1, "unique": False, "copies": 4, "paired_with": None},

    # --- GREEN PRODUCTION (activate on play + during Prepare for Season) ---
    {"name": "Barge Toad",    "card_type": "green_production",   "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 2, "base_points": 1, "unique": False, "copies": 3, "paired_with": "Twig Barge"},
    {"name": "Chip Sweep",    "card_type": "green_production",   "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 3, "base_points": 2, "unique": False, "copies": 3, "paired_with": "Resin Refinery"},
    {"name": "Doctor",        "card_type": "green_production",   "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 4, "base_points": 4, "unique": True,  "copies": 2, "paired_with": "University"},
    {"name": "Husband",       "card_type": "green_production",   "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 3, "base_points": 2, "unique": False, "copies": 4, "paired_with": "Farm"},
    {"name": "Miner Mole",    "card_type": "green_production",   "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 3, "base_points": 1, "unique": False, "copies": 3, "paired_with": "Mine"},
    {"name": "Monk",          "card_type": "green_production",   "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 1, "base_points": 0, "unique": True,  "copies": 2, "paired_with": "Monastery"},
    {"name": "Peddler",       "card_type": "green_production",   "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 2, "base_points": 1, "unique": False, "copies": 3, "paired_with": "Ruins"},
    {"name": "Teacher",       "card_type": "green_production",   "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 2, "base_points": 2, "unique": True,  "copies": 2, "paired_with": "School"},
    {"name": "Woodcarver",    "card_type": "green_production",   "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 3, "base_points": 2, "unique": True,  "copies": 2, "paired_with": "Storehouse"},

    # --- BLUE GOVERNANCE (ongoing bonuses) ---
    {"name": "Historian",     "card_type": "blue_governance",    "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 2, "base_points": 1, "unique": False, "copies": 3, "paired_with": "Clock Tower"},
    {"name": "Innkeeper",     "card_type": "blue_governance",    "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 1, "base_points": 1, "unique": True,  "copies": 2, "paired_with": "Inn"},
    {"name": "Judge",         "card_type": "blue_governance",    "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 3, "base_points": 2, "unique": True,  "copies": 2, "paired_with": "Courthouse"},
    {"name": "Shopkeeper",    "card_type": "blue_governance",    "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 2, "base_points": 1, "unique": True,  "copies": 2, "paired_with": "General Store"},

    # --- PURPLE PROSPERITY (end-game bonus scoring) ---
    {"name": "Architect",     "card_type": "purple_prosperity",  "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 4, "base_points": 2, "unique": True,  "copies": 2, "paired_with": "Crane"},
    {"name": "King",          "card_type": "purple_prosperity",  "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 6, "base_points": 4, "unique": True,  "copies": 2, "paired_with": "Castle"},
    {"name": "Wife",          "card_type": "purple_prosperity",  "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 3, "base_points": 2, "unique": False, "copies": 5, "paired_with": "Ever Tree"},

    # --- RED DESTINATION (activate when worker placed) ---
    {"name": "Queen",         "card_type": "red_destination",    "category": "critter", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 5, "base_points": 4, "unique": True,  "copies": 2, "paired_with": "Palace"},
]

CONSTRUCTION_DEFS: list[CardDef] = [
    # --- TAN TRAVELERS ---
    {"name": "Ruins",           "card_type": "tan_traveler",       "category": "construction", "cost_twig": 0, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 0, "base_points": 0, "unique": False, "copies": 3, "paired_with": None},

    # --- GREEN PRODUCTION ---
    {"name": "Clock Tower",     "card_type": "green_production",   "category": "construction", "cost_twig": 3, "cost_resin": 0, "cost_pebble": 1, "cost_berry": 0, "base_points": 0, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Fair Grounds",    "card_type": "green_production",   "category": "construction", "cost_twig": 1, "cost_resin": 1, "cost_pebble": 1, "cost_berry": 0, "base_points": 1, "unique": False, "copies": 3, "paired_with": None},
    {"name": "Farm",            "card_type": "green_production",   "category": "construction", "cost_twig": 2, "cost_resin": 1, "cost_pebble": 0, "cost_berry": 0, "base_points": 1, "unique": False, "copies": 8, "paired_with": None},
    {"name": "General Store",   "card_type": "green_production",   "category": "construction", "cost_twig": 1, "cost_resin": 1, "cost_pebble": 0, "cost_berry": 0, "base_points": 1, "unique": False, "copies": 5, "paired_with": None},
    {"name": "Mine",            "card_type": "green_production",   "category": "construction", "cost_twig": 1, "cost_resin": 1, "cost_pebble": 1, "cost_berry": 0, "base_points": 1, "unique": False, "copies": 4, "paired_with": None},
    {"name": "Resin Refinery",  "card_type": "green_production",   "category": "construction", "cost_twig": 1, "cost_resin": 0, "cost_pebble": 1, "cost_berry": 0, "base_points": 1, "unique": False, "copies": 3, "paired_with": None},
    {"name": "Storehouse",      "card_type": "green_production",   "category": "construction", "cost_twig": 1, "cost_resin": 1, "cost_pebble": 0, "cost_berry": 0, "base_points": 1, "unique": False, "copies": 4, "paired_with": None},
    {"name": "Twig Barge",      "card_type": "green_production",   "category": "construction", "cost_twig": 1, "cost_resin": 0, "cost_pebble": 1, "cost_berry": 0, "base_points": 1, "unique": False, "copies": 3, "paired_with": None},

    # --- RED DESTINATION ---
    {"name": "Cemetery",        "card_type": "red_destination",    "category": "construction", "cost_twig": 2, "cost_resin": 1, "cost_pebble": 0, "cost_berry": 0, "base_points": 0, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Chapel",          "card_type": "red_destination",    "category": "construction", "cost_twig": 2, "cost_resin": 1, "cost_pebble": 1, "cost_berry": 0, "base_points": 2, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Dungeon",         "card_type": "red_destination",    "category": "construction", "cost_twig": 0, "cost_resin": 1, "cost_pebble": 2, "cost_berry": 0, "base_points": 0, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Inn",             "card_type": "red_destination",    "category": "construction", "cost_twig": 2, "cost_resin": 1, "cost_pebble": 0, "cost_berry": 0, "base_points": 2, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Lookout",         "card_type": "red_destination",    "category": "construction", "cost_twig": 1, "cost_resin": 1, "cost_pebble": 1, "cost_berry": 0, "base_points": 2, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Monastery",       "card_type": "red_destination",    "category": "construction", "cost_twig": 1, "cost_resin": 1, "cost_pebble": 1, "cost_berry": 0, "base_points": 2, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Post Office",     "card_type": "red_destination",    "category": "construction", "cost_twig": 1, "cost_resin": 2, "cost_pebble": 0, "cost_berry": 0, "base_points": 2, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "University",      "card_type": "red_destination",    "category": "construction", "cost_twig": 1, "cost_resin": 1, "cost_pebble": 2, "cost_berry": 0, "base_points": 3, "unique": True,  "copies": 2, "paired_with": None},

    # --- BLUE GOVERNANCE ---
    {"name": "Courthouse",      "card_type": "blue_governance",    "category": "construction", "cost_twig": 1, "cost_resin": 1, "cost_pebble": 2, "cost_berry": 0, "base_points": 2, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Crane",           "card_type": "blue_governance",    "category": "construction", "cost_twig": 1, "cost_resin": 0, "cost_pebble": 0, "cost_berry": 0, "base_points": 1, "unique": True,  "copies": 2, "paired_with": None},

    # --- PURPLE PROSPERITY ---
    {"name": "Castle",          "card_type": "purple_prosperity",  "category": "construction", "cost_twig": 2, "cost_resin": 3, "cost_pebble": 3, "cost_berry": 0, "base_points": 4, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Ever Tree",       "card_type": "purple_prosperity",  "category": "construction", "cost_twig": 3, "cost_resin": 3, "cost_pebble": 3, "cost_berry": 0, "base_points": 5, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Palace",          "card_type": "purple_prosperity",  "category": "construction", "cost_twig": 2, "cost_resin": 3, "cost_pebble": 3, "cost_berry": 0, "base_points": 4, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "School",          "card_type": "purple_prosperity",  "category": "construction", "cost_twig": 2, "cost_resin": 2, "cost_pebble": 0, "cost_berry": 0, "base_points": 2, "unique": True,  "copies": 2, "paired_with": None},
    {"name": "Theater",         "card_type": "purple_prosperity",  "category": "construction", "cost_twig": 3, "cost_resin": 1, "cost_pebble": 1, "cost_berry": 0, "base_points": 3, "unique": True,  "copies": 2, "paired_with": None},
]
# fmt: on

ALL_CARD_DEFS: list[CardDef] = CRITTER_DEFS + CONSTRUCTION_DEFS


def _verify_total() -> int:
    """Return total card count across all definitions."""
    return sum(d["copies"] for d in ALL_CARD_DEFS)


# Sanity check at import time
_total = _verify_total()
if _total != 128:
    raise RuntimeError(
        f"Card definitions total {_total} cards, expected 128. "
        "Check copy counts in card_data.py."
    )
