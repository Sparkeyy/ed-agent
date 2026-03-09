from __future__ import annotations

from typing import TYPE_CHECKING

from ed_engine.models.enums import CardType, Season

if TYPE_CHECKING:
    from ed_engine.engine.deck import DeckManager
    from ed_engine.engine.locations import LocationManager
    from ed_engine.models.game import GameState
    from ed_engine.models.player import Player


# Season order for progression
_SEASON_ORDER = [Season.WINTER, Season.SPRING, Season.SUMMER, Season.AUTUMN]

# Workers gained when entering a new season
_SEASON_WORKERS = {
    Season.SPRING: 1,
    Season.SUMMER: 1,
    Season.AUTUMN: 2,
}


class SeasonManager:
    """Manages per-player season progression."""

    @staticmethod
    def get_next_season(current: Season) -> Season | None:
        """WINTER -> SPRING -> SUMMER -> AUTUMN -> None."""
        idx = _SEASON_ORDER.index(current)
        if idx + 1 < len(_SEASON_ORDER):
            return _SEASON_ORDER[idx + 1]
        return None

    @staticmethod
    def can_prepare_for_season(player: Player) -> bool:
        """True if the player has deployed all workers AND hasn't completed autumn."""
        if player.has_passed:
            return False
        next_season = SeasonManager.get_next_season(player.season)
        if next_season is None:
            # Already in Autumn — preparing means finishing the game
            return player.workers_placed >= player.workers_total
        # Must have all workers deployed (none available)
        return player.workers_placed >= player.workers_total

    @staticmethod
    def prepare_for_season(
        game: GameState,
        player: Player,
        location_mgr: LocationManager,
        deck_mgr: DeckManager,
    ) -> list[str]:
        """Execute season transition. Returns list of event descriptions.

        1. Recall all workers
        2. Advance to next season
        3. Gain new workers
        4. Trigger season bonuses (green production in spring/autumn, meadow draw in summer)
        """
        events: list[str] = []
        player_id = str(player.id)

        next_season = SeasonManager.get_next_season(player.season)

        if next_season is None:
            # Player is in Autumn and all workers deployed — they pass
            # Recall workers
            location_mgr.recall_all_workers(player_id)
            player.workers_placed = 0
            player.workers_deployed.clear()
            player.has_passed = True
            events.append(f"{player.name} has finished the game (completed Autumn)")
            return events

        # 1. Recall all workers
        recalled = location_mgr.recall_all_workers(player_id)
        player.workers_placed = 0
        player.workers_deployed.clear()
        events.append(
            f"{player.name} recalled workers from {len(recalled)} locations"
        )

        # 2. Advance season
        old_season = player.season
        player.season = next_season
        events.append(f"{player.name} advanced from {old_season.value} to {next_season.value}")

        # 3. Gain new workers
        new_workers = _SEASON_WORKERS.get(next_season, 0)
        if new_workers > 0:
            player.workers_total += new_workers
            events.append(f"{player.name} gained {new_workers} worker(s) (total: {player.workers_total})")

        # 4. Trigger season bonuses
        if next_season in (Season.SPRING, Season.AUTUMN):
            prod_events = SeasonManager.trigger_production(game, player, ctx={"deck_mgr": deck_mgr, "game": game})
            events.extend(prod_events)
        elif next_season == Season.SUMMER:
            # Draw up to 2 Meadow cards
            drawn = 0
            for _ in range(2):
                if deck_mgr.meadow:
                    # Draw from the first available meadow slot
                    card = deck_mgr.draw_from_meadow(0)
                    player.hand.append(card)
                    drawn += 1
            if drawn > 0:
                events.append(f"{player.name} drew {drawn} card(s) from the Meadow")

        return events

    @staticmethod
    def trigger_production(game: GameState, player: Player, *, ctx: dict | None = None) -> list[str]:
        """Activate all Green Production cards in player's city."""
        events: list[str] = []
        for card in player.city:
            if card.card_type == CardType.GREEN_PRODUCTION:
                card.on_production(game, player, ctx=ctx)
                events.append(f"  Production: {card.name}")
        return events
