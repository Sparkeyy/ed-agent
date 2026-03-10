"""Encode Everdell game state into a fixed-size float tensor for RL.

Handles both direct GameManager access (training) and API state dicts (inference).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from ed_engine.engine.game_manager import GameManager
    from ed_engine.models.player import Player

# All 48 unique card names in sorted order — canonical index mapping
CARD_NAMES: list[str] = [
    "Architect", "Bard", "Barge Toad", "Castle", "Cemetery", "Chapel",
    "Chip Sweep", "Clock Tower", "Courthouse", "Crane", "Doctor", "Dungeon",
    "Ever Tree", "Fair Grounds", "Farm", "Fool", "Gatherer", "General Store",
    "Harvester", "Historian", "Inn", "Innkeeper", "Judge", "King", "Lookout",
    "Mine", "Miner Mole", "Monastery", "Monk", "Palace", "Peddler",
    "Post Office", "Postal Pigeon", "Queen", "Ranger", "Resin Refinery",
    "Ruins", "School", "Shepherd", "Shopkeeper", "Storehouse", "Teacher",
    "Theater", "Twig Barge", "Undertaker", "University", "Wanderer", "Woodcarver",
]
CARD_TO_IDX: dict[str, int] = {name: i for i, name in enumerate(CARD_NAMES)}
NUM_CARDS = len(CARD_NAMES)  # 48

# Card type indices for composition features
CARD_TYPE_NAMES = [
    "tan_traveler", "green_production", "red_destination",
    "blue_governance", "purple_prosperity",
]
CARD_TYPE_TO_IDX: dict[str, int] = {t: i for i, t in enumerate(CARD_TYPE_NAMES)}

# Season one-hot indices
SEASON_NAMES = ["winter", "spring", "summer", "autumn"]
SEASON_TO_IDX: dict[str, int] = {s: i for i, s in enumerate(SEASON_NAMES)}

# Basic event IDs (always present, fixed order)
BASIC_EVENT_IDS = [
    "basic_governance", "basic_destination", "basic_traveler", "basic_production",
]

# All 16 possible special event IDs (4 chosen per game)
ALL_SPECIAL_EVENT_IDS = [
    "se_performer_in_residence", "se_ancient_scrolls_discovered",
    "se_unexpected_bounty", "se_remembering_fallen",
    "se_brilliant_marketing_plan", "se_under_new_management",
    "se_well_run_city", "se_tax_relief",
    "se_path_of_pilgrims", "se_ministering_to_miscreants",
    "se_evening_of_fireworks", "se_pristine_chapel_ceiling",
    "se_graduation_of_scholars", "se_croak_wart_cure",
    "se_capture_acorn_thieves", "se_flying_doctor_service",
]
SPECIAL_EVENT_TO_IDX: dict[str, int] = {eid: i for i, eid in enumerate(ALL_SPECIAL_EVENT_IDS)}

# Basic location IDs (fixed order)
BASIC_LOCATION_IDS = [
    "basic_3twigs", "basic_2twigs_1card", "basic_2resin", "basic_1resin_1card",
    "basic_2cards_1point", "basic_1pebble", "basic_1berry_1card", "basic_1berry",
]

# Forest location IDs (variable per game, up to 4)
ALL_FOREST_IDS = [f"forest_{i:02d}" for i in range(1, 12)]

# Other fixed locations
OTHER_LOCATION_IDS = [
    "haven",
    "journey_2pt", "journey_3pt", "journey_4pt", "journey_5pt",
]

# Feature block sizes
_SELF_RESOURCES = 4
_SELF_WORKERS = 2
_SELF_SEASON = 4
_SELF_CITY = NUM_CARDS  # 48, multi-hot (count for commons)
_SELF_CITY_COMP = 6  # 5 type counts + total/15
_SELF_HAND = NUM_CARDS  # 48
_SELF_HAND_SIZE = 1
_SELF_BLOCK = _SELF_RESOURCES + _SELF_WORKERS + _SELF_SEASON + _SELF_CITY + _SELF_CITY_COMP + _SELF_HAND + _SELF_HAND_SIZE  # 113

_OPP_RESOURCES = 4
_OPP_WORKERS = 2
_OPP_SEASON = 4
_OPP_CITY = NUM_CARDS  # 48
_OPP_CITY_COMP = 6
_OPP_HAND_SIZE = 1
_OPP_BLOCK = _OPP_RESOURCES + _OPP_WORKERS + _OPP_SEASON + _OPP_CITY + _OPP_CITY_COMP + _OPP_HAND_SIZE  # 65

_MEADOW = NUM_CARDS  # 48
_DECK_DISCARD = 2
_BASIC_EVENTS = 4
_SPECIAL_EVENTS = 16  # all possible, binary presence + claimed
_LOCATIONS = len(BASIC_LOCATION_IDS) + len(ALL_FOREST_IDS) + len(OTHER_LOCATION_IDS)  # 24
_TURN_PHASE = 2
_HAS_PENDING = 1

STATE_SIZE = (
    _SELF_BLOCK
    + 3 * _OPP_BLOCK
    + _MEADOW
    + _DECK_DISCARD
    + _BASIC_EVENTS
    + _SPECIAL_EVENTS
    + _LOCATIONS
    + _TURN_PHASE
    + _HAS_PENDING
)
# 113 + 3*65 + 48 + 2 + 4 + 16 + 24 + 2 + 1 = 405


def _encode_resources(res: Any) -> list[float]:
    """Encode resources normalized to [0, 1] range (cap at 10)."""
    if isinstance(res, dict):
        return [
            min(res.get("twig", 0), 10) / 10.0,
            min(res.get("resin", 0), 10) / 10.0,
            min(res.get("pebble", 0), 10) / 10.0,
            min(res.get("berry", 0), 10) / 10.0,
        ]
    # ResourceBank object
    return [
        min(res.twig, 10) / 10.0,
        min(res.resin, 10) / 10.0,
        min(res.pebble, 10) / 10.0,
        min(res.berry, 10) / 10.0,
    ]


def _encode_city_multihot(cards: list) -> list[float]:
    """Multi-hot encoding of cards in city (count for commons)."""
    vec = [0.0] * NUM_CARDS
    for card in cards:
        name = card.name if hasattr(card, "name") else card.get("name", "")
        idx = CARD_TO_IDX.get(name)
        if idx is not None:
            vec[idx] += 1.0
    return vec


def _encode_city_composition(cards: list) -> list[float]:
    """Count per card type + total city size normalized."""
    type_counts = [0.0] * 5
    for card in cards:
        ct = card.card_type.value if hasattr(card, "card_type") else card.get("card_type", "")
        idx = CARD_TYPE_TO_IDX.get(ct)
        if idx is not None:
            type_counts[idx] += 1.0
    # Normalize type counts by max reasonable (e.g., 8 of one type)
    type_counts = [c / 8.0 for c in type_counts]
    total = len(cards) / 15.0
    return type_counts + [total]


def _encode_hand_multihot(cards: list) -> list[float]:
    """Multi-hot encoding of cards in hand."""
    vec = [0.0] * NUM_CARDS
    for card in cards:
        name = card.name if hasattr(card, "name") else card.get("name", "")
        idx = CARD_TO_IDX.get(name)
        if idx is not None:
            vec[idx] += 1.0
    return vec


def _encode_season(season: str) -> list[float]:
    """One-hot season encoding."""
    vec = [0.0] * 4
    idx = SEASON_TO_IDX.get(season.lower() if isinstance(season, str) else season.value, 0)
    vec[idx] = 1.0
    return vec


def encode_state_from_game(gm: GameManager, player_idx: int) -> np.ndarray:
    """Encode state directly from GameManager (for training).

    Args:
        gm: The GameManager instance
        player_idx: Index of the player whose perspective we encode

    Returns:
        numpy array of shape (STATE_SIZE,) with float32 values
    """
    game = gm.game
    players = game.players
    self_player = players[player_idx]

    features: list[float] = []

    # === Self player ===
    features.extend(_encode_resources(self_player.resources))
    workers_avail = max(0, self_player.workers_total - self_player.workers_placed)
    features.extend([
        workers_avail / max(self_player.workers_total, 1),
        self_player.workers_placed / max(self_player.workers_total, 1),
    ])
    season_str = self_player.season.value if hasattr(self_player.season, "value") else str(self_player.season)
    features.extend(_encode_season(season_str))
    features.extend(_encode_city_multihot(self_player.city))
    features.extend(_encode_city_composition(self_player.city))
    features.extend(_encode_hand_multihot(self_player.hand))
    features.append(len(self_player.hand) / 8.0)

    # === Opponents (up to 3, padded with zeros) ===
    opponent_indices = [i for i in range(len(players)) if i != player_idx]
    for opp_slot in range(3):
        if opp_slot < len(opponent_indices):
            opp = players[opponent_indices[opp_slot]]
            features.extend(_encode_resources(opp.resources))
            opp_avail = max(0, opp.workers_total - opp.workers_placed)
            features.extend([
                opp_avail / max(opp.workers_total, 1),
                opp.workers_placed / max(opp.workers_total, 1),
            ])
            opp_season = opp.season.value if hasattr(opp.season, "value") else str(opp.season)
            features.extend(_encode_season(opp_season))
            features.extend(_encode_city_multihot(opp.city))
            features.extend(_encode_city_composition(opp.city))
            # Only hand size for opponents (hidden info)
            features.append(len(opp.hand) / 8.0)
        else:
            features.extend([0.0] * _OPP_BLOCK)

    # === Meadow ===
    features.extend(_encode_city_multihot(game.meadow))

    # === Deck/discard sizes ===
    features.append(len(game.deck) / 128.0)
    features.append(len(game.discard) / 128.0)

    # === Basic events (claimed = 0, unclaimed = 1) ===
    for eid in BASIC_EVENT_IDS:
        ev_data = game.basic_events.get(eid, {})
        claimed = ev_data.get("claimed_by") is not None if isinstance(ev_data, dict) else False
        features.append(0.0 if claimed else 1.0)

    # === Special events (presence + claimed status) ===
    for eid in ALL_SPECIAL_EVENT_IDS:
        ev_data = game.special_events.get(eid)
        if ev_data is None:
            features.append(0.0)  # Not in this game
        else:
            claimed = ev_data.get("claimed_by") is not None if isinstance(ev_data, dict) else False
            features.append(0.0 if claimed else 1.0)

    # === Locations (available = 1, occupied = 0) ===
    # We encode presence and availability using location manager
    loc_mgr = gm._location_mgr
    pid_str = str(self_player.id)
    all_loc_ids = BASIC_LOCATION_IDS + ALL_FOREST_IDS + OTHER_LOCATION_IDS
    for lid in all_loc_ids:
        loc = loc_mgr.get_location(lid)
        if loc is None:
            features.append(0.0)  # Not in this game
        else:
            features.append(1.0 if loc.is_available(pid_str) else 0.0)

    # === Turn/phase ===
    features.append(min(game.turn_number, 60) / 60.0)
    # Game progress: fraction of players who have passed
    passed = sum(1 for p in players if p.has_passed)
    features.append(passed / max(len(players), 1))

    # === Pending choice ===
    features.append(1.0 if game.pending_choice else 0.0)

    arr = np.array(features, dtype=np.float32)
    assert arr.shape == (STATE_SIZE,), f"Expected {STATE_SIZE}, got {arr.shape[0]}"
    return arr


def encode_state_from_dict(state: dict[str, Any], player_id: str) -> np.ndarray:
    """Encode state from API state dict (for inference).

    Args:
        state: Game state dict from the API
        player_id: ID of the player whose perspective we encode

    Returns:
        numpy array of shape (STATE_SIZE,) with float32 values
    """
    players = state.get("players", [])
    self_player = None
    self_idx = 0
    for i, p in enumerate(players):
        if str(p.get("id", "")) == str(player_id):
            self_player = p
            self_idx = i
            break

    if self_player is None and players:
        self_player = players[0]
        self_idx = 0

    if self_player is None:
        return np.zeros(STATE_SIZE, dtype=np.float32)

    features: list[float] = []

    # === Self player ===
    res = self_player.get("resources", {})
    features.extend(_encode_resources(res))
    wt = self_player.get("workers_total", 2)
    wp = self_player.get("workers_placed", 0)
    features.extend([
        max(0, wt - wp) / max(wt, 1),
        wp / max(wt, 1),
    ])
    features.extend(_encode_season(self_player.get("season", "winter")))
    features.extend(_encode_city_multihot(self_player.get("city", [])))
    features.extend(_encode_city_composition(self_player.get("city", [])))
    features.extend(_encode_hand_multihot(self_player.get("hand", [])))
    features.append(
        self_player.get("hand_size", len(self_player.get("hand", []))) / 8.0
    )

    # === Opponents ===
    opponent_players = [p for i, p in enumerate(players) if i != self_idx]
    for opp_slot in range(3):
        if opp_slot < len(opponent_players):
            opp = opponent_players[opp_slot]
            features.extend(_encode_resources(opp.get("resources", {})))
            owt = opp.get("workers_total", 2)
            owp = opp.get("workers_placed", 0)
            features.extend([
                max(0, owt - owp) / max(owt, 1),
                owp / max(owt, 1),
            ])
            features.extend(_encode_season(opp.get("season", "winter")))
            features.extend(_encode_city_multihot(opp.get("city", [])))
            features.extend(_encode_city_composition(opp.get("city", [])))
            features.append(opp.get("hand_size", 0) / 8.0)
        else:
            features.extend([0.0] * _OPP_BLOCK)

    # === Meadow ===
    features.extend(_encode_city_multihot(state.get("meadow", [])))

    # === Deck/discard ===
    features.append(state.get("deck_size", 0) / 128.0)
    features.append(state.get("discard_size", 0) / 128.0)

    # === Basic events ===
    basic_events = state.get("events", state).get("basic_events", state.get("basic_events", {}))
    for eid in BASIC_EVENT_IDS:
        ev = basic_events.get(eid, {})
        claimed = ev.get("claimed_by") is not None if isinstance(ev, dict) else False
        features.append(0.0 if claimed else 1.0)

    # === Special events ===
    special_events = state.get("events", state).get("special_events", state.get("special_events", {}))
    for eid in ALL_SPECIAL_EVENT_IDS:
        ev = special_events.get(eid)
        if ev is None:
            features.append(0.0)
        else:
            claimed = ev.get("claimed_by") is not None if isinstance(ev, dict) else False
            features.append(0.0 if claimed else 1.0)

    # === Locations ===
    # From API state, locations come as lists with occupancy info
    basic_locs = state.get("basic_locations", [])
    forest_locs = state.get("forest_locations", [])
    haven_locs = state.get("haven_locations", [])
    journey_locs = state.get("journey_locations", [])

    # Build lookup by ID
    loc_lookup: dict[str, dict] = {}
    for loc_list in [basic_locs, forest_locs, haven_locs, journey_locs]:
        if isinstance(loc_list, list):
            for loc in loc_list:
                if isinstance(loc, dict):
                    loc_lookup[loc.get("id", "")] = loc

    all_loc_ids = BASIC_LOCATION_IDS + ALL_FOREST_IDS + OTHER_LOCATION_IDS
    for lid in all_loc_ids:
        loc = loc_lookup.get(lid)
        if loc is None:
            features.append(0.0)
        else:
            workers = loc.get("workers", [])
            if loc.get("exclusive", True):
                features.append(0.0 if workers else 1.0)
            else:
                features.append(0.0 if player_id in [str(w) for w in workers] else 1.0)

    # === Turn/phase ===
    features.append(min(state.get("turn_number", 1), 60) / 60.0)
    passed = sum(1 for p in players if p.get("has_passed", False))
    features.append(passed / max(len(players), 1))

    # === Pending choice ===
    features.append(1.0 if state.get("pending_choice") else 0.0)

    arr = np.array(features, dtype=np.float32)
    # Pad or truncate to STATE_SIZE
    if arr.shape[0] < STATE_SIZE:
        arr = np.pad(arr, (0, STATE_SIZE - arr.shape[0]))
    elif arr.shape[0] > STATE_SIZE:
        arr = arr[:STATE_SIZE]
    return arr
