from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ed_engine.models.card import Card
from ed_engine.models.location import (
    Location,
    create_basic_locations,
    create_forest_locations,
    create_haven_location,
)
from ed_engine.models.player import Player
from ed_engine.models.resources import SupplyPool


class GameState(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    players: list[Player] = Field(default_factory=list)
    supply: SupplyPool = Field(default_factory=SupplyPool)
    deck: list[Card] = Field(default_factory=list)
    meadow: list[Card] = Field(default_factory=list, max_length=8)
    discard: list[Card] = Field(default_factory=list)
    current_player_idx: int = 0
    turn_number: int = 1
    basic_events: dict[str, Any] = Field(default_factory=dict)
    special_events: dict[str, Any] = Field(default_factory=dict)
    board_locations: list[Location] = Field(default_factory=list)
    game_over: bool = False

    @staticmethod
    def create_board(player_count: int) -> list[Location]:
        """Initialize all board locations for a game."""
        locations: list[Location] = []
        locations.extend(create_basic_locations())
        locations.extend(create_forest_locations(player_count))
        locations.append(create_haven_location())
        return locations

    def find_location(self, location_id: str) -> Location | None:
        for loc in self.board_locations:
            if loc.id == location_id:
                return loc
        return None

    def update_location(self, updated: Location) -> "GameState":
        """Return a new GameState with the given location replaced."""
        new_locations = [
            updated if loc.id == updated.id else loc for loc in self.board_locations
        ]
        return self.model_copy(update={"board_locations": new_locations})

    def find_player(self, player_id: UUID) -> Player | None:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def update_player(self, updated: Player) -> "GameState":
        """Return a new GameState with the given player replaced."""
        new_players = [
            updated if p.id == updated.id else p for p in self.players
        ]
        return self.model_copy(update={"players": new_players})

    def recall_workers(self, player_id: UUID) -> "GameState":
        """Remove all of a player's workers from all locations and reset their count."""
        game = self
        for loc in game.board_locations:
            if player_id in loc.occupants:
                game = game.update_location(loc.remove_player(player_id))

        player = game.find_player(player_id)
        if player:
            game = game.update_player(
                player.model_copy(update={"workers_placed": 0})
            )
        return game
