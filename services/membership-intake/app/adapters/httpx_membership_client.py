"""Production HTTP client for membership-service.

Lazy-imports httpx so tests that never instantiate this adapter don't
require the library. Production wiring in deps.py picks this adapter
when ADAPTER_MODE=production.
"""
from __future__ import annotations

from dataclasses import asdict

from app.domain.errors import DownstreamFailure
from app.ports.membership_client import (
    CreateMemberRequest,
    CreateMemberResult,
)


class HttpxMembershipClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def create_member(
        self,
        actor_token: str,
        request: CreateMemberRequest,
    ) -> CreateMemberResult:
        import httpx  # lazy — keeps tests dependency-free

        headers = {"Authorization": f"Bearer {actor_token}"}
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
