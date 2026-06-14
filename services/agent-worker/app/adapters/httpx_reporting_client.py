"""HTTP client for reporting-service with timeout + bounded retries.

Auth carries two identities, same pattern as admin-web's clients:
- Authorization: Bearer <token> — fetched per request from the injected
  token provider (Zitadel client-credentials, cached until near expiry),
  which reporting-service resolves to an admin actor.
- X-Serverless-Authorization: Google-signed ID token from the metadata
  server — lets the call through Cloud Run IAM on the private service.
  Off GCP the provider returns None and the header is omitted.

Retries: transport errors and 5xx are retried twice with backoff (the
notifier-retry debt item, solved from the start here); 4xx is a
permanent error and fails immediately.
"""
from __future__ import annotations

import time
from datetime import date
from typing import Callable

import httpx

from app.domain.errors import JobFailed

IdTokenProvider = Callable[[str], "str | None"]
TokenProvider = Callable[[], str]

_ATTEMPTS = 3


class HttpxReportingClient:
    def __init__(
        self,
        base_url: str,
        token_provider: TokenProvider,
        http_client: httpx.Client | None = None,
        id_token_provider: IdTokenProvider | None = None,
        retry_wait_seconds: float = 0.5,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token_provider = token_provider
        self._http = http_client or httpx.Client(base_url=self._base_url, timeout=10.0)
        self._id_token_provider = id_token_provider
        self._retry_wait = retry_wait_seconds

    def _headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token_provider()}"}
        if self._id_token_provider is not None:
            id_token = self._id_token_provider(self._base_url)
            if id_token:
                headers["X-Serverless-Authorization"] = f"Bearer {id_token}"
        return headers

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(_ATTEMPTS):
            if attempt:
                time.sleep(self._retry_wait * (2 ** (attempt - 1)))
            try:
                response = self._http.request(
                    method, path, headers=self._headers(), **kwargs
                )
            except httpx.HTTPError as exc:
                last_error = exc
                continue
            if response.status_code >= 500:
                last_error = JobFailed(f"{path} -> {response.status_code}")
                continue
            if response.status_code >= 400:
                raise JobFailed(f"{path} -> {response.status_code}")
            return response
        raise JobFailed(f"{path} failed after {_ATTEMPTS} attempts: {last_error}")

    def export_activities(self, start: date, end: date) -> list[dict]:
        response = self._request(
            "GET",
            "/activities/export/period",
            params={"start": start.isoformat(), "end": end.isoformat()},
        )
        return response.json()

    def generate_monthly(
        self, period: str, activities: list[dict], finance: dict
    ) -> str:
        response = self._request(
            "POST",
            "/reports/monthly",
            json={"period": period, "activities": activities, "finance": finance},
        )
        return response.json()["report_id"]
