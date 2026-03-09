import pytest

from ed_engine.models.resources import ResourceBank


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
