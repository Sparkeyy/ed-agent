from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

from ed_engine.engine.seasons import SeasonManager
from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.resources import ResourceBank

if TYPE_CHECKING:
    from ed_engine.engine.deck import DeckManager
    from ed_engine.engine.locations import LocationManager
    from ed_engine.models.game import GameState
    from ed_engine.models.player import Player


class ActionType(str, Enum):
    PLACE_WORKER = "place_worker"
    PLAY_CARD = "play_card"
    PREPARE_FOR_SEASON = "prepare_for_season"
    CLAIM_EVENT = "claim_event"
    RESOLVE_CHOICE = "resolve_choice"


class GameAction(BaseModel):
    action_type: ActionType
    player_id: str
    # For place_worker:
    location_id: str | None = None
    # For play_card:
    card_name: str | None = None
    source: str | None = None  # "hand" or "meadow"
    meadow_index: int | None = None
    # For card abilities that need choices:
    target: str | None = None
    payment: ResourceBank | None = None
    # For free critter via paired construction:
    use_paired_construction: bool = False
    # For claim_event:
    event_id: str | None = None
    # For haven/journey discard:
    discard_cards: list[str] | None = None
    # For resolve_choice (generic choice index into pending_choice options):
    choice_index: int | None = None

    model_config = {"use_enum_values": True}


# Maximum city size in Everdell
MAX_CITY_SIZE = 15


