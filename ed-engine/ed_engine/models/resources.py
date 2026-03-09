from __future__ import annotations

from pydantic import BaseModel, model_validator

from ed_engine.models.enums import ResourceType

# Everdell shared supply limits (per rulebook)
SUPPLY_LIMITS: dict[ResourceType, int] = {
    ResourceType.TWIG: 24,
    ResourceType.RESIN: 15,
    ResourceType.PEBBLE: 15,
    ResourceType.BERRY: 15,
}

MAX_TWIG = SUPPLY_LIMITS[ResourceType.TWIG]
MAX_RESIN = SUPPLY_LIMITS[ResourceType.RESIN]
MAX_PEBBLE = SUPPLY_LIMITS[ResourceType.PEBBLE]
MAX_BERRY = SUPPLY_LIMITS[ResourceType.BERRY]


class ResourceBank(BaseModel):
    twig: int = 0
    resin: int = 0
    pebble: int = 0
    berry: int = 0

    @model_validator(mode="after")
    def _no_negatives(self) -> ResourceBank:
        for field in ("twig", "resin", "pebble", "berry"):
            if getattr(self, field) < 0:
                raise ValueError(f"{field} cannot be negative (got {getattr(self, field)})")
        return self

    # ── Queries ──────────────────────────────────────────

    def total(self) -> int:
        return self.twig + self.resin + self.pebble + self.berry

    def can_afford(self, cost: ResourceBank) -> bool:
        return (
            self.twig >= cost.twig
            and self.resin >= cost.resin
            and self.pebble >= cost.pebble
            and self.berry >= cost.berry
        )

    def get(self, resource_type: ResourceType) -> int:
        return getattr(self, resource_type.value)

    def is_empty(self) -> bool:
        return self.total() == 0

    # ── Operations (immutable – always return new instances) ──

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

    def clamp_to(self, limits: ResourceBank) -> ResourceBank:
        """Return a new bank with each resource capped at the given limits."""
        return ResourceBank(
            twig=min(self.twig, limits.twig),
            resin=min(self.resin, limits.resin),
            pebble=min(self.pebble, limits.pebble),
            berry=min(self.berry, limits.berry),
        )

    # ── Constructors ─────────────────────────────────────

    @classmethod
    def of(cls, resource_type: ResourceType, amount: int) -> ResourceBank:
        """Create a bank with a single resource type."""
        return cls(**{resource_type.value: amount})

    def __add__(self, other: ResourceBank) -> ResourceBank:
        return self.gain(other)

    def __sub__(self, other: ResourceBank) -> ResourceBank:
        return self.spend(other)


class SupplyPool(BaseModel):
    """Shared supply of resources for the game. Players gain from and spend back to the supply."""

    available: ResourceBank = ResourceBank(
        twig=MAX_TWIG, resin=MAX_RESIN, pebble=MAX_PEBBLE, berry=MAX_BERRY,
    )

    def remaining(self, resource_type: ResourceType) -> int:
        return self.available.get(resource_type)

    def can_provide(self, amount: ResourceBank) -> bool:
        return self.available.can_afford(amount)

    def take(self, amount: ResourceBank) -> SupplyPool:
        """Remove resources from supply (player gains). Clamps to available."""
        clamped = amount.clamp_to(self.available)
        return SupplyPool(available=self.available.spend(clamped))

    def take_exact(self, amount: ResourceBank) -> SupplyPool:
        """Remove exact resources from supply. Raises if supply insufficient."""
        if not self.can_provide(amount):
            raise ValueError("Supply does not have enough resources")
        return SupplyPool(available=self.available.spend(amount))

    def return_resources(self, amount: ResourceBank) -> SupplyPool:
        """Return resources to supply (player spends). Caps at supply limits."""
        limits = ResourceBank(
            twig=MAX_TWIG, resin=MAX_RESIN, pebble=MAX_PEBBLE, berry=MAX_BERRY,
        )
        new_available = self.available.gain(amount).clamp_to(limits)
        return SupplyPool(available=new_available)

    def gain_from_supply(
        self, player_bank: ResourceBank, amount: ResourceBank,
    ) -> tuple[ResourceBank, SupplyPool]:
        """Player gains resources from supply. Clamps to what's available.

        Returns (new_player_bank, new_supply).
        """
        clamped = amount.clamp_to(self.available)
        new_player = player_bank.gain(clamped)
        new_supply = SupplyPool(available=self.available.spend(clamped))
        return new_player, new_supply

    def spend_to_supply(
        self, player_bank: ResourceBank, cost: ResourceBank,
    ) -> tuple[ResourceBank, SupplyPool]:
        """Player spends resources back to supply.

        Returns (new_player_bank, new_supply).
        """
        new_player = player_bank.spend(cost)
        new_supply = self.return_resources(cost)
        return new_player, new_supply
