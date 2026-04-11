"""HTTP notifier — fires an n8n webhook when a new pending submission arrives.

Payload contains ONLY: submission_id, church_id, received_at, status.
No identity fields. The admin notification is a pointer, not the data —
a reviewer opens the admin UI to see the submission details under a
real session.
"""
from __future__ import annotations

from app.domain.models import IntakeSubmission


class HttpNotifier:
    def __init__(self, webhook_url: str, timeout_seconds: float = 5.0) -> None:
        self._webhook_url = webhook_url
        self._timeout = timeout_seconds

    def notify_new_pending(self, submission: IntakeSubmission) -> None:
        import httpx  # pragma: no cover — lazy

        payload = {
            "submission_id": submission.submission_id,
            "church_id": submission.church_id,
            "received_at": submission.received_at.isoformat(),
            "status": submission.status.value,
        }
        try:
            httpx.post(self._webhook_url, json=payload, timeout=self._timeout)
        except httpx.HTTPError:
            # Notifier failures must NOT break the intake flow. The
            # submission is stored; the notification can be retried by
            # n8n's own retry logic or re-fired manually.
            pass
