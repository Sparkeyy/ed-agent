"""Tests for the events system."""

from uuid import uuid4

import pytest

from ed_engine.cards.constructions import (
    Castle,
    Cemetery,
    Chapel,
    Courthouse,
    Dungeon,
    FairGrounds,
    Farm,
    GeneralStore,
    Inn,
    Lookout,
    Mine,
    PostOffice,
)
from ed_engine.cards.critters import (
    Bard,
    Doctor,
    Historian,
    Harvester,
    Innkeeper,
    Judge,
    King,
    Monk,
    PostalPigeon,
    Shepherd,
    Shopkeeper,
    Teacher,
    Gatherer,
    Woodcarver,
)
from ed_engine.engine.events import (
    BasicEvent,
    EventManager,
    SpecialEvent,
    SPECIAL_EVENT_DEFS,
)
from ed_engine.models.enums import CardType, Season
from ed_engine.models.player import Player
from ed_engine.models.resources import ResourceBank


def _make_player(name: str = "Alice") -> Player:
    return Player(id=uuid4(), name=name, season=Season.AUTUMN)


class TestBasicEventConditions:
    def test_governance_condition(self):
        p = _make_player()
        mgr = EventManager(seed=42)
        # No governance cards — should not qualify
        avail = [e for e in mgr.get_available_events(p) if e.id == "basic_governance"]
        assert len(avail) == 0

    def test_governance_met_with_3_blue(self):
        p = _make_player()
        p.city = [Courthouse(), Judge(), Innkeeper()]  # 3 blue governance cards
        mgr = EventManager(seed=42)
        avail = [e for e in mgr.get_available_events(p) if e.id == "basic_governance"]
        assert len(avail) == 1

    def test_destination_condition(self):
        p = _make_player()
        p.city = [Inn(), Cemetery(), Lookout()]  # 3 red destination cards
        mgr = EventManager(seed=42)
        avail = [e for e in mgr.get_available_events(p) if e.id == "basic_destination"]
        assert len(avail) == 1

    def test_traveler_condition(self):
        p = _make_player()
        p.city = [Bard(), Shepherd(), PostalPigeon()]  # 3 tan traveler cards
        mgr = EventManager(seed=42)
        avail = [e for e in mgr.get_available_events(p) if e.id == "basic_traveler"]
        assert len(avail) == 1

    def test_production_condition(self):
        p = _make_player()
        p.city = [Farm(), Mine(), GeneralStore()]  # 3 green production cards
        mgr = EventManager(seed=42)
        avail = [e for e in mgr.get_available_events(p) if e.id == "basic_production"]
        assert len(avail) == 1


class TestClaimingEvents:
    def test_claim_basic_event(self):
        p = _make_player()
        pid = str(p.id)
        p.city = [Farm(), Mine(), GeneralStore()]
        mgr = EventManager(seed=42)
        avail = mgr.get_available_events(p)
        prod_event = [e for e in avail if e.id == "basic_production"][0]
        assert mgr.claim_event(prod_event.id, pid) is True

    def test_cannot_claim_twice(self):
        p1 = _make_player("Alice")
        p2 = _make_player("Bob")
        p1.city = [Farm(), Mine(), GeneralStore()]
        p2.city = [Farm(), Mine(), GeneralStore()]
        mgr = EventManager(seed=42)

        assert mgr.claim_event("basic_production", str(p1.id)) is True
        assert mgr.claim_event("basic_production", str(p2.id)) is False

    def test_claimed_event_not_available(self):
        p = _make_player()
        p.city = [Farm(), Mine(), GeneralStore()]
        mgr = EventManager(seed=42)
        mgr.claim_event("basic_production", str(p.id))
        avail = mgr.get_available_events(p)
        prod = [e for e in avail if e.id == "basic_production"]
        assert len(prod) == 0

    def test_get_claimed_events(self):
        p = _make_player()
        pid = str(p.id)
        p.city = [Farm(), Mine(), GeneralStore()]
        mgr = EventManager(seed=42)
        mgr.claim_event("basic_production", pid)
        claimed = mgr.get_claimed_events(pid)
        assert len(claimed) == 1
        assert claimed[0].id == "basic_production"

    def test_claim_nonexistent_event(self):
        mgr = EventManager(seed=42)
        assert mgr.claim_event("fake_event", "player1") is False


