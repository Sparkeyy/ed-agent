"""Tests for the scoring engine."""

from uuid import uuid4

import pytest

from ed_engine.cards.constructions import (
    Castle,
    Farm,
    Mine,
    School,
    Theater,
)
from ed_engine.cards.critters import (
    Architect,
    Harvester,
    King,
    Teacher,
    Gatherer,
)
from ed_engine.engine.scoring import ScoreBreakdown, ScoringEngine
from ed_engine.models.enums import CardCategory, CardType, Season
from ed_engine.models.game import GameState
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank


def _make_player(name: str = "Alice", **kwargs) -> Player:
    return Player(id=uuid4(), name=name, season=Season.AUTUMN, **kwargs)


def _make_game(players: list[Player] | None = None) -> GameState:
    if players is None:
        players = [_make_player()]
    return GameState(players=players)


class TestBasicCardPoints:
    def test_empty_city_scores_zero(self):
        p = _make_player()
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.base_card_points == 0
        assert bd.total == 0

    def test_single_card_base_points(self):
        p = _make_player()
        p.city = [Farm()]  # 1 base point
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.base_card_points == 1
        assert bd.total == 1

    def test_multiple_cards_sum(self):
        p = _make_player()
        p.city = [Farm(), Mine(), Castle()]  # 1 + 2 + 4 = 7
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.base_card_points == 7

    def test_negative_base_points(self):
        """Fool has -2 base points."""
        from ed_engine.cards.critters import Fool

        p = _make_player()
        p.city = [Farm(), Fool()]  # 1 + (-2) = -1
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.base_card_points == -1


class TestPurpleProsperityBonusScoring:
    def test_castle_bonus(self):
        """Castle: +1 pt per common Construction."""
        p = _make_player()
        p.city = [Castle(), Farm(), Farm(), Mine()]  # 2 common constructions (Farm, Mine are not unique... Farm is common, Mine is common)
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        # Castle on_score counts common constructions: Farm x2 + Mine = 3
        assert bd.bonus_card_points == 3

    def test_theater_bonus(self):
        """Theater: +1 pt per unique Critter."""
        p = _make_player()
        p.city = [Theater(), King(), Architect()]  # 2 unique critters
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        # Theater gives +2, King gives +0 (no events), Architect gives resin+pebble bonus
        # bonus = Theater(2) + King(0) + Architect(resin+pebble=0)
        assert bd.bonus_card_points >= 2  # Theater contributes 2

    def test_school_bonus(self):
        """School: +1 pt per common Critter."""
        p = _make_player()
        p.city = [School(), Harvester(), Harvester(), Teacher()]
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        # Harvester x2 + Teacher = 3 common critters
        assert bd.bonus_card_points == 3

    def test_gatherer_bonus_with_harvester(self):
        """Gatherer: +3 pt if Harvester in city."""
        p = _make_player()
        p.city = [Gatherer(), Harvester()]
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.bonus_card_points == 3

    def test_gatherer_bonus_without_harvester(self):
        """Gatherer: 0 extra if no Harvester."""
        p = _make_player()
        p.city = [Gatherer()]
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.bonus_card_points == 0

    def test_architect_bonus(self):
        """Architect: +1 per leftover resin+pebble, max 6."""
        p = _make_player(resources=ResourceBank(resin=3, pebble=4))
        p.city = [Architect()]
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.bonus_card_points == 6  # capped at 6


class TestEventPointsInScore:
    def test_basic_event_points(self):
        p = _make_player()
        pid = str(p.id)
        game = _make_game([p])
        game.basic_events = {
            "basic_governance": {"name": "Governance Mastery", "points": 3, "claimed_by": pid},
        }
        bd = ScoringEngine.score_player(game, p)
        assert bd.event_points == 3

    def test_special_event_points(self):
        p = _make_player()
        pid = str(p.id)
        game = _make_game([p])
        game.special_events = {
            "se_brilliant_wedding": {"name": "A Brilliant Wedding", "points": 3, "claimed_by": pid},
        }
        bd = ScoringEngine.score_player(game, p)
        assert bd.event_points == 3

    def test_unclaimed_events_not_counted(self):
        p = _make_player()
        game = _make_game([p])
        game.basic_events = {
            "basic_governance": {"name": "Governance Mastery", "points": 3, "claimed_by": None},
        }
        bd = ScoringEngine.score_player(game, p)
        assert bd.event_points == 0

    def test_other_player_events_not_counted(self):
        p1 = _make_player("Alice")
        p2 = _make_player("Bob")
        game = _make_game([p1, p2])
        game.basic_events = {
            "basic_governance": {"name": "Governance Mastery", "points": 3, "claimed_by": str(p2.id)},
        }
        bd = ScoringEngine.score_player(game, p1)
        assert bd.event_points == 0


