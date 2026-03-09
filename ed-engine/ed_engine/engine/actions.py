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

        # 2. Play card actions
        city_size = sum(1 for c in player.city if c.occupies_city_space)
        has_city_space = city_size < MAX_CITY_SIZE

        if has_city_space:
            # From hand
            for card in player.hand:
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
                        # Check we haven't already used this pairing
                        # (unique construction can only pair once)
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
            return ActionHandler._place_worker(game, player, action, location_mgr)
        elif action.action_type == ActionType.PLAY_CARD:
            return ActionHandler._play_card(game, player, action, deck_mgr)
        elif action.action_type == ActionType.PREPARE_FOR_SEASON:
            return SeasonManager.prepare_for_season(
                game, player, location_mgr, deck_mgr
            )
        return []

    @staticmethod
    def _place_worker(
        game: GameState,
        player: Player,
        action: GameAction,
        location_mgr: LocationManager,
    ) -> list[str]:
        """Place a worker on a location."""
        player_id = str(player.id)
        location_mgr.place_worker(action.location_id, player_id)
        player.workers_placed += 1
        player.workers_deployed.append(action.location_id)

        # Activate the location
        loc = location_mgr.get_location(action.location_id)
        if loc is not None:
            loc.on_activate(game, player)

        return [f"{player.name} placed a worker at {action.location_id}"]

    @staticmethod
    def _play_card(
        game: GameState,
        player: Player,
        action: GameAction,
        deck_mgr: DeckManager,
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
        card.on_play(game, player)

        # Trigger blue governance cards in city
        for city_card in player.city:
            if (
                city_card.card_type == CardType.BLUE_GOVERNANCE
                and city_card is not card
            ):
                city_card.on_card_played(game, player, card)

        return events
