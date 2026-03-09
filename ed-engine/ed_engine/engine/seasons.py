from ed_engine.models.card import RedDestinationCard
from ed_engine.models.enums import Season
from ed_engine.models.game import GameState
from ed_engine.models.player import Player

SEASON_ORDER = [Season.WINTER, Season.SPRING, Season.SUMMER, Season.AUTUMN]

WORKERS_BY_SEASON: dict[Season, int] = {
    Season.WINTER: 2,
    Season.SPRING: 3,
    Season.SUMMER: 4,
    Season.AUTUMN: 6,
}


class SeasonManager:
    def advance_season(self, game: GameState, player: Player) -> GameState:
        """Advance the player to the next season, recalling workers and gaining bonuses.

        Per Everdell rules, when a player has placed all workers and has no other
        actions, they prepare for the next season:
        1. All workers return from board locations and destination cards
        2. Player gains additional workers for the new season
        3. GREEN production cards in city activate
        """
        current_idx = SEASON_ORDER.index(player.season)
        if current_idx >= len(SEASON_ORDER) - 1:
            raise ValueError("Cannot advance past autumn")

        next_season = SEASON_ORDER[current_idx + 1]

        # Recall all workers from board locations
        game = game.recall_workers(player.id)

        # Recall workers from destination cards in city
        player = game.find_player(player.id)
        assert player is not None
        for card in player.city:
            if isinstance(card, RedDestinationCard) and card.occupied_by is not None:
                card.recall_worker()

        # Update player season and worker count
        new_total = WORKERS_BY_SEASON[next_season]
        updated_player = player.model_copy(
            update={
                "season": next_season,
                "workers_total": new_total,
                "workers_placed": 0,
            }
        )
        game = game.update_player(updated_player)

        return game
