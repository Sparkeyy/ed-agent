"""Pydantic request/response models for the Everdell API."""

from typing import Any

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    player_count: int = Field(ge=2, le=4)
    creator_name: str = Field(min_length=1, max_length=50)


class CreateGameResponse(BaseModel):
    game_id: str
    player_token: str
    player_id: str


class JoinGameRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=50)


class JoinGameResponse(BaseModel):
    player_token: str
    player_id: str


class PerformActionRequest(BaseModel):
    player_token: str
    action_type: str
    location_id: str | None = None
    card_name: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ValidAction(BaseModel):
    action_type: str
    description: str = ""
    params: dict[str, Any] = Field(default_factory=dict)


class GameStateResponse(BaseModel):
    game_id: str
    state: dict[str, Any]
    valid_actions: list[ValidAction] = Field(default_factory=list)
    current_player_id: str | None = None
    game_over: bool = False


class PerformActionResponse(BaseModel):
    status: str = "ok"
    game: GameStateResponse


class AddAiRequest(BaseModel):
    difficulty: str = Field(default="journeyman", pattern="^(apprentice|journeyman|master)$")
    name: str = Field(default="Rugwort", min_length=1, max_length=50)


class AddAiResponse(BaseModel):
    player_id: str
    name: str
    difficulty: str
