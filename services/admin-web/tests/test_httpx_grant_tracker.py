"""Tests for HttpxGrantTracker (proxies grants to membership-service)."""
from __future__ import annotations

import httpx
import pytest

from app.adapters.httpx_grant_tracker import HttpxGrantTracker
from app.ports.client_errors import ClientError
from app.ports.grant_tracker import GrantApplication


class _Resp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def _tracker():
    return HttpxGrantTracker(base_url="https://ms.example", token="tok")


def test_list_applications_parses_and_sends_token(monkeypatch):
    seen = {}

    def fake_get(url, headers=None, timeout=None):
        seen["url"] = url
        seen["auth"] = headers["Authorization"]
        return _Resp(200, [{"grant_id": "g1", "church_id": "c1", "project_name": "P"}])

    monkeypatch.setattr(httpx, "get", fake_get)
    apps = _tracker().list_applications("c1")
    assert len(apps) == 1 and apps[0].grant_id == "g1"
    assert seen["url"] == "https://ms.example/grants"
    assert seen["auth"] == "Bearer tok"


def test_get_application_404_returns_none(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(404, text="nope"))
    assert _tracker().get_application("c1", "g1") is None


def test_get_application_error_raises(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(500, text="boom"))
    with pytest.raises(ClientError):
        _tracker().get_application("c1", "g1")


def test_save_application_posts_body(monkeypatch):
    seen = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        seen["url"] = url
        seen["body"] = json
        return _Resp(201, json)

    monkeypatch.setattr(httpx, "post", fake_post)
    _tracker().save_application(
        GrantApplication(grant_id="g1", church_id="c1", project_name="Proj", budget_amount=1000.0)
    )
    assert seen["url"] == "https://ms.example/grants"
    assert seen["body"]["grant_id"] == "g1"
    assert seen["body"]["project_name"] == "Proj"


def test_save_application_error_raises(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(400, text="church ID mismatch"))
    with pytest.raises(ClientError):
        _tracker().save_application(GrantApplication(grant_id="g1", church_id="c1"))