class TestSpecialEventCardRequirements:
    def test_brilliant_wedding_requires_husband_and_wife(self):
        p = _make_player()
        mgr = EventManager(seed=None)
        # Force the brilliant wedding into the special events
        from ed_engine.engine.events import SPECIAL_EVENT_DEFS

        wedding_def = next(d for d in SPECIAL_EVENT_DEFS if d["id"] == "se_brilliant_wedding")
        mgr.special_events = [SpecialEvent(**wedding_def)]

        # No cards — not available
        avail = mgr.get_available_events(p)
        assert all(e.id != "se_brilliant_wedding" for e in avail)

        # Add both required cards
        p.city = [Harvester(), Gatherer()]
        avail = mgr.get_available_events(p)
        wedding = [e for e in avail if e.id == "se_brilliant_wedding"]
        assert len(wedding) == 1

    def test_three_card_special_event(self):
        """Grand Tour special event needs Inn + Post Office + Lookout."""
        p = _make_player()
        mgr = EventManager(seed=None)
        gt_def = next(d for d in SPECIAL_EVENT_DEFS if d["id"] == "se_grand_tour")
        mgr.special_events = [SpecialEvent(**gt_def)]

        # Only 2 of 3
        p.city = [Inn(), PostOffice()]
        avail = mgr.get_available_events(p)
        assert all(e.id != "se_grand_tour" for e in avail)

        # All 3
        p.city.append(Lookout())
        avail = mgr.get_available_events(p)
        gt = [e for e in avail if e.id == "se_grand_tour"]
        assert len(gt) == 1

    def test_special_event_claim(self):
        p = _make_player()
        pid = str(p.id)
        mgr = EventManager(seed=None)
        wedding_def = next(d for d in SPECIAL_EVENT_DEFS if d["id"] == "se_brilliant_wedding")
        mgr.special_events = [SpecialEvent(**wedding_def)]

        p.city = [Harvester(), Gatherer()]
        assert mgr.claim_event("se_brilliant_wedding", pid) is True
        assert mgr.claim_event("se_brilliant_wedding", pid) is False  # already claimed


class TestSetupDraws4SpecialEvents:
    def test_always_4_basic_events(self):
        mgr = EventManager(seed=42)
        assert len(mgr.basic_events) == 4

    def test_always_4_special_events(self):
        mgr = EventManager(seed=42)
        assert len(mgr.special_events) == 4

    def test_special_events_vary_with_seed(self):
        mgr1 = EventManager(seed=1)
        mgr2 = EventManager(seed=999)
        ids1 = {e.id for e in mgr1.special_events}
        ids2 = {e.id for e in mgr2.special_events}
        # Very unlikely to be identical with different seeds (16 choose 4 = 1820)
        # Not guaranteed, but with these seeds they differ
        assert ids1 != ids2

    def test_special_events_drawn_from_pool_of_16(self):
        all_ids = {d["id"] for d in SPECIAL_EVENT_DEFS}
        assert len(all_ids) == 16
        mgr = EventManager(seed=42)
        for ev in mgr.special_events:
            assert ev.id in all_ids


class TestEventCanOnlyBeClaimedOnce:
    def test_basic_event_single_claim(self):
        p1 = _make_player("Alice")
        p2 = _make_player("Bob")
        p1.city = [Courthouse(), Judge(), Innkeeper()]
        p2.city = [Courthouse(), Judge(), Innkeeper()]
        mgr = EventManager(seed=42)

        assert mgr.claim_event("basic_governance", str(p1.id)) is True
        assert mgr.claim_event("basic_governance", str(p2.id)) is False

    def test_special_event_single_claim(self):
        p1 = _make_player("Alice")
        p2 = _make_player("Bob")
        mgr = EventManager(seed=None)
        wedding_def = next(d for d in SPECIAL_EVENT_DEFS if d["id"] == "se_brilliant_wedding")
        mgr.special_events = [SpecialEvent(**wedding_def)]

        p1.city = [Harvester(), Gatherer()]
        p2.city = [Harvester(), Gatherer()]
        assert mgr.claim_event("se_brilliant_wedding", str(p1.id)) is True
        assert mgr.claim_event("se_brilliant_wedding", str(p2.id)) is False


class TestToGameStateDicts:
    def test_export_to_dicts(self):
        mgr = EventManager(seed=42)
        mgr.claim_event("basic_governance", "player1")
        basic_d, special_d = mgr.to_game_state_dicts()

        assert "basic_governance" in basic_d
        assert basic_d["basic_governance"]["claimed_by"] == "player1"
        assert basic_d["basic_governance"]["points"] == 3

        assert len(special_d) == 4
        for eid, edata in special_d.items():
            assert "points" in edata
            assert "required_cards" in edata
