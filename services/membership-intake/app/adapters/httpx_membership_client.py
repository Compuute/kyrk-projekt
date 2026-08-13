"""Production HTTP client for membership-service.

Lazy-imports httpx so tests that never instantiate this adapter don't
require the library. Production wiring in deps.py picks this adapter
when ADAPTER_MODE=production.
"""
from __future__ import annotations

from dataclasses import asdict

from app.domain.errors import DownstreamFailure, RateLimited
from app.ports.membership_client import (
    CreateMemberRequest,
    CreateMemberResult,
    PublicEnrollmentRequest,
)


class HttpxMembershipClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
        id_token_provider=None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        # Optional: mints a Google ID token for Cloud Run IAM. membership-service
        # is --no-allow-unauthenticated, so without this the forward gets a 403.
        # None off-GCP (local/tests) — the fake client is used there anyway.
        self._id_token_provider = id_token_provider

    def _serverless_headers(self) -> dict[str, str]:
        if self._id_token_provider is None:
            return {}
        token = self._id_token_provider(self._base_url)
        return {"X-Serverless-Authorization": f"Bearer {token}"} if token else {}

    def create_member(
        self,
        actor_token: str,
        request: CreateMemberRequest,
    ) -> CreateMemberResult:
        import httpx  # lazy — keeps tests dependency-free

        headers = {"Authorization": f"Bearer {actor_token}", **self._serverless_headers()}
        try:
            response = httpx.post(
                f"{self._base_url}/members",
                json=asdict(request),
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise DownstreamFailure(f"network error: {exc}") from exc

        if response.status_code != 201:
            raise DownstreamFailure(
                f"membership-service returned {response.status_code}: {response.text}"
            )
        data = response.json()
        return CreateMemberResult(member_id=data["member_id"])

    def create_public_enrollment(
        self,
        request: PublicEnrollmentRequest,
        client_ip: str,
    ) -> None:
        import httpx  # lazy — keeps tests dependency-free

        try:
            response = httpx.post(
                f"{self._base_url}/sunday-school/public/enrollments",
                json=asdict(request),
                headers={"X-Forwarded-For": client_ip, **self._serverless_headers()},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise DownstreamFailure(f"network error: {exc}") from exc

        if response.status_code == 202:
            return
        if response.status_code == 429:
            raise RateLimited("downstream rate limit")
        raise DownstreamFailure(
            f"membership-service returned {response.status_code}: {response.text}"
        )
