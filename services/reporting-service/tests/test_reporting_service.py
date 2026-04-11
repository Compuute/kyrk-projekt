import pytest

from app.domain.errors import NotAuthorized, PIIRejected, ReportNotFound
from app.domain.models import Actor, ReportKind, Role
from app.services.reporting_service import GenerateReportInput


def _actor(role: Role, church_id: str = "c1") -> Actor:
    return Actor(user_id="u1", church_id=church_id, role=role)


def _activities():
    return [
        {
            "activity_type": "youth_tech",
            "date": "2025-06-01",
            "location": "Storgatan 1",
            "funding_tag": "arvsfonden",
            "participants_total": 20,
            "age_band_counts": {"0-6": 0, "7-12": 5, "13-17": 10, "18-25": 5, "26+": 0},
        },
        {
            "activity_type": "coding",
            "date": "2025-06-10",
            "location": "Storgatan 1",
            "funding_tag": "kommunala",
            "participants_total": 10,
            "age_band_counts": {"0-6": 0, "7-12": 10, "13-17": 0, "18-25": 0, "26+": 0},
        },
    ]


def _finance():
    return {"operating_cost": 30000, "grants": 20000, "own_contribution": 10000}


def test_monthly_computes_aggregates(service):
    report = service.generate(
        _actor(Role.ADMIN),
        GenerateReportInput(
            kind=ReportKind.MONTHLY,
            period="2025-06",
            activities=_activities(),
            finance=_finance(),
        ),
    )
    p = report.payload
    assert p["participants_total"] == 30
    assert p["participants_by_type"]["youth_tech"] == 20
    assert p["participants_by_type"]["coding"] == 10
    assert p["participants_by_age_band"]["7-12"] == 15
    assert p["cost_per_participant"] == 1000.0
    assert p["grant_leverage_ratio"] == 2.0


def test_pii_in_activities_rejected(service):
    acts = _activities()
    acts[0]["first_name"] = "Anna"
    with pytest.raises(PIIRejected):
        service.generate(
            _actor(Role.ADMIN),
            GenerateReportInput(
                kind=ReportKind.MONTHLY,
                period="2025-06",
                activities=acts,
                finance=_finance(),
            ),
        )


def test_pii_in_finance_rejected(service):
    fin = dict(_finance())
    fin["email"] = "a@b.se"
    with pytest.raises(PIIRejected):
        service.generate(
            _actor(Role.ADMIN),
            GenerateReportInput(
                kind=ReportKind.MONTHLY,
                period="2025-06",
                activities=_activities(),
                finance=fin,
            ),
        )


def test_viewer_cannot_generate(service):
    with pytest.raises(NotAuthorized):
        service.generate(
            _actor(Role.VIEWER),
            GenerateReportInput(
                kind=ReportKind.MONTHLY,
                period="2025-06",
                activities=_activities(),
                finance=_finance(),
            ),
        )


def test_get_scoped_by_church(service):
    r = service.generate(
        _actor(Role.ADMIN, "c1"),
        GenerateReportInput(
            kind=ReportKind.MONTHLY,
            period="2025-06",
            activities=_activities(),
            finance=_finance(),
        ),
    )
    with pytest.raises(ReportNotFound):
        service.get(_actor(Role.VIEWER, "c2"), r.report_id)


def test_board_export_shape_is_openclaw_ready(service):
    r = service.generate(
        _actor(Role.ADMIN),
        GenerateReportInput(
            kind=ReportKind.BOARD_EXPORT,
            period="2025-Q2",
            activities=_activities(),
            finance=_finance(),
        ),
    )
    assert r.payload["openclaw_ready"] is True
    assert "summary" in r.payload
    assert "breakdown" in r.payload
