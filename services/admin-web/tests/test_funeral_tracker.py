"""TDD tests for funeral/hemtransport case management.

Tests cover:
1. Domain model (FuneralCase, pricing, checklist)
2. Fake adapter (CRUD operations)
3. Routes (list, create, detail, update, checklist, status)
4. Repatriation-specific workflow
5. Memorial page
6. Grief calendar
"""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_funeral_tracker import FakeFuneralTracker
from app.ports.funeral_tracker import (
    CHECKLIST_ITEMS_REPATRIATION,
    CHECKLIST_ITEMS_SWEDEN,
    FUNERAL_STATUSES,
    MEMORIAL_DAYS,
    FuneralCase,
    build_checklist,
    calculate_price,
    checklist_progress,
)


# ================================================================
# Domain model tests
# ================================================================


class TestFuneralCaseModel:
    def test_default_status_is_registered(self):
        case = FuneralCase(case_id="f1", church_id="c1")
        assert case.status == "registered"

    def test_repatriation_defaults_to_false(self):
        case = FuneralCase(case_id="f1", church_id="c1")
        assert case.repatriation is False

    def test_checklist_defaults_to_empty_dict(self):
        case = FuneralCase(case_id="f1", church_id="c1")
        assert case.checklist == {}


class TestPricing:
    def test_enkel_no_repatriation(self):
        pkg, rep, total = calculate_price("enkel", False)
        assert pkg == 19_000
        assert rep == 0
        assert total == 19_000

    def test_standard_no_repatriation(self):
        pkg, rep, total = calculate_price("standard", False)
        assert pkg == 28_000
        assert total == 28_000

    def test_komplett_no_repatriation(self):
        pkg, rep, total = calculate_price("komplett", False)
        assert pkg == 35_000
        assert total == 35_000

    def test_standard_with_repatriation(self):
        pkg, rep, total = calculate_price("standard", True)
        assert pkg == 28_000
        assert rep == 65_000
        assert total == 93_000

    def test_unknown_package_falls_back_to_standard(self):
        pkg, rep, total = calculate_price("unknown", False)
        assert pkg == 28_000


class TestChecklist:
    def test_sweden_only_checklist(self):
        cl = build_checklist(repatriation=False)
        assert len(cl) == len(CHECKLIST_ITEMS_SWEDEN)
        assert all(v is False for v in cl.values())
        assert "rep_export_permit" not in cl

    def test_repatriation_checklist_includes_extra_items(self):
        cl = build_checklist(repatriation=True)
        expected = len(CHECKLIST_ITEMS_SWEDEN) + len(CHECKLIST_ITEMS_REPATRIATION)
        assert len(cl) == expected
        assert "rep_export_permit" in cl
        assert "rep_zinc_coffin" in cl

    def test_checklist_progress_all_unchecked(self):
        cl = build_checklist(repatriation=False)
        done, total = checklist_progress(cl)
        assert done == 0
        assert total == len(CHECKLIST_ITEMS_SWEDEN)

    def test_checklist_progress_partial(self):
        cl = build_checklist(repatriation=False)
        cl["doc_death_cert"] = True
        cl["doc_death_report"] = True
        done, total = checklist_progress(cl)
        assert done == 2

    def test_checklist_progress_all_done(self):
        cl = build_checklist(repatriation=False)
        for k in cl:
            cl[k] = True
        done, total = checklist_progress(cl)
        assert done == total


class TestMemorialDays:
    def test_memorial_days_are_defined(self):
        assert len(MEMORIAL_DAYS) == 6

    def test_day_3_is_salist(self):
        assert MEMORIAL_DAYS[0] == (3, "ሳልስት", "Salist")

    def test_day_40_is_arba(self):
        assert MEMORIAL_DAYS[3] == (40, "አርባ", "Arba")


class TestStatuses:
    def test_all_statuses_defined(self):
        assert "registered" in FUNERAL_STATUSES
        assert "completed" in FUNERAL_STATUSES
        assert "repatriation" in FUNERAL_STATUSES
        assert "closed" in FUNERAL_STATUSES


# ================================================================
# Fake adapter tests
# ================================================================


