from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ed_engine.models.enums import LocationType, Season
from ed_engine.models.resources import ResourceBank

if TYPE_CHECKING:
    from ed_engine.engine.deck import DeckManager
    from ed_engine.models.game import GameState
    from ed_engine.models.player import Player

# Hand limit for drawing cards
HAND_LIMIT = 8


def _draw_cards_for_player(player: Any, deck_mgr: Any, count: int) -> None:
    """Draw cards from deck into player's hand, respecting hand limit."""
    space = HAND_LIMIT - len(player.hand)
    to_draw = min(count, space)
    if to_draw > 0:
        cards = deck_mgr.draw(to_draw)
        player.hand.extend(cards)


class Location(BaseModel):
    """Base location for worker placement."""

    id: str
    name: str
    location_type: LocationType
    exclusive: bool = True
    workers: list[str] = Field(default_factory=list)

    def is_available(self, player_id: str) -> bool:
        """Check if a player can place a worker here."""
        if self.exclusive:
            return len(self.workers) == 0
        # Shared locations: player can only place once
        return player_id not in self.workers

    def place_worker(self, player_id: str) -> None:
        if not self.is_available(player_id):
            raise ValueError(f"Location {self.id} not available for player {player_id}")
        self.workers.append(player_id)

    def remove_worker(self, player_id: str) -> None:
        if player_id in self.workers:
            self.workers.remove(player_id)

    def on_activate(self, game: Any, player: Any, deck_mgr: Any = None) -> None:
        """Override in subclasses to define what happens when a worker is placed."""
        pass


class BasicLocation(Location):
    """Standard board spaces with resource rewards."""

    location_type: LocationType = LocationType.BASIC

    def on_activate(self, game: Any, player: Any, deck_mgr: Any = None) -> None:
        """Grant resources/cards based on location id."""
        if self.id == "basic_3twigs":
            player.resources = player.resources.gain(ResourceBank(twig=3))
        elif self.id == "basic_2twigs_1card":
            player.resources = player.resources.gain(ResourceBank(twig=2))
            if deck_mgr:
                _draw_cards_for_player(player, deck_mgr, 1)
        elif self.id == "basic_2resin":
            player.resources = player.resources.gain(ResourceBank(resin=2))
        elif self.id == "basic_1resin_1card":
            player.resources = player.resources.gain(ResourceBank(resin=1))
            if deck_mgr:
                _draw_cards_for_player(player, deck_mgr, 1)
        elif self.id == "basic_2cards_1point":
            if deck_mgr:
                _draw_cards_for_player(player, deck_mgr, 2)
            player.point_tokens = getattr(player, 'point_tokens', 0) + 1
        elif self.id == "basic_1pebble":
            player.resources = player.resources.gain(ResourceBank(pebble=1))
        elif self.id == "basic_1berry_1card":
            player.resources = player.resources.gain(ResourceBank(berry=1))
            if deck_mgr:
                _draw_cards_for_player(player, deck_mgr, 1)
        elif self.id == "basic_1berry":
            player.resources = player.resources.gain(ResourceBank(berry=1))


class ForestLocation(Location):
    """Variable per player count. Grants resources/cards on activation."""

    location_type: LocationType = LocationType.FOREST
    exclusive: bool = True

    def on_activate(self, game: Any, player: Any, deck_mgr: Any = None) -> None:
        """Grant resources/cards based on forest location id.

        Locations verified against physical card scans 2026-03-10.
        """
        if self.id == "forest_01":  # 1 twig, 1 resin & 1 berry
            player.resources = player.resources.gain(ResourceBank(twig=1, resin=1, berry=1))
        elif self.id == "forest_02":  # 2 any resource (interactive choice)
            pass  # Handled at action level — player chooses 2 resources
        elif self.id == "forest_03":  # 2 berries & 1 card
            player.resources = player.resources.gain(ResourceBank(berry=2))
            if deck_mgr:
                _draw_cards_for_player(player, deck_mgr, 1)
        elif self.id == "forest_04":  # 2 cards & 1 any resource (interactive choice)
            if deck_mgr:
                _draw_cards_for_player(player, deck_mgr, 2)
            # +1 any resource handled at action level
        elif self.id == "forest_05":  # 2 resin & 1 twig
            player.resources = player.resources.gain(ResourceBank(resin=2, twig=1))
        elif self.id == "forest_06":  # 3 berries
            player.resources = player.resources.gain(ResourceBank(berry=3))
        elif self.id == "forest_07":  # 3 cards & 1 pebble
            if deck_mgr:
                _draw_cards_for_player(player, deck_mgr, 3)
            player.resources = player.resources.gain(ResourceBank(pebble=1))
        elif self.id == "forest_08":  # Copy any Basic location and draw 1 card (interactive choice)
            if deck_mgr:
                _draw_cards_for_player(player, deck_mgr, 1)
            # Basic location copy handled at action level
        elif self.id == "forest_09":  # Discard up to 3 cards & gain 1 any for each card (interactive)
            pass  # Handled at action level — player chooses cards to discard and resources
        elif self.id == "forest_10":  # Discard any, then draw 2 for every card discarded (interactive)
            pass  # Handled at action level — player chooses cards to discard
        elif self.id == "forest_11":  # Draw 2 Meadow cards and play 1 for -1 any (interactive)
            pass  # Handled at action level — player chooses meadow cards


