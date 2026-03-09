"""Perspective-filtered game state serialization for Everdell.

When sending game state to a player, hide private information:
- Other players' hands (show hand_size only)
- Deck order (show deck_size only)
- Other players' valid actions

Show all public information:
- All players' cities, resources, workers, seasons
- Meadow, events, locations
- Deck/discard sizes
- Current player turn
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from ed_engine.engine.actions import GameAction
from ed_engine.models.card import Card
from ed_engine.models.player import Player

# Avoid circular import — GameManager used only for type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ed_engine.engine.game_manager import GameManager


class PerspectiveFilter:
    """Filters game state for a specific player's view."""

    @staticmethod
    def serialize_card(card: Card) -> dict[str, Any]:
        """Convert a Card to a JSON-safe dict."""
        return {
            "name": card.name,
            "card_type": card.card_type.value if hasattr(card.card_type, "value") else str(card.card_type),
            "category": card.category.value if hasattr(card.category, "value") else str(card.category),
            "cost": card.cost.to_dict(),
            "base_points": card.base_points,
            "unique": card.unique,
            "paired_with": card.paired_with,
            "occupies_city_space": card.occupies_city_space,
            "is_open_destination": card.is_open_destination,
        }

    @staticmethod
    def serialize_player(player: Player, is_self: bool = False) -> dict[str, Any]:
        """Convert Player to dict. If is_self, include hand. Otherwise hand_size only."""
        result: dict[str, Any] = {
            "id": str(player.id),
            "name": player.name,
            "resources": player.resources.to_dict(),
            "city": [PerspectiveFilter.serialize_card(c) for c in player.city],
            "workers_total": player.workers_total,
            "workers_placed": player.workers_placed,
            "workers_deployed": list(player.workers_deployed),
            "season": player.season.value if hasattr(player.season, "value") else str(player.season),
            "score": player.score,
            "has_passed": player.has_passed,
        }
        if is_self:
            result["hand"] = [PerspectiveFilter.serialize_card(c) for c in player.hand]
        result["hand_size"] = len(player.hand)
        return result

    @staticmethod
    def _serialize_action(action: GameAction) -> dict[str, Any]:
        """Convert a GameAction to a JSON-safe dict."""
        result: dict[str, Any] = {
            "action_type": str(action.action_type),
        }
        if action.location_id:
            result["location_id"] = action.location_id
        if action.card_name:
            result["card_name"] = action.card_name
        if action.source:
            result["source"] = action.source
        if action.meadow_index is not None:
            result["meadow_index"] = action.meadow_index
        if action.use_paired_construction:
            result["use_paired_construction"] = True
        if action.event_id:
            result["event_id"] = action.event_id
        if action.discard_cards:
            result["discard_cards"] = action.discard_cards
        if action.choice_index is not None:
            result["choice_index"] = action.choice_index
        return result

    @staticmethod
    def serialize_for_api(game_manager: GameManager, player_id: str | None = None) -> dict[str, Any]:
        """Create a full serialized game state for API response.

        If player_id is None, return spectator view (no hands visible).
        If player_id is provided, show that player's hand but hide others'.
        player_id should be the GameManager's internal UUID string.
        """
        game = game_manager.game
        current_player = game_manager.get_current_player()
        current_player_id = str(current_player.id) if current_player else None

        # Serialize players with perspective filtering
        players = []
        for p in game.players:
            is_self = (player_id is not None and str(p.id) == player_id)
            players.append(PerspectiveFilter.serialize_player(p, is_self=is_self))

        # Meadow (public)
        meadow = [PerspectiveFilter.serialize_card(c) for c in game.meadow]

        # Events (public)
        events = {
            "basic_events": dict(game.basic_events),
            "special_events": dict(game.special_events),
        }

        # Locations (public)
        location_mgr = game_manager._location_mgr
        forest_locations = []
        basic_locations = []
        haven_locations = []
        journey_locations = []
        for loc in location_mgr.all_locations:
            loc_dict = {
                "id": loc.id,
                "name": loc.name,
                "location_type": loc.location_type.value if hasattr(loc.location_type, "value") else str(loc.location_type),
                "exclusive": loc.exclusive,
                "workers": list(loc.workers),
            }
            loc_type_val = loc.location_type.value if hasattr(loc.location_type, "value") else str(loc.location_type)
            if loc_type_val == "forest":
                forest_locations.append(loc_dict)
            elif loc_type_val == "basic":
                basic_locations.append(loc_dict)
            elif loc_type_val == "haven":
                haven_locations.append(loc_dict)
            elif loc_type_val == "journey":
                loc_dict["point_value"] = getattr(loc, "point_value", 0)
                journey_locations.append(loc_dict)

        # Valid actions — only for the requesting player, and only if it's their turn
        valid_actions: list[dict[str, Any]] = []
        if player_id and current_player_id == player_id:
            raw_actions = game_manager.get_valid_actions(player_id)
            valid_actions = [PerspectiveFilter._serialize_action(a) for a in raw_actions]

        # Deck info (sizes only, never order)
        deck_mgr = game_manager._deck_mgr

        return {
            "game_id": str(game.id),
            "turn_number": game.turn_number,
            "current_player_id": current_player_id,
            "players": players,
            "meadow": meadow,
            "deck_size": deck_mgr.deck_size,
            "discard_size": deck_mgr.discard_size,
            "events": events,
            "forest_locations": forest_locations,
            "basic_locations": basic_locations,
            "haven_locations": haven_locations,
            "journey_locations": journey_locations,
            "game_over": game.game_over,
            "valid_actions": valid_actions,
            "pending_choice": game.pending_choice,
        }

    @staticmethod
    def filter_state(game_state: dict, player_id: str | None = None) -> dict:
        """Filter a raw game state dict for a player's perspective.

        If player_id is None, return spectator view (no hands visible).
        If player_id is provided, show that player's hand but hide others'.
        """
        filtered = dict(game_state)

        # Remove deck contents — only keep size
        if "deck" in filtered:
            filtered["deck_size"] = len(filtered.pop("deck"))

        # Remove discard contents — only keep size
        if "discard" in filtered:
            filtered["discard_size"] = len(filtered.pop("discard"))

        # Filter player hands
        if "players" in filtered:
            new_players = []
            for p in filtered["players"]:
                p_copy = dict(p)
                pid = str(p_copy.get("id", ""))
                is_self = (player_id is not None and pid == player_id)
                if "hand" in p_copy:
                    p_copy["hand_size"] = len(p_copy["hand"])
                    if not is_self:
                        del p_copy["hand"]
                new_players.append(p_copy)
            filtered["players"] = new_players

        return filtered

    @staticmethod
    def serialize_for_ai(game_manager: GameManager, player_id: str) -> str:
        """Compact text format for AI prompt consumption (<2K tokens).

        Designed to give an AI agent all the information it needs to make
        a decision in a token-efficient format.
        """
        game = game_manager.game
        player = None
        for p in game.players:
            if str(p.id) == player_id:
                player = p
                break

        if player is None:
            return "ERROR: Unknown player_id"

        lines: list[str] = []

        # --- MY STATE ---
        lines.append("=== MY STATE ===")
        r = player.resources
        lines.append(f"Resources: {r.twig}T {r.resin}R {r.pebble}P {r.berry}B")
        avail = player.workers_total - player.workers_placed
        lines.append(f"Workers: {avail}/{player.workers_total} available")
        season_val = player.season.value if hasattr(player.season, "value") else str(player.season)
        lines.append(f"Season: {season_val.capitalize()}")
        hand_names = [c.name for c in player.hand]
        lines.append(f"Hand ({len(hand_names)}): [{', '.join(hand_names)}]")
        city_count = sum(1 for c in player.city if c.occupies_city_space)
        city_names = [c.name for c in player.city]
        lines.append(f"City ({city_count}/15): [{', '.join(city_names)}]")

        # --- MEADOW ---
        lines.append("")
        lines.append("=== MEADOW ===")
        meadow_parts = []
        for i, card in enumerate(game.meadow):
            cost_parts = []
            if card.cost.twig:
                cost_parts.append(f"{card.cost.twig}T")
            if card.cost.resin:
                cost_parts.append(f"{card.cost.resin}R")
            if card.cost.pebble:
                cost_parts.append(f"{card.cost.pebble}P")
            if card.cost.berry:
                cost_parts.append(f"{card.cost.berry}B")
            cost_str = "".join(cost_parts) or "free"
            meadow_parts.append(f"[{i + 1}] {card.name} ({card.base_points}pt, {cost_str})")
        lines.append(" ".join(meadow_parts))

        # --- OPPONENTS ---
        lines.append("")
        lines.append("=== OPPONENTS ===")
        for p in game.players:
            if str(p.id) == player_id:
                continue
            r2 = p.resources
            avail2 = p.workers_total - p.workers_placed
            city_sz = sum(1 for c in p.city if c.occupies_city_space)
            lines.append(
                f"{p.name}: {r2.twig}T {r2.resin}R {r2.pebble}P {r2.berry}B"
                f" | Workers {avail2}/{p.workers_total}"
                f" | City {city_sz}/15"
                f" | Hand {len(p.hand)}"
            )

        # --- VALID ACTIONS ---
        lines.append("")
        lines.append("=== VALID ACTIONS ===")
        current = game_manager.get_current_player()
        if current and str(current.id) == player_id:
            actions = game_manager.get_valid_actions(player_id)
            for i, a in enumerate(actions, 1):
                desc = _describe_action(a, player, game)
                lines.append(f"{i}. {desc}")
        else:
            lines.append("(not your turn)")

        return "\n".join(lines)


