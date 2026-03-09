from ed_engine.models.card import Card
from ed_engine.models.game import GameState
from ed_engine.models.player import Player


class ActionHandler:
    def place_worker(self, game: GameState, player: Player, location_id: str) -> GameState:
        raise NotImplementedError

    def play_card(self, game: GameState, player: Player, card: Card) -> GameState:
        raise NotImplementedError

    def prepare_for_season(self, game: GameState, player: Player) -> GameState:
        raise NotImplementedError

    def validate_action(self, game: GameState, player: Player, action: dict) -> bool:
        raise NotImplementedError
