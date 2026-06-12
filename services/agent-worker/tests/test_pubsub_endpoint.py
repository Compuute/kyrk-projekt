"""Tests for the Pub/Sub push endpoint (routes_jobs).

Pub/Sub semantics drive the status codes: 2xx acks the message, anything
else makes Pub/Sub redeliver. Permanent failures (malformed envelope,
unknown job, duplicate) are therefore ACKED with 204 and recorded in the
audit log — only transient job failures return 500 to trigger a retry.
"""
from __future__ import annotations

import base64
import json

from app.domain.models import JobStatus


def _envelope(payload: dict, message_id: str = "m-1") -> dict:
    return {
        "message": {
            "data": base64.b64encode(json.dumps(payload).encode()).decode(),
            "messageId": message_id,
        },
        "subscription": "projects/p/subscriptions/agent-jobs",
    }


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_monthly_report_job_is_acked_and_audited(client, audit_log, reporting):
    r = client.post("/pubsub", json=_envelope({"job": "monthly-report", "period": "2026-05"}))
    assert r.status_code == 204
    assert len(reporting.generated) == 1
    events = audit_log.events
    assert len(events) == 1
    assert events[0].status is JobStatus.SUCCEEDED
    assert events[0].message_id == "m-1"


def test_unknown_job_is_acked_not_retried(client, audit_log, reporting):
    r = client.post("/pubsub", json=_envelope({"job": "world-domination"}))
    assert r.status_code == 204
    assert reporting.generated == []
    assert audit_log.events[0].status is JobStatus.REJECTED


def test_malformed_envelope_is_acked_not_retried(client, audit_log):
    r = client.post("/pubsub", json={"not": "an envelope"})
    assert r.status_code == 204
    assert audit_log.events[0].status is JobStatus.REJECTED


def test_garbage_data_field_is_acked_not_retried(client, audit_log):
    r = client.post(
        "/pubsub",
        json={"message": {"data": "inte-base64!!!", "messageId": "m-9"}},
    )
    assert r.status_code == 204
    assert audit_log.events[0].status is JobStatus.REJECTED


def test_failing_job_returns_500_for_redelivery(client, audit_log, reporting):
    reporting.fail_next = True
    r = client.post("/pubsub", json=_envelope({"job": "monthly-report", "period": "2026-05"}))
    assert r.status_code == 500
    assert audit_log.events[0].status is JobStatus.FAILED


def test_redelivered_message_is_not_run_twice(client, audit_log, reporting):
    env = _envelope({"job": "monthly-report", "period": "2026-05"}, message_id="dup-1")
    assert client.post("/pubsub", json=env).status_code == 204
    assert client.post("/pubsub", json=env).status_code == 204
    assert len(reporting.generated) == 1  # second delivery deduped
    statuses = [e.status for e in audit_log.events]
    assert statuses == [JobStatus.SUCCEEDED, JobStatus.SKIPPED]