def _describe_action(action: GameAction, player: Player, game: Any) -> str:
    """Human-readable single-line description of an action."""
    at = action.action_type
    if at == "place_worker":
        return f"PLACE_WORKER at \"{action.location_id}\""
    elif at == "play_card":
        # Find the card to show cost
        card = None
        if action.source == "hand":
            for c in player.hand:
                if c.name == action.card_name:
                    card = c
                    break
        elif action.source == "meadow" and action.meadow_index is not None:
            if 0 <= action.meadow_index < len(game.meadow):
                card = game.meadow[action.meadow_index]

        source_str = f"from {action.source}"
        if action.source == "meadow" and action.meadow_index is not None:
            source_str = f"from meadow[{action.meadow_index + 1}]"

        if action.use_paired_construction and card:
            return f"PLAY_CARD \"{action.card_name}\" {source_str} (free via {card.paired_with})"

        cost_str = ""
        if card:
            parts = []
            if card.cost.twig:
                parts.append(f"{card.cost.twig}T")
            if card.cost.resin:
                parts.append(f"{card.cost.resin}R")
            if card.cost.pebble:
                parts.append(f"{card.cost.pebble}P")
            if card.cost.berry:
                parts.append(f"{card.cost.berry}B")
            cost_str = f" (cost: {''.join(parts)})" if parts else " (free)"

        return f"PLAY_CARD \"{action.card_name}\" {source_str}{cost_str}"
    elif at == "prepare_for_season":
        return "PREPARE_FOR_SEASON"
    elif at == "claim_event":
        return f"CLAIM_EVENT \"{action.event_id}\""
    return str(action.action_type)