class TestJourneyPoints:
    def test_journey_points_from_deployed_workers(self):
        p = _make_player()
        p.workers_deployed = ["journey_3pt", "journey_5pt"]
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.journey_points == 8

    def test_no_journey_workers(self):
        p = _make_player()
        p.workers_deployed = ["basic_3twigs"]
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.journey_points == 0


class TestPointTokens:
    def test_point_tokens_counted(self):
        p = _make_player()
        p.point_tokens = 7
        game = _make_game([p])
        bd = ScoringEngine.score_player(game, p)
        assert bd.point_tokens == 7
        assert bd.total == 7


class TestTotalScore:
    def test_total_is_sum_of_all(self):
        p = _make_player(resources=ResourceBank(resin=2, pebble=2))
        pid = str(p.id)
        p.city = [Farm(), Castle(), Gatherer(), Harvester()]
        p.point_tokens = 5
        p.workers_deployed = ["journey_3pt"]
        game = _make_game([p])
        game.basic_events = {
            "basic_production": {"name": "A Year of Plenty", "points": 3, "claimed_by": pid},
        }

        bd = ScoringEngine.score_player(game, p)
        expected_base = 1 + 4 + 2 + 2  # Farm(1) + Castle(4) + Gatherer(2) + Harvester(2)
        expected_bonus = 1 + 3  # Castle(Farm is common construction=1) + Gatherer(has Harvester=3)
        expected_events = 3
        expected_journey = 3
        expected_tokens = 5
        expected_total = expected_base + expected_bonus + expected_events + expected_journey + expected_tokens
        assert bd.total == expected_total


class TestTiebreaker:
    def test_highest_score_wins(self):
        p1 = _make_player("Alice")
        p1.city = [Castle()]  # 4 pts
        p2 = _make_player("Bob")
        p2.city = [Farm()]   # 1 pt
        game = _make_game([p1, p2])
        winners = ScoringEngine.determine_winner(game)
        assert len(winners) == 1
        assert winners[0].name == "Alice"

    def test_tiebreak_by_events(self):
        p1 = _make_player("Alice")
        p1.city = [Farm()]
        p1.claimed_events = ["basic_governance"]
        p2 = _make_player("Bob")
        p2.city = [Farm()]
        p2.claimed_events = []
        game = _make_game([p1, p2])
        winners = ScoringEngine.determine_winner(game)
        assert len(winners) == 1
        assert winners[0].name == "Alice"

    def test_tiebreak_by_resources(self):
        p1 = _make_player("Alice", resources=ResourceBank(twig=5))
        p1.city = [Farm()]
        p2 = _make_player("Bob", resources=ResourceBank(twig=1))
        p2.city = [Farm()]
        game = _make_game([p1, p2])
        winners = ScoringEngine.determine_winner(game)
        assert len(winners) == 1
        assert winners[0].name == "Alice"

    def test_true_tie(self):
        p1 = _make_player("Alice")
        p1.city = [Farm()]
        p2 = _make_player("Bob")
        p2.city = [Farm()]
        game = _make_game([p1, p2])
        winners = ScoringEngine.determine_winner(game)
        assert len(winners) == 2

    def test_calculate_final_scores_sets_player_score(self):
        p = _make_player()
        p.city = [Farm(), Mine()]  # 1 + 2 = 3
        game = _make_game([p])
        ScoringEngine.calculate_final_scores(game)
        assert p.score == 3


class TestKingScoring:
    def test_king_scores_events(self):
        p = _make_player()
        pid = str(p.id)
        p.city = [King()]
        game = _make_game([p])
        game.basic_events = {
            "basic_governance": {"name": "Governance Mastery", "points": 3, "claimed_by": pid},
            "basic_production": {"name": "A Year of Plenty", "points": 3, "claimed_by": pid},
        }
        game.special_events = {
            "se_brilliant_wedding": {"name": "A Brilliant Wedding", "points": 3, "claimed_by": pid},
        }
        bd = ScoringEngine.score_player(game, p)
        # King bonus: 2 basic * 1 + 1 special * 2 = 4
        assert bd.bonus_card_points == 4
