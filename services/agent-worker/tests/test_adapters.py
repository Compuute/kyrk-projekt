"""Adapter tests: httpx_reporting_client (mock transport), firestore_audit_log
(mocked client) and in_memory_audit_log semantics."""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import httpx
import pytest

from app.adapters.firestore_audit_log import FirestoreAuditLog
from app.adapters.httpx_reporting_client import HttpxReportingClient
from app.adapters.in_memory_audit_log import InMemoryAuditLog
from app.domain.errors import JobFailed
from app.domain.models import AuditEvent, JobStatus


def _event(message_id="m-1"):
    return AuditEvent(
        message_id=message_id,
        job="monthly-report",
        status=JobStatus.SUCCEEDED,
        agent="report-agent",
        created_at=datetime(2026, 6, 12, tzinfo=timezone.utc),
    )


# ------------------------------------------------------------- in-memory audit


def test_in_memory_audit_seen_only_counts_completed():
    audit = InMemoryAuditLog()
    assert audit.seen("m-1") is False
    audit.record(_event("m-1"))
    assert audit.seen("m-1") is True


# ------------------------------------------------------------ firestore audit


def test_firestore_audit_record_writes_doc_keyed_by_message_id():
    client = MagicMock()
    audit = FirestoreAuditLog(client=client)
    audit.record(_event("m-7"))
    client.collection.assert_called_with("audit_events")
    doc_id = client.collection.return_value.document.call_args[0][0]
    assert "m-7" in doc_id
    doc = client.collection.return_value.document.return_value.set.call_args[0][0]
    assert doc["status"] == "succeeded"
    assert doc["agent"] == "report-agent"


def test_firestore_audit_seen_checks_success_doc():
    client = MagicMock()
    snap = client.collection.return_value.document.return_value.get.return_value
    snap.exists = True
    audit = FirestoreAuditLog(client=client)
    assert audit.seen("m-7") is True
    snap.exists = False
    assert audit.seen("m-8") is False


# ------------------------------------------------------- httpx reporting client


def _client_with(handler) -> HttpxReportingClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="http://reporting")
    return HttpxReportingClient(
        base_url="http://reporting",
        token_provider=lambda: "agent-token",
        http_client=http,
        retry_wait_seconds=0,
    )


def test_export_and_generate_happy_path():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen[request.url.path] = request
        if request.url.path == "/activities/export/period":
            assert request.url.params["start"] == "2026-05-01"
            assert request.url.params["end"] == "2026-05-31"
            return httpx.Response(200, json=[{"activity_type": "CODING"}])
        if request.url.path == "/reports/monthly":
            return httpx.Response(201, json={"report_id": "r-1", "kind": "monthly", "period": "2026-05", "payload": {}})
        return httpx.Response(404)

    client = _client_with(handler)
    acts = client.export_activities(date(2026, 5, 1), date(2026, 5, 31))
    assert acts == [{"activity_type": "CODING"}]
    report_id = client.generate_monthly("2026-05", acts, {})
    assert report_id == "r-1"
    # Bearer token forwarded on both calls.
    for req in seen.values():
        assert req.headers["Authorization"] == "Bearer agent-token"


def test_5xx_is_retried_then_raises():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    client = _client_with(handler)
    with pytest.raises(JobFailed):
        client.export_activities(date(2026, 5, 1), date(2026, 5, 31))
    assert calls["n"] == 3  # initial + 2 retries


def test_4xx_is_not_retried():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(403)

    client = _client_with(handler)
    with pytest.raises(JobFailed):
        client.generate_monthly("2026-05", [], {})
    assert calls["n"] == 1
