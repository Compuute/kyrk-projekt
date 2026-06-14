"""Tests for the Zitadel client-credentials token provider.

A static token secret expires within hours — useless for a monthly
schedule. The provider fetches a fresh access token via the OAuth2
client_credentials grant and caches it until shortly before expiry.
References adapter module: zitadel_token_provider.
"""
from __future__ import annotations

import httpx
import pytest

from app.adapters.zitadel_token_provider import ZitadelTokenProvider
from app.domain.errors import JobFailed


def _provider(handler, now=None, **kwargs) -> ZitadelTokenProvider:
    clock = now or {"t": 1_000_000.0}
    transport = httpx.MockTransport(handler)
    return ZitadelTokenProvider(
        issuer_url="https://auth.example",
        client_id="cid",
        client_secret="hemlis",
        http_client=httpx.Client(transport=transport),
        now_fn=lambda: clock["t"],
        **kwargs,
    )


def test_fetches_token_with_client_credentials_grant():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"access_token": "tok-1", "expires_in": 3600})

    provider = _provider(handler)
    assert provider.token() == "tok-1"
    assert captured["url"] == "https://auth.example/oauth/v2/token"
    assert "grant_type=client_credentials" in captured["body"]
    assert "client_id=cid" in captured["body"]
    assert "client_secret=hemlis" in captured["body"]
    assert "scope=" in captured["body"]


def test_scope_is_configurable():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})

    provider = _provider(handler, scope="openid custom:scope")
    provider.token()
    assert "custom%3Ascope" in captured["body"] or "custom:scope" in captured["body"]


def test_token_is_cached_until_near_expiry():
    clock = {"t": 1_000_000.0}
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200, json={"access_token": f"tok-{calls['n']}", "expires_in": 3600}
        )

    provider = _provider(handler, now=clock)
    assert provider.token() == "tok-1"
    clock["t"] += 600  # well within lifetime
    assert provider.token() == "tok-1"
    assert calls["n"] == 1
    clock["t"] += 3000  # 3600s total elapsed > 3600 - 60s margin
    assert provider.token() == "tok-2"
    assert calls["n"] == 2


def test_http_error_raises_jobfailed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_client"})

    provider = _provider(handler)
    with pytest.raises(JobFailed):
        provider.token()


def test_transport_error_raises_jobfailed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    provider = _provider(handler)
    with pytest.raises(JobFailed):
        provider.token()


def test_failed_fetch_is_not_cached():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"access_token": "tok-ok", "expires_in": 3600})

    provider = _provider(handler)
    with pytest.raises(JobFailed):
        provider.token()
    assert provider.token() == "tok-ok"
