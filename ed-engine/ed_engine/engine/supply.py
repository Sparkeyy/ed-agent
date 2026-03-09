from __future__ import annotations

from ed_engine.models.enums import ResourceType
from ed_engine.models.resources import (
    SUPPLY_BERRIES,
    SUPPLY_PEBBLES,
    SUPPLY_RESIN,
    SUPPLY_TWIGS,
    ResourceBank,
)


class Supply:
    """Tracks the shared resource pool for the game."""

    def __init__(self) -> None:
        self._pool = ResourceBank(
            twig=SUPPLY_TWIGS,
            resin=SUPPLY_RESIN,
            pebble=SUPPLY_PEBBLES,
            berry=SUPPLY_BERRIES,
        )

    def take(self, resource_type: ResourceType, amount: int) -> int:
        """Take resources from the supply. Returns actual amount taken (may be less if supply low)."""
        current = getattr(self._pool, resource_type.value)
        actual = min(amount, current)
        new_value = current - actual
        self._pool = self._pool.model_copy(update={resource_type.value: new_value})
        return actual

    def return_resources(self, bank: ResourceBank) -> None:
        """Return resources back to the supply."""
        self._pool = ResourceBank(
            twig=min(self._pool.twig + bank.twig, SUPPLY_TWIGS),
            resin=min(self._pool.resin + bank.resin, SUPPLY_RESIN),
            pebble=min(self._pool.pebble + bank.pebble, SUPPLY_PEBBLES),
            berry=min(self._pool.berry + bank.berry, SUPPLY_BERRIES),
        )

    def available(self) -> ResourceBank:
        """Return the current supply pool."""
        return self._pool.model_copy()
