import pytest

from ed_engine.models.resources import (
    SUPPLY_BERRIES,
    SUPPLY_PEBBLES,
    SUPPLY_RESIN,
    SUPPLY_TWIGS,
    ResourceBank,
)
from ed_engine.engine.supply import Supply
from ed_engine.models.enums import ResourceType


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
        assert bank.twig == 5

    def test_gain_does_not_mutate(self) -> None:
        bank = ResourceBank(twig=1)
        bank.gain(ResourceBank(twig=10))
        assert bank.twig == 1

    # --- New operator tests ---

    def test_add_operator(self) -> None:
        a = ResourceBank(twig=1, resin=2)
        b = ResourceBank(twig=3, berry=4)
        result = a + b
        assert result == ResourceBank(twig=4, resin=2, pebble=0, berry=4)

    def test_sub_operator(self) -> None:
        a = ResourceBank(twig=5, resin=3, pebble=2, berry=4)
        b = ResourceBank(twig=2, resin=1, pebble=1, berry=3)
        result = a - b
        assert result == ResourceBank(twig=3, resin=2, pebble=1, berry=1)

    def test_sub_operator_insufficient_raises(self) -> None:
        a = ResourceBank(twig=1)
        b = ResourceBank(twig=5)
        with pytest.raises(ValueError):
            _ = a - b

    def test_ge_operator_true(self) -> None:
        bank = ResourceBank(twig=3, resin=2)
        cost = ResourceBank(twig=2, resin=1)
        assert bank >= cost

    def test_ge_operator_exact(self) -> None:
        bank = ResourceBank(twig=2, resin=1)
        cost = ResourceBank(twig=2, resin=1)
        assert bank >= cost

    def test_ge_operator_false(self) -> None:
        bank = ResourceBank(twig=1)
        cost = ResourceBank(twig=2)
        assert not (bank >= cost)

    def test_clamp_to_zero(self) -> None:
        bank = ResourceBank(twig=-3, resin=2, pebble=-1, berry=0)
        result = bank.clamp_to_zero()
        assert result == ResourceBank(twig=0, resin=2, pebble=0, berry=0)

    def test_clamp_to_zero_no_negatives(self) -> None:
        bank = ResourceBank(twig=1, resin=2, pebble=3, berry=4)
        result = bank.clamp_to_zero()
        assert result == bank

    def test_to_dict(self) -> None:
        bank = ResourceBank(twig=1, resin=2, pebble=3, berry=4)
        d = bank.to_dict()
        assert d == {"twig": 1, "resin": 2, "pebble": 3, "berry": 4}

    def test_from_dict(self) -> None:
        d = {"twig": 5, "resin": 3, "pebble": 1, "berry": 7}
        bank = ResourceBank.from_dict(d)
        assert bank == ResourceBank(twig=5, resin=3, pebble=1, berry=7)

    def test_from_dict_partial(self) -> None:
        d = {"twig": 2}
        bank = ResourceBank.from_dict(d)
        assert bank == ResourceBank(twig=2, resin=0, pebble=0, berry=0)

    def test_from_dict_empty(self) -> None:
        bank = ResourceBank.from_dict({})
        assert bank == ResourceBank()

    def test_supply_constants(self) -> None:
        assert SUPPLY_TWIGS == 30
        assert SUPPLY_RESIN == 25
        assert SUPPLY_PEBBLES == 20
        assert SUPPLY_BERRIES == 30


class TestSupply:
    def test_initial_supply(self) -> None:
        supply = Supply()
        avail = supply.available()
        assert avail.twig == SUPPLY_TWIGS
        assert avail.resin == SUPPLY_RESIN
        assert avail.pebble == SUPPLY_PEBBLES
        assert avail.berry == SUPPLY_BERRIES

    def test_take_full_amount(self) -> None:
        supply = Supply()
        taken = supply.take(ResourceType.TWIG, 5)
        assert taken == 5
        assert supply.available().twig == SUPPLY_TWIGS - 5

    def test_take_more_than_available(self) -> None:
        supply = Supply()
        # Take all twigs
        supply.take(ResourceType.TWIG, SUPPLY_TWIGS)
        # Try to take more
        taken = supply.take(ResourceType.TWIG, 10)
        assert taken == 0

    def test_take_partial(self) -> None:
        supply = Supply()
        supply.take(ResourceType.PEBBLE, SUPPLY_PEBBLES - 3)
        taken = supply.take(ResourceType.PEBBLE, 10)
        assert taken == 3
        assert supply.available().pebble == 0

    def test_return_resources(self) -> None:
        supply = Supply()
        supply.take(ResourceType.TWIG, 10)
        supply.return_resources(ResourceBank(twig=5))
        assert supply.available().twig == SUPPLY_TWIGS - 10 + 5

    def test_return_resources_capped_at_max(self) -> None:
        supply = Supply()
        # Return more than was taken — should cap at max
        supply.return_resources(ResourceBank(twig=100))
        assert supply.available().twig == SUPPLY_TWIGS

    def test_available_is_copy(self) -> None:
        supply = Supply()
        avail = supply.available()
        # Modifying returned bank shouldn't affect supply
        assert supply.available().twig == SUPPLY_TWIGS
