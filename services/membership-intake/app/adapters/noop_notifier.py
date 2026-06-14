"""No-op notifier — used in production when ADMIN_NOTIFY_WEBHOOK is unset.

Admin notifications are a non-critical side channel: a missing (or dead)
webhook must never break a member's intake submission. Pending submissions
are always visible in admin-web regardless of the webhook. Logs once so ops
can see that notifications are unconfigured.
"""
from __future__ import annotations

import logging

from app.domain.models import IntakeSubmission

logger = logging.getLogger("membership-intake.notifier")


class NoopNotifier:
    def __init__(self) -> None:
        self._warned = False

    def notify_new_pending(self, submission: IntakeSubmission) -> None:
        if not self._warned:
            logger.warning(
                "ADMIN_NOTIFY_WEBHOOK unset — admin notifications disabled "
                "(submissions still saved and visible in admin-web)"
            )
            self._warned = True
