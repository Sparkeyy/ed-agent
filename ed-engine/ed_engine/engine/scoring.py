"""Scoring engine for Everdell end-of-game tallying."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from ed_engine.models.enums import CardType

if TYPE_CHECKING:
    from ed_engine.models.game import GameState
    from ed_engine.models.player import Player


class ScoreBreakdown(BaseModel):
    base_card_points: int = 0
    bonus_card_points: int = 0
    event_points: int = 0
    journey_points: int = 0
    point_tokens: int = 0
    total: int = 0


class ScoringEngine:
    @staticmethod
    def calculate_final_scores(game: GameState) -> dict[str, ScoreBreakdown]:
        """Calculate final scores for all players.

        Returns a mapping of player name to ScoreBreakdown. Also sets
        player.score on each player for convenience.
        """
        breakdowns: dict[str, ScoreBreakdown] = {}
        for player in game.players:
            bd = ScoringEngine.score_player(game, player)
            player.score = bd.total
            breakdowns[player.name] = bd
        return breakdowns

    @staticmethod
    def score_player(game: GameState, player: Player) -> ScoreBreakdown:
        """Full score breakdown for one player.

        - base_card_points: sum of base_points for all cards in city
        - bonus_card_points: sum of on_score() for Purple Prosperity cards
        - event_points: sum of achieved event point values
        - journey_points: points from workers on journey locations
        - point_tokens: accumulated point tokens during game
        """
        # Base card points
        base = sum(c.base_points for c in player.city)

        # Bonus from Purple Prosperity on_score() hooks
        bonus = sum(
            c.on_score(game, player)
            for c in player.city
            if c.card_type == CardType.PURPLE_PROSPERITY
        )

        # Event points — look up from game state dicts
        event_pts = 0
        player_id = str(player.id)
        for eid, edata in game.basic_events.items():
            if isinstance(edata, dict) and edata.get("claimed_by") == player_id:
                event_pts += edata.get("points", 0)
            elif hasattr(edata, "claimed_by") and edata.claimed_by == player_id:
                event_pts += getattr(edata, "points", 0)
        for eid, edata in game.special_events.items():
            if isinstance(edata, dict) and edata.get("claimed_by") == player_id:
                event_pts += edata.get("points", 0)
            elif hasattr(edata, "claimed_by") and edata.claimed_by == player_id:
                event_pts += getattr(edata, "points", 0)

        # Journey points — count from workers_deployed
        journey_pts = 0
        for loc_id in player.workers_deployed:
            if loc_id.startswith("journey_"):
                # Extract point value from location id (e.g. journey_3pt -> 3)
                try:
                    val = int(loc_id.split("_")[1].replace("pt", ""))
                    journey_pts += val
                except (IndexError, ValueError):
                    pass

        # Point tokens accumulated during game
        pt = player.point_tokens

        total = base + bonus + event_pts + journey_pts + pt

        return ScoreBreakdown(
            base_card_points=base,
            bonus_card_points=bonus,
            event_points=event_pts,
            journey_points=journey_pts,
            point_tokens=pt,
            total=total,
        )

    @staticmethod
    def determine_winner(game: GameState) -> list[Player]:
        """Return the winner(s) after tiebreaking.

        Tiebreaker rules (from rulebook):
        1. Highest total score
        2. Most Events achieved
        3. Most leftover resources
        Returns a list (length > 1 only if still tied after all breakers).
        """
        breakdowns = ScoringEngine.calculate_final_scores(game)
        players = list(game.players)

        def sort_key(p: Player) -> tuple[int, int, int]:
            bd = breakdowns[p.name]
            num_events = len(p.claimed_events)
            leftover = p.resources.total()
            return (bd.total, num_events, leftover)

        players.sort(key=sort_key, reverse=True)

        # Collect all tied at the top
        best = sort_key(players[0])
        winners = [p for p in players if sort_key(p) == best]
        return winners
