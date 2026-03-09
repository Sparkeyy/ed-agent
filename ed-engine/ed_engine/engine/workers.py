from __future__ import annotations

from ed_engine.models.enums import Season


class WorkerManager:
    """Manages workers for a single player."""

    def __init__(self) -> None:
        self.total_workers: int = 2
        self.deployed_workers: list[str] = []  # location_ids

    def available_workers(self) -> int:
        return self.total_workers - len(self.deployed_workers)

    def deploy(self, location_id: str) -> None:
        if self.available_workers() <= 0:
            raise ValueError("No available workers to deploy")
        self.deployed_workers.append(location_id)

    def recall_all(self) -> list[str]:
        """Return all location_ids where workers were deployed, then clear."""
        locations = list(self.deployed_workers)
        self.deployed_workers.clear()
        return locations

    def gain_workers(self, season: Season) -> None:
        """Gain workers based on season advancement."""
        if season == Season.SPRING:
            self.total_workers += 1
        elif season == Season.SUMMER:
            self.total_workers += 1
        elif season == Season.AUTUMN:
            self.total_workers += 2
