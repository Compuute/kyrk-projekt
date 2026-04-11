"""Notifier port. n8n webhook in production; in-memory for tests."""
from __future__ import annotations

from typing import Protocol

from app.domain.models import IntakeSubmission


class NotifierPort(Protocol):
    def notify_new_pending(self, submission: IntakeSubmission) -> None: ...