class TestFakeFuneralTracker:
    def test_list_empty(self):
        tracker = FakeFuneralTracker()
        assert tracker.list_cases("c1") == []

    def test_save_and_get(self):
        tracker = FakeFuneralTracker()
        case = FuneralCase(case_id="f1", church_id="c1", deceased_name="Test")
        tracker.save_case(case)
        result = tracker.get_case("c1", "f1")
        assert result is not None
        assert result.deceased_name == "Test"

    def test_list_filters_by_church(self):
        tracker = FakeFuneralTracker()
        tracker.save_case(FuneralCase(case_id="f1", church_id="c1"))
        tracker.save_case(FuneralCase(case_id="f2", church_id="c2"))
        assert len(tracker.list_cases("c1")) == 1
        assert len(tracker.list_cases("c2")) == 1

    def test_delete(self):
        tracker = FakeFuneralTracker()
        tracker.save_case(FuneralCase(case_id="f1", church_id="c1"))
        tracker.delete_case("c1", "f1")
        assert tracker.get_case("c1", "f1") is None

    def test_seed(self):
        tracker = FakeFuneralTracker()
        case = FuneralCase(case_id="f1", church_id="c1", status="completed")
        tracker.seed(case)
        assert tracker.get_case("c1", "f1").status == "completed"


# ================================================================
# Route tests
# ================================================================


@pytest.fixture
def funeral_tracker() -> FakeFuneralTracker:
    return FakeFuneralTracker()


@pytest.fixture
def seeded_case(funeral_tracker) -> FuneralCase:
    case = FuneralCase(
        case_id="f-001",
        church_id="c1",
        status="registered",
        deceased_name="Abebe Tadesse",
        deceased_name_am="አበበ ታደሰ",
        date_of_death="2026-06-01",
        contact_person="Meron Tadesse",
        contact_phone="070-123-4567",
        package="standard",
        repatriation=False,
        checklist=build_checklist(repatriation=False),
        created_at=datetime(2026, 6, 1, 10, 0),
    )
    case.package_price, case.repatriation_price, case.total_price = calculate_price(
        case.package, case.repatriation
    )
    funeral_tracker.seed(case)
    return case


@pytest.fixture
def seeded_repatriation_case(funeral_tracker) -> FuneralCase:
    case = FuneralCase(
        case_id="f-002",
        church_id="c1",
        status="registered",
        deceased_name="Kidane Gebre",
        deceased_name_am="ኪዳነ ገብረ",
        date_of_death="2026-06-03",
        contact_person="Sara Gebre",
        package="komplett",
        repatriation=True,
        repatriation_destination="ethiopia",
        checklist=build_checklist(repatriation=True),
        created_at=datetime(2026, 6, 3, 14, 0),
    )
    case.package_price, case.repatriation_price, case.total_price = calculate_price(
        case.package, case.repatriation
    )
    funeral_tracker.seed(case)
    return case


@pytest.fixture
def funeral_client(client, funeral_tracker) -> TestClient:
    from app.api import deps
    app = client.app
    app.dependency_overrides[deps.get_funeral_tracker] = lambda: funeral_tracker
    return client


@pytest.fixture
def authed_funeral_client(funeral_client) -> TestClient:
    funeral_client.cookies.set("kyrk_session", "u-admin:c1:admin")
    return funeral_client


