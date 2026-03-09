import pytest

from ed_engine.models.enums import ResourceType
from ed_engine.models.resources import (
    MAX_BERRY,
    MAX_PEBBLE,
    MAX_RESIN,
    MAX_TWIG,
    SUPPLY_LIMITS,
    ResourceBank,
    SupplyPool,
)


class TestResourceBank:
    def test_total(self) -> None:
        bank = ResourceBank(twig=1, resin=2, pebble=3, berry=4)
        assert bank.total() == 10

    def test_total_empty(self) -> None:
        bank = ResourceBank()
        assert bank.total() == 0

    def test_can_afford_true(self) -> None:
        bank = ResourceBank(twig=3, resin=2, pebble=1, berry=5)
        cost = ResourceBank(twig=2, resin=1, pebble=0, berry=3)
        assert bank.can_afford(cost) is True

    def test_can_afford_false(self) -> None:
        bank = ResourceBank(twig=1, resin=0, pebble=0, berry=0)
        cost = ResourceBank(twig=2)
        assert bank.can_afford(cost) is False

    def test_can_afford_exact(self) -> None:
        bank = ResourceBank(twig=2, resin=1)
        cost = ResourceBank(twig=2, resin=1)
        assert bank.can_afford(cost) is True

    def test_spend(self) -> None:
        bank = ResourceBank(twig=5, resin=3, pebble=2, berry=4)
        cost = ResourceBank(twig=2, resin=1, pebble=1, berry=3)
        result = bank.spend(cost)
        assert result.twig == 3
        assert result.resin == 2
        assert result.pebble == 1
        assert result.berry == 1

    def test_spend_insufficient_raises(self) -> None:
        bank = ResourceBank(twig=1)
        cost = ResourceBank(twig=5)
        with pytest.raises(ValueError, match="Cannot afford"):
            bank.spend(cost)

    def test_gain(self) -> None:
        bank = ResourceBank(twig=1, resin=1)
        amount = ResourceBank(twig=2, berry=3)
        result = bank.gain(amount)
        assert result.twig == 3
        assert result.resin == 1
        assert result.pebble == 0
        assert result.berry == 3

    def test_spend_does_not_mutate(self) -> None:
        bank = ResourceBank(twig=5)
        bank.spend(ResourceBank(twig=2))
        assert bank.twig == 5  # original unchanged

    def test_gain_does_not_mutate(self) -> None:
        bank = ResourceBank(twig=1)
        bank.gain(ResourceBank(twig=10))
        assert bank.twig == 1  # original unchanged

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            ResourceBank(twig=-1)

    def test_negative_resin_raises(self) -> None:
        with pytest.raises(ValueError, match="resin cannot be negative"):
            ResourceBank(resin=-5)

    def test_get_resource_type(self) -> None:
        bank = ResourceBank(twig=3, resin=7, pebble=1, berry=5)
        assert bank.get(ResourceType.TWIG) == 3
        assert bank.get(ResourceType.RESIN) == 7
        assert bank.get(ResourceType.PEBBLE) == 1
        assert bank.get(ResourceType.BERRY) == 5

    def test_is_empty(self) -> None:
        assert ResourceBank().is_empty() is True
        assert ResourceBank(twig=1).is_empty() is False

    def test_clamp_to(self) -> None:
        bank = ResourceBank(twig=10, resin=20, pebble=5, berry=0)
        limits = ResourceBank(twig=5, resin=15, pebble=15, berry=15)
        result = bank.clamp_to(limits)
        assert result.twig == 5
        assert result.resin == 15
        assert result.pebble == 5
        assert result.berry == 0

    def test_of_single_resource(self) -> None:
        bank = ResourceBank.of(ResourceType.BERRY, 4)
        assert bank.berry == 4
        assert bank.twig == 0
        assert bank.resin == 0
        assert bank.pebble == 0

    def test_add_operator(self) -> None:
        a = ResourceBank(twig=1, resin=2)
        b = ResourceBank(twig=3, berry=1)
        result = a + b
        assert result.twig == 4
        assert result.resin == 2
        assert result.berry == 1

    def test_sub_operator(self) -> None:
        a = ResourceBank(twig=5, resin=3)
        b = ResourceBank(twig=2, resin=1)
        result = a - b
        assert result.twig == 3
        assert result.resin == 2

    def test_sub_operator_insufficient_raises(self) -> None:
        a = ResourceBank(twig=1)
        b = ResourceBank(twig=5)
        with pytest.raises(ValueError, match="Cannot afford"):
            _ = a - b


