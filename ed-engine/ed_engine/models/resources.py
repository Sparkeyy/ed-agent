from __future__ import annotations

from pydantic import BaseModel


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
