"""Zitadel client-credentials token provider.

A static token secret expires within hours — useless for the monthly
schedule. This adapter exchanges the agent's machine-user client id +
secret for a fresh access token at the issuer's token endpoint and
caches it until shortly before expiry, so every job runs with a valid
token without any manual rotation.

The scope is configurable (AGENT_TOKEN_SCOPE): which claims Zitadel puts
in the token (project roles, audience) depends on scope, and the exact
strings are environment-specific — see services/agent-worker/README.md.
"""
from __future__ import annotations

import time
from typing import Callable

import httpx

from app.domain.errors import JobFailed

_DEFAULT_SCOPE = "openid urn:zitadel:iam:org:projects:roles"
# Refresh this many seconds before the token actually expires.
_EXPIRY_MARGIN_SECONDS = 60


class ZitadelTokenProvider:
    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        client_secret: str,
        scope: str = _DEFAULT_SCOPE,
        http_client: httpx.Client | None = None,
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        self._token_url = f"{issuer_url.rstrip('/')}/oauth/v2/token"
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._http = http_client or httpx.Client(timeout=10.0)
        self._now_fn = now_fn
        self._cached_token = ""
        self._expires_at = 0.0

    def token(self) -> str:
        now = self._now_fn()
        if self._cached_token and now < self._expires_at:
            return self._cached_token

        try:
            response = self._http.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": self._scope,
                },
            )
        except httpx.HTTPError as exc:
            raise JobFailed(f"token fetch failed: {exc}") from exc
        if response.status_code != 200:
            raise JobFailed(f"token endpoint -> {response.status_code}")

        payload = response.json()
        self._cached_token = payload["access_token"]
        self._expires_at = (
            now + float(payload.get("expires_in", 0)) - _EXPIRY_MARGIN_SECONDS
        )
        return self._cached_token
