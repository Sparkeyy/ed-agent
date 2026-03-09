from ed_engine.models.game import GameState
from ed_engine.models.player import Player


class SeasonManager:
    def advance_season(self, game: GameState, player: Player) -> GameState:
        """Advance the player to the next season, recalling workers and gaining bonuses."""
        raise NotImplementedError
