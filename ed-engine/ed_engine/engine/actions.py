from ed_engine.models.card import Card, RedDestinationCard
from ed_engine.models.enums import CardType, LocationType
from ed_engine.models.game import GameState
from ed_engine.models.location import Location
from ed_engine.models.player import Player


class ActionHandler:
    def place_worker(
        self,
        game: GameState,
        player: Player,
        location_id: str,
    ) -> GameState:
        """Place a worker at a board location or destination card in a player's city.

        Validates:
        - Player has available workers
        - Location exists (board or destination card)
        - Location can accept the worker (exclusive vs shared)

        Returns updated GameState with worker placed and rewards granted.
        """
        if player.workers_placed >= player.workers_total:
            raise ValueError("No available workers to place")

        # Check board locations first
        location = game.find_location(location_id)
        if location is not None:
            return self._place_on_board(game, player, location)

        # Check destination cards in player's city
        dest_card = self._find_destination_card(player, location_id)
        if dest_card is not None:
            return self._place_on_destination(game, player, dest_card)

        raise ValueError(f"Location not found: {location_id}")

    def _place_on_board(
        self,
        game: GameState,
        player: Player,
        location: Location,
    ) -> GameState:
        if not location.can_place(player.id):
            raise ValueError(f"Cannot place worker at {location.name}: location is occupied")

        updated_location = location.place(player.id)
        game = game.update_location(updated_location)

        # Grant resource rewards
        updated_player = player.model_copy(
            update={
                "workers_placed": player.workers_placed + 1,
                "resources": player.resources.gain(location.rewards),
            }
        )

        # Draw cards if location grants them
        if location.cards_drawn > 0:
            cards_to_draw = min(location.cards_drawn, len(game.deck))
            drawn = game.deck[:cards_to_draw]
            remaining_deck = game.deck[cards_to_draw:]
            updated_player = updated_player.model_copy(
                update={"hand": [*updated_player.hand, *drawn]}
            )
            game = game.model_copy(update={"deck": remaining_deck})

        game = game.update_player(updated_player)
        return game

    def _find_destination_card(self, player: Player, card_id: str) -> RedDestinationCard | None:
        for card in player.city:
            if card.id == card_id and isinstance(card, RedDestinationCard):
                return card
        return None

    def _place_on_destination(
        self,
        game: GameState,
        player: Player,
        card: RedDestinationCard,
    ) -> GameState:
        """Place a worker on a RED destination card in the player's city.

        Destination cards are exclusive — only one worker per card.
        Uses the card's built-in place_worker/recall_worker methods.
        """
        card.place_worker(str(player.id))

        updated_player = player.model_copy(
            update={"workers_placed": player.workers_placed + 1}
        )
        game = game.update_player(updated_player)

        # Trigger the destination card's effect
        card.on_trigger(player=updated_player)

        return game

    def play_card(self, game: GameState, player: Player, card: Card) -> GameState:
        raise NotImplementedError

    def prepare_for_season(self, game: GameState, player: Player) -> GameState:
        raise NotImplementedError

    def validate_action(self, game: GameState, player: Player, action: dict) -> bool:
        raise NotImplementedError
