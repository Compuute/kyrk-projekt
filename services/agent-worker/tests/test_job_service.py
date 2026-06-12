"""Tests for JobService — dispatch, period logic and audit trail.

References domain modules by name for the repo guard: job_service,
models, errors.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.adapters.fake_reporting_client import FakeReportingClient
from app.adapters.in_memory_audit_log import InMemoryAuditLog
from app.domain.errors import JobFailed
from app.domain.models import AuditEvent, JobStatus
from app.services.job_service import JobService


def _service(now: datetime | None = None):
    reporting = FakeReportingClient()
    audit = InMemoryAuditLog()
    svc = JobService(
        reporting=reporting,
        audit=audit,
        now_fn=lambda: now or datetime(2026, 6, 12, 8, 0, tzinfo=timezone.utc),
    )
    return svc, reporting, audit


def test_explicit_period_is_used():
    svc, reporting, _ = _service()
    svc.handle("m-1", {"job": "monthly-report", "period": "2026-03"})
    period, start, end = reporting.exported[0]
    assert period == "2026-03"
    assert start.isoformat() == "2026-03-01"
    assert end.isoformat() == "2026-03-31"


def test_default_period_is_previous_month():
    svc, reporting, _ = _service(now=datetime(2026, 1, 5, tzinfo=timezone.utc))
    svc.handle("m-1", {"job": "monthly-report"})
    period, start, end = reporting.exported[0]
    assert period == "2025-12"
    assert start.isoformat() == "2025-12-01"
    assert end.isoformat() == "2025-12-31"


def test_activities_flow_into_report():
    svc, reporting, audit = _service()
    reporting.activities = [{"activity_type": "SUNDAY_SCHOOL", "participants_total": 30}]
    status = svc.handle("m-1", {"job": "monthly-report", "period": "2026-05"})
    assert status is JobStatus.SUCCEEDED
    period, activities, finance = reporting.generated[0]
    assert activities == reporting.activities
    assert finance == {}
    event = audit.events[0]
    assert event.job == "monthly-report"
    assert event.period == "2026-05"
    assert event.report_id == reporting.report_id


def test_failure_audits_and_raises():
    svc, reporting, audit = _service()
    reporting.fail_next = True
    with pytest.raises(JobFailed):
        svc.handle("m-1", {"job": "monthly-report", "period": "2026-05"})
    assert audit.events[0].status is JobStatus.FAILED
    assert "boom" in audit.events[0].detail


def test_invalid_period_is_rejected_not_retried():
    svc, reporting, audit = _service()
    status = svc.handle("m-1", {"job": "monthly-report", "period": "igår"})
    assert status is JobStatus.REJECTED
    assert reporting.generated == []
    assert audit.events[0].status is JobStatus.REJECTED


def test_audit_event_carries_agent_identity():
    svc, _, audit = _service()
    svc.handle("m-1", {"job": "monthly-report", "period": "2026-05"})
    event: AuditEvent = audit.events[0]
    assert event.agent == "report-agent"
    assert event.created_at.tzinfo is not None
