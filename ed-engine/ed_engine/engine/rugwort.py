"""Rugwort solo AI opponent for Everdell.

Rugwort is a deterministic solo opponent who doesn't play like a normal player.
He uses dice rolls to take Meadow cards and blocks locations/meadow slots
according to fixed season-progression rules.

Year variants:
  1 - "Rugwort the Rascal": base rules (3pt journey, 3pt per unachieved special event)
  2 - "Rugwort the Rotten": 4pt journey, 6pt per unachieved special event
  3 - "Rugwort the Rapscallion": 5pt journey, kidnaps a human worker in autumn
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from ed_engine.models.card import Card
from ed_engine.models.enums import CardType, Season

if TYPE_CHECKING:
    from ed_engine.engine.deck import DeckManager
    from ed_engine.engine.events import EventManager
    from ed_engine.engine.locations import LocationManager


# Basic event ID -> required CardType color
_BASIC_EVENT_COLORS: dict[str, CardType] = {
    "basic_governance": CardType.BLUE_GOVERNANCE,
    "basic_destination": CardType.RED_DESTINATION,
    "basic_traveler": CardType.TAN_TRAVELER,
    "basic_production": CardType.GREEN_PRODUCTION,
}

# Season -> which basic location Rugwort's roaming worker moves to
_ROAMING_WORKER_PROGRESSION: dict[Season, str] = {
    Season.SPRING: "basic_2resin",
    Season.SUMMER: "basic_1pebble",
    Season.AUTUMN: "basic_1berry_1card",
}

# Season -> initial location for roaming worker
_ROAMING_WORKER_INITIAL = "basic_3twigs"

# Season -> meadow indices to block with new workers (0-indexed)
_MEADOW_BLOCK_BY_SEASON: dict[Season, list[int]] = {
    Season.SPRING: [0],
    Season.SUMMER: [1],
    Season.AUTUMN: [2, 3],
}

# Journey location Rugwort places a worker on during autumn
_JOURNEY_LOCATION = "journey_3pt"


class RugwortAI:
    """Deterministic solo opponent for Everdell."""

    RUGWORT_ID = "rugwort"

    def __init__(self, year: int = 1, seed: int | None = None) -> None:
        """Year 1/2/3 determines difficulty variant."""
        if year not in (1, 2, 3):
            raise ValueError(f"Year must be 1, 2, or 3, got {year}")
        self.year = year
        self.rng = random.Random(seed)
        self.city_cards: list[Card] = []
        self.workers_on_meadow: list[int] = []  # blocked meadow indices (0-7)
        self.achieved_events: list[str] = []  # event IDs
        self.journey_points: int = 0
        self.point_tokens: int = 0
        self.current_season: Season = Season.WINTER
        self.roaming_worker_location: str | None = None
        self.forest_worker_location: str | None = None
        self._kidnapped_worker: bool = False

    @property
    def journey_value(self) -> int:
        """Journey point value based on year difficulty."""
        return {1: 3, 2: 4, 3: 5}[self.year]

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup(
        self,
        location_mgr: LocationManager,
        forest_location_id: str | None = None,
    ) -> list[str]:
        """Place initial workers: one on a Forest card, one on the 3-twig space.

        Args:
            location_mgr: The game's location manager.
            forest_location_id: Which forest location to block. If None,
                picks the first available forest location.

        Returns:
            List of event description strings.
        """
        events: list[str] = []

        # Find the first forest location if not specified
        if forest_location_id is None:
            for loc in location_mgr.all_locations:
                if loc.id.startswith("forest_"):
                    forest_location_id = loc.id
                    break

        if forest_location_id is not None:
            loc = location_mgr.get_location(forest_location_id)
            if loc is not None and loc.is_available(self.RUGWORT_ID):
                loc.place_worker(self.RUGWORT_ID)
                self.forest_worker_location = forest_location_id
                events.append(
                    f"Rugwort placed a worker on {forest_location_id} (forest)"
                )

        # Place roaming worker on 3-twig location
        twig_loc = location_mgr.get_location(_ROAMING_WORKER_INITIAL)
        if twig_loc is not None:
            twig_loc.place_worker(self.RUGWORT_ID)
            self.roaming_worker_location = _ROAMING_WORKER_INITIAL
            events.append(
                f"Rugwort placed a worker on {_ROAMING_WORKER_INITIAL} (roaming)"
            )

        return events

    # ------------------------------------------------------------------
    # Card play (after human plays a card)
    # ------------------------------------------------------------------

    def on_human_plays_card(self, deck_mgr: DeckManager) -> dict[str, Any]:
        """After human plays a card, Rugwort rolls a die and takes a meadow card.

        Returns a dict with keys:
            'die_roll': int (1-8)
            'adjusted_index': int (actual meadow index used)
            'card': Card | None
            'blocked': bool (True if original slot was blocked)
        """
        meadow = deck_mgr.meadow
        if not meadow:
            return {
                "die_roll": 0,
                "adjusted_index": -1,
                "card": None,
                "blocked": False,
            }

        die_roll = self.rng.randint(1, 8)
        # Die roll maps to 0-indexed meadow position
        target_index = die_roll - 1

        # Adjust for blocked positions and out-of-range
        actual_index = self._find_available_meadow_index(target_index, len(meadow))
        if actual_index is None:
            return {
                "die_roll": die_roll,
                "adjusted_index": -1,
                "card": None,
                "blocked": True,
            }

        was_blocked = actual_index != target_index

        # Take the card from meadow (this also replenishes)
        card = deck_mgr.draw_from_meadow(actual_index)
        self.city_cards.append(card)

        # Update blocked indices after meadow shift
        self._adjust_blocked_indices_after_removal(actual_index)

        return {
            "die_roll": die_roll,
            "adjusted_index": actual_index,
            "card": card,
            "blocked": was_blocked,
        }

    def _find_available_meadow_index(
        self, target: int, meadow_size: int
    ) -> int | None:
        """Find the nearest available (unblocked) meadow index.

        Searches forward from target, wrapping around. Returns None if
        all slots are blocked.
        """
        for offset in range(meadow_size):
            candidate = (target + offset) % meadow_size
            if candidate not in self.workers_on_meadow:
                return candidate
        return None

    def _adjust_blocked_indices_after_removal(self, removed_index: int) -> None:
        """After a card is removed from the meadow, indices shift down.

        Any blocked index > removed_index decreases by 1, then the new
        card fills at the end (index 7), so no blocked index should
        reference removed_index anymore.
        """
        new_blocked: list[int] = []
        for idx in self.workers_on_meadow:
            if idx > removed_index:
                new_blocked.append(idx - 1)
            elif idx < removed_index:
                new_blocked.append(idx)
            # idx == removed_index: this shouldn't happen since we skip blocked,
            # but drop it if it does
        self.workers_on_meadow = new_blocked

    # ------------------------------------------------------------------
    # Prepare for season
    # ------------------------------------------------------------------

    def on_human_prepares_for_season(
        self,
        season: Season,
        location_mgr: LocationManager,
        event_mgr: EventManager | None = None,
    ) -> list[str]:
        """Execute Rugwort's prepare-for-season actions.

        Called immediately after the human prepares for a given season.

        Steps:
            1. Check and claim basic events (if event_mgr provided)
            2. Place worker(s) on meadow to block
            3. Move roaming worker to next action space
            4. Autumn special actions (forest worker -> journey, year 3 kidnap)
        """
        self.current_season = season
        events: list[str] = []

        # 1. Claim basic events
        if event_mgr is not None:
            claim_events = self._check_and_claim_events(event_mgr)
            events.extend(claim_events)

        # 2. Block meadow slots
        block_indices = _MEADOW_BLOCK_BY_SEASON.get(season, [])
        for idx in block_indices:
            if idx not in self.workers_on_meadow and 0 <= idx <= 7:
                self.workers_on_meadow.append(idx)
                events.append(f"Rugwort blocked meadow slot {idx + 1}")

        # 3. Move roaming worker to next action space
        new_loc = _ROAMING_WORKER_PROGRESSION.get(season)
        if new_loc is not None:
            # Remove from old location
            if self.roaming_worker_location is not None:
                old_loc = location_mgr.get_location(self.roaming_worker_location)
                if old_loc is not None:
                    old_loc.remove_worker(self.RUGWORT_ID)

            # Place on new location
            target_loc = location_mgr.get_location(new_loc)
            if target_loc is not None:
                target_loc.place_worker(self.RUGWORT_ID)
                self.roaming_worker_location = new_loc
                events.append(f"Rugwort moved roaming worker to {new_loc}")

        # 4. Autumn special actions
        if season == Season.AUTUMN:
            # Remove forest worker and place on journey
            if self.forest_worker_location is not None:
                forest_loc = location_mgr.get_location(self.forest_worker_location)
                if forest_loc is not None:
                    forest_loc.remove_worker(self.RUGWORT_ID)
                events.append(
                    f"Rugwort removed worker from {self.forest_worker_location}"
                )
                self.forest_worker_location = None

            # Place on 3-point journey location
            journey_loc = location_mgr.get_location(_JOURNEY_LOCATION)
            if journey_loc is not None:
                journey_loc.place_worker(self.RUGWORT_ID)
                self.journey_points = self.journey_value
                events.append(
                    f"Rugwort placed worker on journey ({self.journey_value} points)"
                )

        return events

    def _check_and_claim_events(self, event_mgr: EventManager) -> list[str]:
        """Claim any basic events Rugwort qualifies for (3+ cards of a color)."""
        events: list[str] = []
        for event_id, card_type in _BASIC_EVENT_COLORS.items():
            if event_id in self.achieved_events:
                continue
            if self.can_claim_basic_event(card_type):
                success = event_mgr.claim_event(event_id, self.RUGWORT_ID)
                if success:
                    self.achieved_events.append(event_id)
                    events.append(f"Rugwort claimed basic event: {event_id}")
        return events

    def can_claim_basic_event(self, card_type: CardType) -> bool:
        """Check if Rugwort has 3+ cards of the required color/type."""
        count = sum(1 for c in self.city_cards if c.card_type == card_type)
        return count >= 3

    # ------------------------------------------------------------------
    # Year 3: Kidnap
    # ------------------------------------------------------------------

    def kidnap_worker(self, human_workers_deployed: list[str]) -> str | None:
        """Year 3 autumn: kidnap one of the human player's workers.

        Returns the location ID of the kidnapped worker, or None if
        not applicable (year < 3 or no workers to kidnap).
        """
        if self.year < 3:
            return None
        if not human_workers_deployed:
            return None
        # Pick the first deployed worker location
        self._kidnapped_worker = True
        return human_workers_deployed[0]

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def calculate_score(
        self,
        human_special_events: list[str],
        total_special_events: int = 4,
    ) -> int:
        """Calculate Rugwort's final score.

        Args:
            human_special_events: Event IDs the human achieved.
            total_special_events: Total special events in the game (default 4).

        Returns:
            Rugwort's total score.
        """
        score = 0

        # 2 points per card, 3 per purple/prosperity
        for card in self.city_cards:
            if card.card_type == CardType.PURPLE_PROSPERITY:
                score += 3
            else:
                score += 2

        # 3 points per basic event claimed
        score += len(self.achieved_events) * 3

        # Points for unachieved special events (human didn't get them)
        unachieved = total_special_events - len(human_special_events)
        if self.year == 1:
            score += unachieved * 3
        elif self.year >= 2:
            score += unachieved * 6

        # Journey points
        score += self.journey_points

        # Point tokens given by human
        score += self.point_tokens

        return score

    def add_point_tokens(self, amount: int) -> None:
        """Add point tokens (e.g., from human card effects)."""
        self.point_tokens += amount
