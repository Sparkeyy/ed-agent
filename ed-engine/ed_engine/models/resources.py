from __future__ import annotations

from pydantic import BaseModel

# Supply limits (total tokens in the game box)
SUPPLY_TWIGS = 30
SUPPLY_RESIN = 25
SUPPLY_PEBBLES = 20
SUPPLY_BERRIES = 30


class ResourceBank(BaseModel):
    twig: int = 0
    resin: int = 0
    pebble: int = 0
    berry: int = 0

    def total(self) -> int:
        return self.twig + self.resin + self.pebble + self.berry

    def can_afford(self, cost: ResourceBank) -> bool:
        return (
            self.twig >= cost.twig
            and self.resin >= cost.resin
            and self.pebble >= cost.pebble
            and self.berry >= cost.berry
        )

    def spend(self, cost: ResourceBank) -> ResourceBank:
        if not self.can_afford(cost):
            raise ValueError("Cannot afford cost")
        return ResourceBank(
            twig=self.twig - cost.twig,
            resin=self.resin - cost.resin,
            pebble=self.pebble - cost.pebble,
            berry=self.berry - cost.berry,
        )

    def gain(self, amount: ResourceBank) -> ResourceBank:
        return ResourceBank(
            twig=self.twig + amount.twig,
            resin=self.resin + amount.resin,
            pebble=self.pebble + amount.pebble,
            berry=self.berry + amount.berry,
        )

    def __add__(self, other: ResourceBank) -> ResourceBank:
        return self.gain(other)

    def __sub__(self, other: ResourceBank) -> ResourceBank:
        return self.spend(other)

    def __ge__(self, other: ResourceBank) -> bool:
        return self.can_afford(other)

    def clamp_to_zero(self) -> ResourceBank:
        """Return a new ResourceBank with each resource floored at 0."""
        return ResourceBank(
            twig=max(self.twig, 0),
            resin=max(self.resin, 0),
            pebble=max(self.pebble, 0),
            berry=max(self.berry, 0),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "twig": self.twig,
            "resin": self.resin,
            "pebble": self.pebble,
            "berry": self.berry,
        }

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> ResourceBank:
        return cls(
            twig=data.get("twig", 0),
            resin=data.get("resin", 0),
            pebble=data.get("pebble", 0),
            berry=data.get("berry", 0),
        )


SUPPLY_LIMITS = {
    "twig": SUPPLY_TWIGS,
    "resin": SUPPLY_RESIN,
    "pebble": SUPPLY_PEBBLES,
    "berry": SUPPLY_BERRIES,
}


class SupplyPool(BaseModel):
    """Shared supply of resources for the game."""

    twig: int = SUPPLY_TWIGS
    resin: int = SUPPLY_RESIN
    pebble: int = SUPPLY_PEBBLES
    berry: int = SUPPLY_BERRIES
