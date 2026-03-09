from ed_engine.models.game import GameState


class ScoringEngine:
    def calculate_final_scores(self, game: GameState) -> dict[str, int]:
        """Return a mapping of player id to final score."""
        raise NotImplementedError