class TestSupplyLimits:
    def test_supply_limits_values(self) -> None:
        assert SUPPLY_LIMITS[ResourceType.TWIG] == 24
        assert SUPPLY_LIMITS[ResourceType.RESIN] == 15
        assert SUPPLY_LIMITS[ResourceType.PEBBLE] == 15
        assert SUPPLY_LIMITS[ResourceType.BERRY] == 15

    def test_max_constants(self) -> None:
        assert MAX_TWIG == 24
        assert MAX_RESIN == 15
        assert MAX_PEBBLE == 15
        assert MAX_BERRY == 15


class TestSupplyPool:
    def test_default_supply(self) -> None:
        pool = SupplyPool()
        assert pool.available.twig == 24
        assert pool.available.resin == 15
        assert pool.available.pebble == 15
        assert pool.available.berry == 15

    def test_remaining(self) -> None:
        pool = SupplyPool()
        assert pool.remaining(ResourceType.TWIG) == 24
        assert pool.remaining(ResourceType.BERRY) == 15

    def test_can_provide(self) -> None:
        pool = SupplyPool()
        assert pool.can_provide(ResourceBank(twig=10)) is True
        assert pool.can_provide(ResourceBank(twig=25)) is False

    def test_take_exact(self) -> None:
        pool = SupplyPool()
        new_pool = pool.take_exact(ResourceBank(twig=5, resin=3))
        assert new_pool.available.twig == 19
        assert new_pool.available.resin == 12
        # Original unchanged
        assert pool.available.twig == 24

    def test_take_exact_insufficient_raises(self) -> None:
        pool = SupplyPool()
        with pytest.raises(ValueError, match="Supply does not have enough"):
            pool.take_exact(ResourceBank(twig=25))

    def test_take_clamps_to_available(self) -> None:
        pool = SupplyPool(available=ResourceBank(twig=3, resin=0, pebble=15, berry=15))
        new_pool = pool.take(ResourceBank(twig=10))  # want 10, only 3 available
        assert new_pool.available.twig == 0

    def test_return_resources(self) -> None:
        pool = SupplyPool(available=ResourceBank(twig=20, resin=10, pebble=10, berry=10))
        new_pool = pool.return_resources(ResourceBank(twig=3, resin=2))
        assert new_pool.available.twig == 23
        assert new_pool.available.resin == 12

    def test_return_resources_caps_at_limit(self) -> None:
        pool = SupplyPool(available=ResourceBank(twig=23, resin=15, pebble=15, berry=15))
        new_pool = pool.return_resources(ResourceBank(twig=5))
        assert new_pool.available.twig == 24  # capped at MAX_TWIG

    def test_gain_from_supply(self) -> None:
        pool = SupplyPool()
        player = ResourceBank(twig=2, berry=1)
        amount = ResourceBank(twig=3, berry=2)
        new_player, new_supply = pool.gain_from_supply(player, amount)
        assert new_player.twig == 5
        assert new_player.berry == 3
        assert new_supply.available.twig == 21
        assert new_supply.available.berry == 13

    def test_gain_from_supply_clamps_to_available(self) -> None:
        pool = SupplyPool(available=ResourceBank(twig=2, resin=0, pebble=15, berry=15))
        player = ResourceBank()
        amount = ResourceBank(twig=5)  # want 5, only 2 available
        new_player, new_supply = pool.gain_from_supply(player, amount)
        assert new_player.twig == 2  # only got what supply had
        assert new_supply.available.twig == 0

    def test_spend_to_supply(self) -> None:
        pool = SupplyPool(available=ResourceBank(twig=20, resin=10, pebble=10, berry=10))
        player = ResourceBank(twig=5, resin=3)
        cost = ResourceBank(twig=2, resin=1)
        new_player, new_supply = pool.spend_to_supply(player, cost)
        assert new_player.twig == 3
        assert new_player.resin == 2
        assert new_supply.available.twig == 22
        assert new_supply.available.resin == 11

    def test_spend_to_supply_insufficient_raises(self) -> None:
        pool = SupplyPool()
        player = ResourceBank(twig=1)
        cost = ResourceBank(twig=5)
        with pytest.raises(ValueError, match="Cannot afford"):
            pool.spend_to_supply(player, cost)

    def test_immutability(self) -> None:
        pool = SupplyPool()
        pool.take_exact(ResourceBank(twig=5))
        assert pool.available.twig == 24  # original unchanged

    def test_full_round_trip(self) -> None:
        """Player gains from supply, then spends back — supply is restored."""
        pool = SupplyPool()
        player = ResourceBank()
        amount = ResourceBank(twig=5, berry=3)
        # Gain from supply
        player, pool = pool.gain_from_supply(player, amount)
        assert player.twig == 5
        assert pool.available.twig == 19
        # Spend back to supply
        player, pool = pool.spend_to_supply(player, amount)
        assert player.twig == 0
        assert pool.available.twig == 24
