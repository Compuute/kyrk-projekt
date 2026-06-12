"""Service-to-service identity: outbound calls to private Cloud Run
services must carry a Google-signed ID token in X-Serverless-Authorization
(checked by Cloud Run IAM) alongside the user's bearer in Authorization
(checked by the downstream app)."""
from __future__ import annotations

import httpx
import pytest

from app.adapters.httpx_sunday_school import HttpxSundaySchoolClient


class _Resp:
    status_code = 200

    @staticmethod
    def json():
        return {
            "attendance_id": "a1",
            "group_id": "g1",
            "date": "2026-06-14",
            "participants_total": 1,
            "age_band_counts": {"7-12": 1},
        }


def test_outbound_call_carries_both_identities(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return _Resp()

    monkeypatch.setattr(httpx, "post", fake_post)
    client = HttpxSundaySchoolClient(
        base_url="https://membership.example",
        id_token_provider=lambda audience: f"gid-for-{audience}",
    )
    client.record_attendance("zitadel-token", "g1", "2026-06-14", ["e1"])

    assert captured["headers"]["Authorization"] == "Bearer zitadel-token"
    assert (
        captured["headers"]["X-Serverless-Authorization"]
        == "Bearer gid-for-https://membership.example"
    )


def test_outbound_call_works_without_provider(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _Resp()

    monkeypatch.setattr(httpx, "post", fake_post)
    client = HttpxSundaySchoolClient(base_url="https://membership.example")
    client.record_attendance("zitadel-token", "g1", "2026-06-14", ["e1"])

    assert "X-Serverless-Authorization" not in captured["headers"]


def test_provider_failure_does_not_break_the_call(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return _Resp()

    def broken_provider(audience):
        return None

    monkeypatch.setattr(httpx, "post", fake_post)
    client = HttpxSundaySchoolClient(
        base_url="https://membership.example", id_token_provider=broken_provider
    )
    result = client.record_attendance("t", "g1", "2026-06-14", ["e1"])
    assert result.attendance_id == "a1"
