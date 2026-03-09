import pytest

from ed_engine.engine.workers import WorkerManager
from ed_engine.models.enums import Season


class TestWorkerManager:
    def test_initial_workers(self) -> None:
        wm = WorkerManager()
        assert wm.total_workers == 2
        assert wm.available_workers() == 2
        assert wm.deployed_workers == []

    def test_deploy(self) -> None:
        wm = WorkerManager()
        wm.deploy("basic_3twigs")
        assert wm.available_workers() == 1
        assert "basic_3twigs" in wm.deployed_workers

    def test_deploy_all_workers(self) -> None:
        wm = WorkerManager()
        wm.deploy("loc1")
        wm.deploy("loc2")
        assert wm.available_workers() == 0

    def test_deploy_no_available_raises(self) -> None:
        wm = WorkerManager()
        wm.deploy("loc1")
        wm.deploy("loc2")
        with pytest.raises(ValueError, match="No available workers"):
            wm.deploy("loc3")

    def test_recall_all(self) -> None:
        wm = WorkerManager()
        wm.deploy("loc1")
        wm.deploy("loc2")
        locations = wm.recall_all()
        assert sorted(locations) == ["loc1", "loc2"]
        assert wm.available_workers() == 2
        assert wm.deployed_workers == []

    def test_recall_all_empty(self) -> None:
        wm = WorkerManager()
        locations = wm.recall_all()
        assert locations == []

    def test_gain_workers_spring(self) -> None:
        wm = WorkerManager()
        wm.gain_workers(Season.SPRING)
        assert wm.total_workers == 3

    def test_gain_workers_summer(self) -> None:
        wm = WorkerManager()
        wm.gain_workers(Season.SUMMER)
        assert wm.total_workers == 3

    def test_gain_workers_autumn(self) -> None:
        wm = WorkerManager()
        wm.gain_workers(Season.AUTUMN)
        assert wm.total_workers == 4

    def test_gain_workers_winter_noop(self) -> None:
        wm = WorkerManager()
        wm.gain_workers(Season.WINTER)
        assert wm.total_workers == 2

    def test_full_season_progression(self) -> None:
        """Simulate gaining workers through all seasons: 2 -> 3 -> 4 -> 6."""
        wm = WorkerManager()
        assert wm.total_workers == 2
        wm.gain_workers(Season.SPRING)
        assert wm.total_workers == 3
        wm.gain_workers(Season.SUMMER)
        assert wm.total_workers == 4
        wm.gain_workers(Season.AUTUMN)
        assert wm.total_workers == 6

    def test_deploy_after_gaining_workers(self) -> None:
        wm = WorkerManager()
        wm.gain_workers(Season.SPRING)
        wm.deploy("loc1")
        wm.deploy("loc2")
        wm.deploy("loc3")
        assert wm.available_workers() == 0