class TestFuneralRoutes:
    def test_list_requires_auth(self, funeral_client):
        resp = funeral_client.get("/funerals")
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]

    def test_list_empty(self, authed_funeral_client):
        resp = authed_funeral_client.get("/funerals")
        assert resp.status_code == 200
        assert "Inga ärenden" in resp.text or "ärenden" in resp.text.lower()

    def test_list_with_cases(self, authed_funeral_client, seeded_case):
        resp = authed_funeral_client.get("/funerals")
        assert resp.status_code == 200
        assert "Abebe Tadesse" in resp.text

    def test_new_form(self, authed_funeral_client):
        resp = authed_funeral_client.get("/funerals/new")
        assert resp.status_code == 200
        assert "Nytt begravningsärende" in resp.text

    def test_create_case(self, authed_funeral_client, funeral_tracker):
        resp = authed_funeral_client.post(
            "/funerals/new",
            data={
                "deceased_name": "Test Person",
                "deceased_name_am": "ተስት ሰው",
                "date_of_death": "2026-06-05",
                "contact_person": "Contact",
                "contact_phone": "070-000-0000",
                "package": "standard",
            },
        )
        assert resp.status_code == 303
        cases = funeral_tracker.list_cases("c1")
        assert len(cases) == 1
        assert cases[0].deceased_name == "Test Person"
        assert cases[0].package_price == 28_000
        assert cases[0].total_price == 28_000

    def test_create_repatriation_case(self, authed_funeral_client, funeral_tracker):
        resp = authed_funeral_client.post(
            "/funerals/new",
            data={
                "deceased_name": "Repatriation Test",
                "deceased_name_am": "ተስት",
                "date_of_death": "2026-06-05",
                "contact_person": "Contact",
                "contact_phone": "070-000-0000",
                "package": "komplett",
                "repatriation": "on",
                "repatriation_destination": "ethiopia",
            },
        )
        assert resp.status_code == 303
        cases = funeral_tracker.list_cases("c1")
        assert len(cases) == 1
        assert cases[0].repatriation is True
        assert cases[0].repatriation_price == 65_000
        assert cases[0].total_price == 100_000
        assert "rep_export_permit" in cases[0].checklist

    def test_detail_page(self, authed_funeral_client, seeded_case):
        resp = authed_funeral_client.get("/funerals/f-001")
        assert resp.status_code == 200
        assert "Abebe Tadesse" in resp.text
        assert "28" in resp.text

    def test_detail_not_found(self, authed_funeral_client):
        resp = authed_funeral_client.get("/funerals/nonexistent")
        assert resp.status_code == 303

    def test_update_status(self, authed_funeral_client, seeded_case, funeral_tracker):
        resp = authed_funeral_client.post(
            "/funerals/f-001/status",
            data={"status": "documents"},
        )
        assert resp.status_code == 303
        case = funeral_tracker.get_case("c1", "f-001")
        assert case.status == "documents"

    def test_update_checklist(self, authed_funeral_client, seeded_case, funeral_tracker):
        resp = authed_funeral_client.post(
            "/funerals/f-001/checklist",
            data={"doc_death_cert": "on", "doc_death_report": "on"},
        )
        assert resp.status_code == 303
        case = funeral_tracker.get_case("c1", "f-001")
        assert case.checklist["doc_death_cert"] is True
        assert case.checklist["doc_death_report"] is True
        assert case.checklist["doc_burial_permit"] is False

    def test_repatriation_detail_shows_extra_checklist(
        self, authed_funeral_client, seeded_repatriation_case
    ):
        resp = authed_funeral_client.get("/funerals/f-002")
        assert resp.status_code == 200
        assert "Zinkkista" in resp.text or "zinkkista" in resp.text.lower()
        assert "100" in resp.text

    def test_update_notes(self, authed_funeral_client, seeded_case, funeral_tracker):
        resp = authed_funeral_client.post(
            "/funerals/f-001/notes",
            data={"notes": "Familjen vill ha extra blommor"},
        )
        assert resp.status_code == 303
        case = funeral_tracker.get_case("c1", "f-001")
        assert "extra blommor" in case.notes

    def test_memorial_save(self, authed_funeral_client, seeded_case, funeral_tracker):
        resp = authed_funeral_client.post(
            "/funerals/f-001/memorial",
            data={
                "memorial_text_sv": "Vila i frid, Abebe.",
                "memorial_text_am": "በሰላም ዕረፍ አበበ።",
            },
        )
        assert resp.status_code == 303
        case = funeral_tracker.get_case("c1", "f-001")
        assert "Vila i frid" in case.memorial_text_sv
        assert "በሰላም" in case.memorial_text_am


class TestDashboardIncludesFunerals:
    def test_dashboard_shows_funeral_count(self, authed_funeral_client, seeded_case):
        resp = authed_funeral_client.get("/")
        assert resp.status_code == 200
        assert "begravning" in resp.text.lower() or "funeral" in resp.text.lower()
