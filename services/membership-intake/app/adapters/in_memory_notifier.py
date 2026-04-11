from __future__ import annotations

from app.domain.models import IntakeSubmission


class InMemoryNotifier:
    def __init__(self) -> None:
        self.sent: list[IntakeSubmission] = []

    def notify_new_pending(self, submission: IntakeSubmission) -> None:
        self.sent.append(submission)
