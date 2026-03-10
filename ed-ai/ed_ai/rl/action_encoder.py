"""Action encoder: bijection between GameAction and fixed action indices.

Maps the variable-cardinality action space to a fixed 210-slot discrete space
with binary masking for valid actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from ed_engine.engine.actions import GameAction

from ed_ai.rl.state_encoder import (
    ALL_FOREST_IDS,
    BASIC_LOCATION_IDS,
    CARD_NAMES,
    CARD_TO_IDX,
    NUM_CARDS,
    OTHER_LOCATION_IDS,
)

# --- Action space layout ---
# Each block has a fixed offset and size.

# Place worker: basic locations (8)
_PW_BASIC_OFFSET = 0
_PW_BASIC_SIZE = len(BASIC_LOCATION_IDS)  # 8

# Place worker: forest locations (11)
_PW_FOREST_OFFSET = _PW_BASIC_OFFSET + _PW_BASIC_SIZE  # 8
_PW_FOREST_SIZE = len(ALL_FOREST_IDS)  # 11

# Place worker: haven (1)
_PW_HAVEN_OFFSET = _PW_FOREST_OFFSET + _PW_FOREST_SIZE  # 19
_PW_HAVEN_SIZE = 1

# Place worker: journey (4)
_PW_JOURNEY_OFFSET = _PW_HAVEN_OFFSET + _PW_HAVEN_SIZE  # 20
_PW_JOURNEY_SIZE = 4

# Place worker: destination cards (48)
_PW_DEST_OFFSET = _PW_JOURNEY_OFFSET + _PW_JOURNEY_SIZE  # 24
_PW_DEST_SIZE = NUM_CARDS  # 48

# Play card from hand (48)
_PC_HAND_OFFSET = _PW_DEST_OFFSET + _PW_DEST_SIZE  # 72
_PC_HAND_SIZE = NUM_CARDS  # 48

# Play card from hand, paired construction (48)
_PC_HAND_PAIRED_OFFSET = _PC_HAND_OFFSET + _PC_HAND_SIZE  # 120
_PC_HAND_PAIRED_SIZE = NUM_CARDS  # 48

# Play card from meadow (8)
_PC_MEADOW_OFFSET = _PC_HAND_PAIRED_OFFSET + _PC_HAND_PAIRED_SIZE  # 168
_PC_MEADOW_SIZE = 8

# Play card from meadow, paired (8)
_PC_MEADOW_PAIRED_OFFSET = _PC_MEADOW_OFFSET + _PC_MEADOW_SIZE  # 176
_PC_MEADOW_PAIRED_SIZE = 8

# Prepare for season (1)
_PREPARE_OFFSET = _PC_MEADOW_PAIRED_OFFSET + _PC_MEADOW_PAIRED_SIZE  # 184
_PREPARE_SIZE = 1

# Claim event (8: 4 basic + 4 special)
_CLAIM_EVENT_OFFSET = _PREPARE_OFFSET + _PREPARE_SIZE  # 185
_CLAIM_EVENT_SIZE = 8

# Resolve choice (8 option slots)
_RESOLVE_OFFSET = _CLAIM_EVENT_OFFSET + _CLAIM_EVENT_SIZE  # 193
_RESOLVE_SIZE = 8

ACTION_SPACE_SIZE = _RESOLVE_OFFSET + _RESOLVE_SIZE  # 201

# Location ID to index mappings
_BASIC_LOC_TO_IDX = {lid: i for i, lid in enumerate(BASIC_LOCATION_IDS)}
_FOREST_LOC_TO_IDX = {lid: i for i, lid in enumerate(ALL_FOREST_IDS)}
_JOURNEY_LOCS = ["journey_2pt", "journey_3pt", "journey_4pt", "journey_5pt"]
_JOURNEY_LOC_TO_IDX = {lid: i for i, lid in enumerate(_JOURNEY_LOCS)}

# Event ID indexing — we use a dynamic mapping per game for special events
BASIC_EVENT_IDS_LIST = [
    "basic_governance", "basic_destination", "basic_traveler", "basic_production",
]


def encode_action(action: GameAction | dict[str, Any], event_id_map: dict[str, int] | None = None) -> int:
    """Convert a GameAction (or dict) to its action index.

    Args:
        action: GameAction object or action dict
        event_id_map: Mapping from special event IDs to indices 4-7

    Returns:
        Integer action index in [0, ACTION_SPACE_SIZE)
    """
    if isinstance(action, dict):
        at = action.get("action_type", "")
        card_name = action.get("card_name", "")
        location_id = action.get("location_id", "")
        source = action.get("source", "hand")
        meadow_index = action.get("meadow_index")
        use_paired = action.get("use_paired_construction", False)
        event_id = action.get("event_id", "")
        choice_index = action.get("choice_index", 0)
    else:
        at = action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type)
        card_name = action.card_name or ""
        location_id = action.location_id or ""
        source = action.source or "hand"
        meadow_index = action.meadow_index
        use_paired = action.use_paired_construction
        event_id = action.event_id or ""
        choice_index = action.choice_index or 0

    if at == "place_worker":
        # Check basic locations
        if location_id in _BASIC_LOC_TO_IDX:
            return _PW_BASIC_OFFSET + _BASIC_LOC_TO_IDX[location_id]
        # Forest
        if location_id in _FOREST_LOC_TO_IDX:
            return _PW_FOREST_OFFSET + _FOREST_LOC_TO_IDX[location_id]
        # Haven
        if location_id == "haven":
            return _PW_HAVEN_OFFSET
        # Journey
        if location_id in _JOURNEY_LOC_TO_IDX:
            return _PW_JOURNEY_OFFSET + _JOURNEY_LOC_TO_IDX[location_id]
        # Destination card — location_id might be a card name
        card_idx = CARD_TO_IDX.get(location_id)
        if card_idx is not None:
            return _PW_DEST_OFFSET + card_idx
        # If location_id contains a card name as destination
        if card_name and card_name in CARD_TO_IDX:
            return _PW_DEST_OFFSET + CARD_TO_IDX[card_name]
        # Fallback: hash to a destination slot
        return _PW_DEST_OFFSET + (hash(location_id) % NUM_CARDS)

    elif at == "play_card":
        card_idx = CARD_TO_IDX.get(card_name, 0)
        if source == "meadow" and meadow_index is not None:
            idx = min(meadow_index, 7)
            if use_paired:
                return _PC_MEADOW_PAIRED_OFFSET + idx
            return _PC_MEADOW_OFFSET + idx
        else:
            if use_paired:
                return _PC_HAND_PAIRED_OFFSET + card_idx
            return _PC_HAND_OFFSET + card_idx

    elif at == "prepare_for_season":
        return _PREPARE_OFFSET

    elif at == "claim_event":
        # Basic events: indices 0-3
        if event_id in BASIC_EVENT_IDS_LIST:
            return _CLAIM_EVENT_OFFSET + BASIC_EVENT_IDS_LIST.index(event_id)
        # Special events: indices 4-7 (mapped per game)
        if event_id_map and event_id in event_id_map:
            return _CLAIM_EVENT_OFFSET + event_id_map[event_id]
        # Fallback: use hash
        return _CLAIM_EVENT_OFFSET + 4 + (hash(event_id) % 4)

    elif at == "resolve_choice":
        ci = choice_index if choice_index is not None else 0
        return _RESOLVE_OFFSET + min(ci, _RESOLVE_SIZE - 1)

    return 0  # Fallback


def decode_action(
    action_idx: int,
    valid_actions: list[dict[str, Any]] | list[Any],
    event_id_map: dict[str, int] | None = None,
) -> dict[str, Any] | None:
    """Convert an action index back to the matching valid action dict.

    Finds the valid action that maps to this index. Returns None if no match.
    """
    for va in valid_actions:
        if encode_action(va, event_id_map) == action_idx:
            if isinstance(va, dict):
                return va
            return va.model_dump()
    return None


def build_action_mask(
    valid_actions: list[dict[str, Any]] | list[Any],
    event_id_map: dict[str, int] | None = None,
) -> np.ndarray:
    """Build a binary mask of valid actions.

    Args:
        valid_actions: List of valid GameAction dicts or objects
        event_id_map: Mapping from special event IDs to indices 4-7

    Returns:
        numpy array of shape (ACTION_SPACE_SIZE,) with 1.0 for valid, 0.0 for invalid
    """
    mask = np.zeros(ACTION_SPACE_SIZE, dtype=np.float32)
    for va in valid_actions:
        idx = encode_action(va, event_id_map)
        if 0 <= idx < ACTION_SPACE_SIZE:
            mask[idx] = 1.0
    return mask


def build_event_id_map(game_state: Any) -> dict[str, int]:
    """Build special event ID → index (4-7) mapping for this game.

    Works with both GameState objects and API state dicts.
    """
    mapping: dict[str, int] = {}
    if isinstance(game_state, dict):
        events = game_state.get("events", game_state)
        special = events.get("special_events", game_state.get("special_events", {}))
    else:
        special = game_state.special_events

    slot = 4
    for eid in special:
        if slot > 7:
            break
        mapping[eid] = slot
        slot += 1
    return mapping
