from __future__ import annotations

import random
from typing import Any
from uuid import UUID, uuid4

from ed_engine.cards import build_deck
from ed_engine.engine.actions import ActionHandler, ActionType, GameAction
from ed_engine.engine.deck import DeckManager
from ed_engine.engine.events import EventManager
from ed_engine.engine.locations import LocationManager
from ed_engine.engine.seasons import SeasonManager
from ed_engine.models.enums import Season
from ed_engine.models.game import GameState
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank


# Starting hand sizes by player order (1st player gets fewer cards)
_STARTING_HAND_SIZES = {
    1: 5,  # 1st player
    2: 6,  # 2nd player
    3: 7,  # 3rd player
    4: 8,  # 4th player
}


class GameManager:
    """Orchestrates a complete Everdell game."""

    def __init__(self, player_names: list[str], seed: int | None = None) -> None:
        """Create a new game with 1-4 players."""
        if not (1 <= len(player_names) <= 4):
            raise ValueError(f"Everdell supports 1-4 players, got {len(player_names)}")

        self._seed = seed
        self._rng = random.Random(seed)

        # Create players
        players = []
        for i, name in enumerate(player_names):
            players.append(
                Player(
                    id=uuid4(),
                    name=name,
                    season=Season.WINTER,
                    workers_total=2,
                    workers_placed=0,
                )
            )

        # Initialize deck and meadow
        all_cards = build_deck()
        self._deck_mgr = DeckManager(all_cards, seed=seed)

        # Initialize locations
        self._location_mgr = LocationManager(len(player_names), seed=seed)

        # Initialize events
        self._event_mgr = EventManager(seed=seed)

        # Debug mode: give "debug" player unlimited resources
        for player in players:
            if player.name.lower() == "debug":
                player.resources = ResourceBank(twig=999, resin=999, pebble=999, berry=999)

        # Deal starting hands (player order determines hand size)
        for i, player in enumerate(players):
            hand_size = _STARTING_HAND_SIZES.get(i + 1, 5)
            player.hand = self._deck_mgr.draw(hand_size)

        # Build game state with events
        basic_events, special_events = self._event_mgr.to_game_state_dicts()
        self._game = GameState(
            players=players,
            meadow=list(self._deck_mgr.meadow),
            current_player_idx=0,
            turn_number=1,
            seed=seed,
            basic_events=basic_events,
            special_events=special_events,
        )

    @property
    def game(self) -> GameState:
        return self._game

    @property
    def state(self) -> GameState:
        """Alias for backward compat with API layer."""
        return self._game

    @property
    def current_player(self) -> Player:
        return self._game.players[self._game.current_player_idx]

    def get_state(self, perspective_player_id: str | None = None) -> GameState:
        """Return current game state, optionally filtered by perspective."""
        self._sync_state()
        return self._game

    def get_current_player(self) -> Player | None:
        """Return the current player, or None if no players."""
        if not self._game.players:
            return None
        idx = self._game.current_player_idx % len(self._game.players)
        return self._game.players[idx]

    def get_valid_actions(self, player_id: str | UUID | None = None) -> list[GameAction]:
        """What can this player do? Defaults to current player.

        Also supports the old dict-returning API when called with a UUID.
        """
        if player_id is None:
            player = self.current_player
        else:
            player = self._find_player(str(player_id))
            if player is None:
                return []

        return ActionHandler.get_valid_actions(
            self._game, player, self._location_mgr, self._deck_mgr
        )

    def perform_action(
        self,
        action_or_player_id: GameAction | UUID | str,
        action_type: str | None = None,
        **kwargs: Any,
    ) -> GameState | list[str]:
        """Execute action, advance turn, return updated state or events.

        Supports two calling conventions:
        1. New: perform_action(GameAction) -> list[str]
        2. Legacy: perform_action(player_id, action_type, **kwargs) -> GameState
        """
        # Detect legacy calling convention
        if action_type is not None:
            return self._perform_action_legacy(action_or_player_id, action_type, **kwargs)

        if not isinstance(action_or_player_id, GameAction):
            raise TypeError(
                "Expected GameAction or (player_id, action_type). "
                f"Got {type(action_or_player_id)}"
            )

        action = action_or_player_id
        player = self._find_player(action.player_id)
        if player is None:
            raise ValueError(f"Unknown player: {action.player_id}")

        # Validate
        valid, reason = ActionHandler.validate_action(
            self._game, player, action, self._location_mgr, self._deck_mgr
        )
        if not valid:
            raise ValueError(f"Invalid action: {reason}")

        # Execute
        events = ActionHandler.execute_action(
            self._game, player, action, self._location_mgr, self._deck_mgr
        )

        # Log action
        self._game.action_log.append(
            {
                "turn": self._game.turn_number,
                "player": player.name,
                "action_type": action.action_type,
                "details": action.model_dump(),
            }
        )

        # Sync state from managers
        self._sync_state()

        # Advance turn
        self.advance_turn()

        return events

    def _perform_action_legacy(
        self,
        player_id: UUID | str,
        action_type: str,
        **kwargs: Any,
    ) -> GameState:
        """Legacy perform_action for backward compat with API layer."""
        current = self.get_current_player()
        if current is None:
            raise ValueError("No players in game")

        pid = player_id if isinstance(player_id, UUID) else UUID(str(player_id))
        if current.id != pid:
            raise ValueError("Not your turn")
        if self._game.game_over:
            raise ValueError("Game is over")

        player_id_str = str(current.id)

        if action_type == "place_worker":
            location_id = kwargs.get("location_id")
            if not location_id:
                raise ValueError("location_id is required for place_worker")
            action = GameAction(
                action_type=ActionType.PLACE_WORKER,
                player_id=player_id_str,
                location_id=location_id,
            )
        elif action_type == "play_card":
            card_name = kwargs.get("card_name")
            if not card_name:
                raise ValueError("card_name is required for play_card")
            source = kwargs.get("source", "hand")
            meadow_index = kwargs.get("meadow_index")
            use_paired = kwargs.get("use_paired_construction", False)
            action = GameAction(
                action_type=ActionType.PLAY_CARD,
                player_id=player_id_str,
                card_name=card_name,
                source=source,
                meadow_index=meadow_index,
                use_paired_construction=use_paired,
            )
        elif action_type == "prepare_for_season":
            action = GameAction(
                action_type=ActionType.PREPARE_FOR_SEASON,
                player_id=player_id_str,
            )
        elif action_type == "claim_event":
            event_id = kwargs.get("event_id")
            if not event_id:
                raise ValueError("event_id is required for claim_event")
            action = GameAction(
                action_type=ActionType.CLAIM_EVENT,
                player_id=player_id_str,
                event_id=event_id,
            )
        else:
            raise ValueError(f"Unknown action type: {action_type}")

        # For legacy path: validate and execute directly
        player = current
        valid, reason = ActionHandler.validate_action(
            self._game, player, action, self._location_mgr, self._deck_mgr
        )
        if not valid:
            raise ValueError(reason)

        ActionHandler.execute_action(
            self._game, player, action, self._location_mgr, self._deck_mgr
        )

        self._game.action_log.append(
            {
                "turn": self._game.turn_number,
                "player": player.name,
                "action_type": action_type,
            }
        )

        self._sync_state()
        self.advance_turn()
        return self._game

    def advance_turn(self) -> None:
        """Move to next player who hasn't passed."""
        if self.is_game_over():
            self._game.game_over = True
            return

        num_players = len(self._game.players)
        for _ in range(num_players):
            self._game.current_player_idx = (
                self._game.current_player_idx + 1
            ) % num_players
            candidate = self._game.players[self._game.current_player_idx]
            if not candidate.has_passed:
                self._game.turn_number += 1
                return

        # All players passed
        self._game.game_over = True

    def is_game_over(self) -> bool:
        """True when all players have passed."""
        return all(p.has_passed for p in self._game.players)

    def calculate_scores(self) -> dict[str, int]:
        """Calculate final scores for all players."""
        scores: dict[str, int] = {}
        for player in self._game.players:
            total = 0
            for card in player.city:
                total += card.base_points
                total += card.on_score(self._game, player)
            player.score = total
            scores[player.name] = total
        return scores

    def _find_player(self, player_id: str) -> Player | None:
        for p in self._game.players:
            if str(p.id) == player_id:
                return p
        return None

    def _sync_state(self) -> None:
        """Sync game state from managers."""
        self._game.meadow = list(self._deck_mgr.meadow)