class HavenLocation(Location):
    """Shared location: discard 2 cards for 1 any resource."""

    location_type: LocationType = LocationType.HAVEN
    exclusive: bool = False


class JourneyLocation(Location):
    """Autumn only: discard cards equal to point value."""

    location_type: LocationType = LocationType.JOURNEY
    point_value: int = 0

    def is_available(self, player_id: str) -> bool:
        """Journey locations use normal availability rules; season check is in LocationManager."""
        return super().is_available(player_id)


class EventLocation(Location):
    """For basic and special events."""

    location_type: LocationType = LocationType.EVENT


# --- All 11 forest locations (verified against physical card scans 2026-03-10) ---
ALL_FOREST_LOCATIONS = [
    ForestLocation(id="forest_01", name="1 twig, 1 resin & 1 berry"),
    ForestLocation(id="forest_02", name="2 any"),
    ForestLocation(id="forest_03", name="2 berries & 1 card"),
    ForestLocation(id="forest_04", name="2 cards & 1 any"),
    ForestLocation(id="forest_05", name="2 resin & 1 twig"),
    ForestLocation(id="forest_06", name="3 berries"),
    ForestLocation(id="forest_07", name="3 cards & 1 pebble"),
    ForestLocation(id="forest_08", name="Copy any Basic location and draw 1 card"),
    ForestLocation(id="forest_09", name="Discard up to 3 cards & gain 1 any for each card"),
    ForestLocation(id="forest_10", name="Discard any, then draw 2 for every card discarded"),
    ForestLocation(id="forest_11", name="Draw 2 Meadow cards and play 1 for -1 any"),
]


class LocationManager:
    """Initializes and manages all board locations."""

    def __init__(self, player_count: int, seed: int | None = None) -> None:
        self._locations: dict[str, Location] = {}
        self._player_count = player_count
        self._setup_basic_locations(player_count)
        self._setup_forest_locations(player_count, seed)
        self._setup_haven()
        self._setup_journey_locations()

    def _setup_basic_locations(self, player_count: int) -> None:
        basics = [
            BasicLocation(id="basic_3twigs", name="3 Twigs", exclusive=True),
            BasicLocation(id="basic_2twigs_1card", name="2 Twigs + 1 Card", exclusive=False),
            BasicLocation(id="basic_2resin", name="2 Resin", exclusive=True),
            BasicLocation(id="basic_1resin_1card", name="1 Resin + 1 Card", exclusive=False),
            BasicLocation(id="basic_2cards_1point", name="2 Cards + 1 Point", exclusive=False),
            BasicLocation(id="basic_1pebble", name="1 Pebble", exclusive=True),
            BasicLocation(id="basic_1berry_1card", name="1 Berry + 1 Card", exclusive=True),
            BasicLocation(id="basic_1berry", name="1 Berry", exclusive=False),
        ]

        for loc in basics:
            self._locations[loc.id] = loc

    def _setup_forest_locations(self, player_count: int, seed: int | None) -> None:
        rng = random.Random(seed)
        count = 3 if player_count <= 2 else 4
        chosen = rng.sample(ALL_FOREST_LOCATIONS, count)
        for loc in chosen:
            copy = loc.model_copy(deep=True)
            self._locations[copy.id] = copy

    def _setup_haven(self) -> None:
        haven = HavenLocation(id="haven", name="Haven", exclusive=False)
        self._locations[haven.id] = haven

    def _setup_journey_locations(self) -> None:
        journeys = [
            JourneyLocation(id="journey_2pt", name="Journey (2 VP)", exclusive=False, point_value=2),
            JourneyLocation(id="journey_3pt", name="Journey (3 VP)", exclusive=True, point_value=3),
            JourneyLocation(id="journey_4pt", name="Journey (4 VP)", exclusive=True, point_value=4),
            JourneyLocation(id="journey_5pt", name="Journey (5 VP)", exclusive=True, point_value=5),
        ]
        for loc in journeys:
            self._locations[loc.id] = loc

    def get_available_locations(self, player_id: str, season: Season) -> list[Location]:
        """Return all locations where the player can place a worker."""
        available = []
        for loc in self._locations.values():
            # Journey locations only available in autumn
            if loc.location_type == LocationType.JOURNEY and season != Season.AUTUMN:
                continue
            if loc.is_available(player_id):
                available.append(loc)
        return available

    def place_worker(self, location_id: str, player_id: str) -> None:
        loc = self._locations.get(location_id)
        if loc is None:
            raise ValueError(f"Unknown location: {location_id}")
        loc.place_worker(player_id)

    def recall_all_workers(self, player_id: str) -> list[Location]:
        """Recall all workers for a player. Returns locations they were recalled from."""
        recalled_from = []
        for loc in self._locations.values():
            if player_id in loc.workers:
                loc.remove_worker(player_id)
                recalled_from.append(loc)
        return recalled_from

    def get_location(self, location_id: str) -> Location | None:
        return self._locations.get(location_id)

    @property
    def all_locations(self) -> list[Location]:
        return list(self._locations.values())