class ActionHandler:
    """Validates and executes game actions."""

    @staticmethod
    def get_valid_actions(
        game: GameState,
        player: Player,
        location_mgr: LocationManager,
        deck_mgr: DeckManager,
    ) -> list[GameAction]:
        """Return all legal actions for this player."""
        actions: list[GameAction] = []
        player_id = str(player.id)

        if player.has_passed:
            return actions

        # If there's a pending choice, only resolve_choice actions are valid
        if game.pending_choice and game.pending_choice.get("player_id") == player_id:
            return ActionHandler._get_pending_choice_actions(game, player, deck_mgr)

        # 1. Place worker actions
        available_workers = player.workers_total - player.workers_placed
        if available_workers > 0:
            available_locs = location_mgr.get_available_locations(
                player_id, player.season
            )
            for loc in available_locs:
                actions.append(
                    GameAction(
                        action_type=ActionType.PLACE_WORKER,
                        player_id=player_id,
                        location_id=loc.id,
                    )
                )

            # Destination cards in player's city as worker spots
            for card in player.city:
                if card.is_open_destination:
                    dest_id = f"destination:{card.name}"
                    # Check not already visited this season
                    if dest_id not in player.workers_deployed:
                        actions.append(
                            GameAction(
                                action_type=ActionType.PLACE_WORKER,
                                player_id=player_id,
                                location_id=dest_id,
                            )
                        )

        # 2. Play card actions
        city_size = sum(1 for c in player.city if c.occupies_city_space)
        has_city_space = city_size < MAX_CITY_SIZE
        city_names = {c.name for c in player.city}

        def _can_place(card) -> bool:
            """Check if card can be placed in city (uniqueness + space)."""
            if card.unique and card.name in city_names:
                return False
            if card.occupies_city_space and not has_city_space:
                return False
            return True

        if has_city_space or any(not c.occupies_city_space for c in player.hand):
            # From hand
            for card in player.hand:
                if not _can_place(card):
                    continue
                # Check if can afford normally
                if player.resources.can_afford(card.cost):
                    actions.append(
                        GameAction(
                            action_type=ActionType.PLAY_CARD,
                            player_id=player_id,
                            card_name=card.name,
                            source="hand",
                        )
                    )
                # Check if can play free via paired construction
                if card.category == CardCategory.CRITTER and card.paired_with:
                    has_pair = any(
                        c.name == card.paired_with for c in player.city
                    )
                    if has_pair:
                        actions.append(
                            GameAction(
                                action_type=ActionType.PLAY_CARD,
                                player_id=player_id,
                                card_name=card.name,
                                source="hand",
                                use_paired_construction=True,
                            )
                        )

            # From meadow
            for idx, card in enumerate(deck_mgr.meadow):
                if not _can_place(card):
                    continue
                if player.resources.can_afford(card.cost):
                    actions.append(
                        GameAction(
                            action_type=ActionType.PLAY_CARD,
                            player_id=player_id,
                            card_name=card.name,
                            source="meadow",
                            meadow_index=idx,
                        )
                    )
                # Check paired construction for meadow critters too
                if card.category == CardCategory.CRITTER and card.paired_with:
                    has_pair = any(
                        c.name == card.paired_with for c in player.city
                    )
                    if has_pair:
                        actions.append(
                            GameAction(
                                action_type=ActionType.PLAY_CARD,
                                player_id=player_id,
                                card_name=card.name,
                                source="meadow",
                                meadow_index=idx,
                                use_paired_construction=True,
                            )
                        )

        # 3. Prepare for season
        if SeasonManager.can_prepare_for_season(player):
            actions.append(
                GameAction(
                    action_type=ActionType.PREPARE_FOR_SEASON,
                    player_id=player_id,
                )
            )

        # 4. Claim event actions (only events the player qualifies for)
        player_card_names = {c.name for c in player.city}
        player_card_types = {}
        for c in player.city:
            ct = c.card_type.value if hasattr(c.card_type, "value") else str(c.card_type)
            player_card_types[ct] = player_card_types.get(ct, 0) + 1

        for event_id, event_data in game.basic_events.items():
            if isinstance(event_data, dict) and not event_data.get("claimed_by"):
                # Basic events require 3+ of a card type
                qualified = False
                if "governance" in event_id and player_card_types.get("blue_governance", 0) >= 3:
                    qualified = True
                elif "destination" in event_id and player_card_types.get("red_destination", 0) >= 3:
                    qualified = True
                elif "traveler" in event_id and player_card_types.get("tan_traveler", 0) >= 3:
                    qualified = True
                elif "production" in event_id and player_card_types.get("green_production", 0) >= 3:
                    qualified = True
                if qualified:
                    actions.append(
                        GameAction(
                            action_type=ActionType.CLAIM_EVENT,
                            player_id=player_id,
                            event_id=event_id,
                        )
                    )
        for event_id, event_data in game.special_events.items():
            if isinstance(event_data, dict) and not event_data.get("claimed_by"):
                # Special events require specific cards in city
                required = event_data.get("required_cards", [])
                if required and all(name in player_card_names for name in required):
                    actions.append(
                        GameAction(
                            action_type=ActionType.CLAIM_EVENT,
                            player_id=player_id,
                            event_id=event_id,
                        )
                    )

        return actions

    @staticmethod
    def validate_action(
        game: GameState,
        player: Player,
        action: GameAction,
        location_mgr: LocationManager,
        deck_mgr: DeckManager,
    ) -> tuple[bool, str]:
        """Check if action is legal. Returns (valid, reason)."""
        player_id = str(player.id)

        if player.has_passed:
            return False, "Player has already passed"

        if action.player_id != player_id:
            return False, "Action player_id does not match current player"

        if action.action_type == ActionType.PLACE_WORKER:
            return ActionHandler._validate_place_worker(
                game, player, action, location_mgr
            )
        elif action.action_type == ActionType.PLAY_CARD:
            return ActionHandler._validate_play_card(
                game, player, action, deck_mgr
            )
        elif action.action_type == ActionType.PREPARE_FOR_SEASON:
            if not SeasonManager.can_prepare_for_season(player):
                return False, "Cannot prepare for season (workers still available or already passed)"
            return True, ""
        elif action.action_type == ActionType.CLAIM_EVENT:
            if not action.event_id:
                return False, "No event specified"
            # Check basic events
            if action.event_id in game.basic_events:
                data = game.basic_events[action.event_id]
                if isinstance(data, dict) and data.get("claimed_by"):
                    return False, f"Event {action.event_id} already claimed"
                return True, ""
            # Check special events
            if action.event_id in game.special_events:
                data = game.special_events[action.event_id]
                if isinstance(data, dict) and data.get("claimed_by"):
                    return False, f"Event {action.event_id} already claimed"
                return True, ""
            return False, f"Unknown event: {action.event_id}"
        elif action.action_type == ActionType.RESOLVE_CHOICE:
            return ActionHandler._validate_resolve_choice(game, player, action, deck_mgr)

        return False, f"Unknown action type: {action.action_type}"

    @staticmethod
    def _validate_place_worker(
        game: GameState,
        player: Player,
        action: GameAction,
        location_mgr: LocationManager,
    ) -> tuple[bool, str]:
        available_workers = player.workers_total - player.workers_placed
        if available_workers <= 0:
            return False, "No available workers"

        if not action.location_id:
            return False, "No location specified"

        # Destination card placement
        if action.location_id.startswith("destination:"):
            card_name = action.location_id[len("destination:"):]
            has_card = any(
                c.name == card_name and c.is_open_destination for c in player.city
            )
            if not has_card:
                return False, f"No open destination card {card_name} in city"
            if action.location_id in player.workers_deployed:
                return False, f"Already visited {card_name} this season"
            return True, ""

        loc = location_mgr.get_location(action.location_id)
        if loc is None:
            return False, f"Unknown location: {action.location_id}"

        from ed_engine.engine.locations import LocationType

        if loc.location_type == LocationType.JOURNEY and player.season != "autumn":
            return False, "Journey locations only available in Autumn"

        if not loc.is_available(str(player.id)):
            return False, f"Location {action.location_id} is not available"

        return True, ""

    @staticmethod
    def _validate_play_card(
        game: GameState,
        player: Player,
        action: GameAction,
        deck_mgr: DeckManager,
    ) -> tuple[bool, str]:
        if not action.card_name:
            return False, "No card specified"

        city_size = sum(1 for c in player.city if c.occupies_city_space)

        # Find the card
        card = None
        if action.source == "hand":
            for c in player.hand:
                if c.name == action.card_name:
                    card = c
                    break
            if card is None:
                return False, f"Card {action.card_name} not in hand"
        elif action.source == "meadow":
            if action.meadow_index is None:
                return False, "No meadow index specified"
            meadow = deck_mgr.meadow
            if action.meadow_index < 0 or action.meadow_index >= len(meadow):
                return False, f"Meadow index {action.meadow_index} out of range"
            card = meadow[action.meadow_index]
            if card.name != action.card_name:
                return False, f"Meadow card at index {action.meadow_index} is {card.name}, not {action.card_name}"
        else:
            return False, f"Invalid source: {action.source}"

        # Check city space
        if card.occupies_city_space and city_size >= MAX_CITY_SIZE:
            return False, "City is full"

        # Check unique constraint
        if card.unique and any(c.name == card.name for c in player.city):
            return False, f"Already have unique card {card.name} in city"

        # Check cost
        if action.use_paired_construction:
            if card.category != CardCategory.CRITTER:
                return False, "Only critters can use paired construction"
            if not card.paired_with:
                return False, f"{card.name} has no paired construction"
            has_pair = any(c.name == card.paired_with for c in player.city)
            if not has_pair:
                return False, f"No {card.paired_with} in city for free pairing"
        else:
            if not player.resources.can_afford(card.cost):
                return False, f"Cannot afford {card.name}"

        return True, ""

    @staticmethod
    def execute_action(
        game: GameState,
        player: Player,
        action: GameAction,
        location_mgr: LocationManager,
        deck_mgr: DeckManager,
    ) -> list[str]:
        """Execute the action. Returns list of event descriptions."""
        if action.action_type == ActionType.PLACE_WORKER:
            return ActionHandler._place_worker(game, player, action, location_mgr, deck_mgr)
        elif action.action_type == ActionType.PLAY_CARD:
            return ActionHandler._play_card(game, player, action, deck_mgr, location_mgr)
        elif action.action_type == ActionType.PREPARE_FOR_SEASON:
            return SeasonManager.prepare_for_season(
                game, player, location_mgr, deck_mgr
            )
        elif action.action_type == ActionType.CLAIM_EVENT:
            return ActionHandler._claim_event(game, player, action)
        elif action.action_type == ActionType.RESOLVE_CHOICE:
            return ActionHandler._resolve_choice(game, player, action, deck_mgr, location_mgr)
        return []

    @staticmethod
    def _place_worker(
        game: GameState,
        player: Player,
        action: GameAction,
        location_mgr: LocationManager,
        deck_mgr: DeckManager | None = None,
    ) -> list[str]:
        """Place a worker on a location."""
        player_id = str(player.id)

        # Destination card placement
        if action.location_id and action.location_id.startswith("destination:"):
            card_name = action.location_id[len("destination:"):]
            player.workers_placed += 1
            player.workers_deployed.append(action.location_id)
            # Activate destination card
            ctx = {"deck_mgr": deck_mgr, "game": game} if deck_mgr else None
            for card in player.city:
                if card.name == card_name:
                    card.on_worker_placed(game, player, player, ctx=ctx)
                    break
            return [f"{player.name} placed a worker on destination {card_name}"]

        location_mgr.place_worker(action.location_id, player_id)
        player.workers_placed += 1
        player.workers_deployed.append(action.location_id)

        # Activate the location (grants resources/cards)
        loc = location_mgr.get_location(action.location_id)
        if loc is not None:
            loc.on_activate(game, player, deck_mgr=deck_mgr)

        return [f"{player.name} placed a worker at {action.location_id}"]

    @staticmethod
    def _play_card(
        game: GameState,
        player: Player,
        action: GameAction,
        deck_mgr: DeckManager,
        location_mgr: LocationManager | None = None,
    ) -> list[str]:
        """Play a card from hand or meadow."""
        events: list[str] = []

        # Get the card
        card = None
        if action.source == "hand":
            for i, c in enumerate(player.hand):
                if c.name == action.card_name:
                    card = player.hand.pop(i)
                    break
        elif action.source == "meadow":
            card = deck_mgr.draw_from_meadow(action.meadow_index)

        if card is None:
            return [f"ERROR: Could not find card {action.card_name}"]

        # Pay cost (unless using paired construction)
        if action.use_paired_construction:
            events.append(
                f"{player.name} played {card.name} free via {card.paired_with}"
            )
        else:
            player.resources = player.resources.spend(card.cost)
            events.append(f"{player.name} played {card.name}")

        # Add to city
        player.city.append(card)

        # Trigger on_play
        ctx = {"deck_mgr": deck_mgr, "game": game, "location_mgr": location_mgr}
        card.on_play(game, player, ctx=ctx)

        # Trigger blue governance cards in city
        for city_card in player.city:
            if (
                city_card.card_type == CardType.BLUE_GOVERNANCE
                and city_card is not card
            ):
                city_card.on_card_played(game, player, card, ctx=ctx)

        return events

    @staticmethod
    def _claim_event(
        game: GameState,
        player: Player,
        action: GameAction,
    ) -> list[str]:
        """Claim a basic or special event."""
        event_id = action.event_id
        points = 0
        event_name = event_id

        if event_id in game.basic_events:
            event_data = game.basic_events[event_id]
            if isinstance(event_data, dict):
                points = event_data.get("points", 3)
                event_name = event_data.get("name", event_id)
            game.basic_events[event_id] = {
                **event_data,
                "claimed_by": str(player.id),
            }
        elif event_id in game.special_events:
            event_data = game.special_events[event_id]
            if isinstance(event_data, dict):
                points = event_data.get("points", 3)
                event_name = event_data.get("name", event_id)
            game.special_events[event_id] = {
                **event_data,
                "claimed_by": str(player.id),
            }

        # Track claimed event for tiebreaker
        player.claimed_events.append(event_id)

        return [f"{player.name} claimed {event_name} (+{points} VP)"]

    @staticmethod
    def _get_pending_choice_actions(
        game: GameState,
        player: Player,
        deck_mgr: DeckManager,
    ) -> list[GameAction]:
        """Return resolve_choice actions for the current pending choice."""
        pc = game.pending_choice
        if not pc:
            return []
        player_id = str(player.id)
        actions: list[GameAction] = []
        options = pc.get("options")
        if options:
            # Generic options-based choice
            for idx in range(len(options)):
                actions.append(
                    GameAction(
                        action_type=ActionType.RESOLVE_CHOICE,
                        player_id=player_id,
                        choice_index=idx,
                    )
                )
        else:
            # Legacy meadow-index choice (Undertaker)
            meadow = deck_mgr.meadow
            for idx in range(len(meadow)):
                actions.append(
                    GameAction(
                        action_type=ActionType.RESOLVE_CHOICE,
                        player_id=player_id,
                        meadow_index=idx,
                        card_name=meadow[idx].name,
                        choice_index=idx,
                    )
                )
        return actions

    @staticmethod
    def _validate_resolve_choice(
        game: GameState,
        player: Player,
        action: GameAction,
        deck_mgr: DeckManager,
    ) -> tuple[bool, str]:
        pc = game.pending_choice
        if not pc:
            return False, "No pending choice to resolve"
        if pc.get("player_id") != str(player.id):
            return False, "Pending choice belongs to another player"

        options = pc.get("options")
        if options:
            if action.choice_index is None:
                return False, "No choice_index specified"
            if action.choice_index < 0 or action.choice_index >= len(options):
                return False, f"choice_index {action.choice_index} out of range (0-{len(options)-1})"
            return True, ""

        # Legacy meadow-index validation (Undertaker)
        idx = action.choice_index if action.choice_index is not None else action.meadow_index
        if idx is None:
            return False, "No choice_index or meadow_index specified"
        meadow = deck_mgr.meadow
        if idx < 0 or idx >= len(meadow):
            return False, f"Meadow index {idx} out of range"
        return True, ""

    @staticmethod
    def _resolve_choice(
        game: GameState,
        player: Player,
        action: GameAction,
        deck_mgr: DeckManager,
        location_mgr: LocationManager | None = None,
    ) -> list[str]:
        """Resolve a pending choice — dispatch to card's resolve_choice if options-based."""
        pc = game.pending_choice
        if not pc:
            return ["ERROR: No pending choice"]

        options = pc.get("options")
        if options:
            # Generic options-based: delegate to the card
            idx = action.choice_index
            if idx is None or idx < 0 or idx >= len(options):
                return ["ERROR: Invalid choice_index"]
            option = options[idx]

            # Forest_08: copy a basic location (not a card — handle directly)
            if pc.get("choice_type") == "select_basic_location":
                location_id = option["value"]
                if location_mgr:
                    loc = location_mgr.get_location(location_id)
                    if loc:
                        loc.on_activate(game, player, deck_mgr=deck_mgr)
                game.pending_choice = None
                return [f"{player.name} copied {option['label']} from forest location"]

            card_name = pc.get("card")
            from ed_engine.cards import get_card_definition
            card = get_card_definition(card_name)
            ctx = {"deck_mgr": deck_mgr, "game": game, "location_mgr": location_mgr}
            events = card.resolve_choice(game, player, idx, option, pc, ctx=ctx)

            # After card resolves, check production queue
            if game.pending_choice is None:
                queue = pc.get("context", {}).get("production_queue", [])
                if queue:
                    _continue_production(game, player, queue, deck_mgr)

            return events

        # Legacy Undertaker meadow-index flow
        events: list[str] = []
        step = pc.get("step")
        meadow_idx = action.choice_index if action.choice_index is not None else action.meadow_index

        if step == "discard":
            card = deck_mgr.draw_from_meadow(meadow_idx)
            deck_mgr.discard([card])
            remaining = pc.get("discards_remaining", 1) - 1
            events.append(f"{player.name} discarded {card.name} from meadow ({remaining} remaining)")

            if remaining > 0 and len(deck_mgr.meadow) > 0:
                game.pending_choice = {
                    **pc,
                    "discards_remaining": remaining,
                    "prompt": f"Select a meadow card to discard ({remaining} remaining)",
                }
            else:
                if len(deck_mgr.meadow) > 0:
                    game.pending_choice = {
                        **pc,
                        "step": "draw",
                        "prompt": "Select a meadow card to add to your hand",
                    }
                else:
                    game.pending_choice = None

        elif step == "draw":
            card = deck_mgr.draw_from_meadow(meadow_idx)
            player.hand.append(card)
            events.append(f"{player.name} drew {card.name} from meadow")
            game.pending_choice = None

        return events


def _continue_production(
    game: GameState,
    player: Player,
    queue: list[str],
    deck_mgr: DeckManager,
) -> None:
    """Resume production for remaining green cards after a choice is resolved."""
    from ed_engine.cards import get_card_definition
    ctx = {"deck_mgr": deck_mgr, "game": game}
    for i, card_name in enumerate(queue):
        # Find this card instance in player's city
        card_instance = None
        for c in player.city:
            if c.name == card_name and c.card_type == CardType.GREEN_PRODUCTION:
                card_instance = c
                break
        if card_instance is None:
            continue
        card_instance.on_production(game, player, ctx=ctx)
        if game.pending_choice is not None:
            remaining = queue[i + 1:]
            if remaining:
                game.pending_choice.setdefault("context", {})
                game.pending_choice["context"]["production_queue"] = remaining
            break
