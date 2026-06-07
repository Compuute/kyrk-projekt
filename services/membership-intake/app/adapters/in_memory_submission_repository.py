from __future__ import annotations

from app.domain.models import IntakeSubmission, SubmissionStatus


class InMemorySubmissionRepository:
    def __init__(self) -> None:
        self._items: dict[str, IntakeSubmission] = {}

    def add(self, submission: IntakeSubmission) -> None:
        self._items[submission.submission_id] = submission

    def get(self, submission_id: str) -> IntakeSubmission | None:
        return self._items.get(submission_id)

    def update(self, submission: IntakeSubmission) -> None:
        self._items[submission.submission_id] = submission

    def list_pending(self, church_id: str) -> list[IntakeSubmission]:
        return [
            s for s in self._items.values()
            if s.church_id == church_id and s.status is SubmissionStatus.PENDING
        ]

    def find_by_personal_number(self, personal_number: str) -> IntakeSubmission | None:
        clean = personal_number.replace("-", "").replace(" ", "")
        for s in self._items.values():
            if s.personal_number.replace("-", "").replace(" ", "") == clean:
                return s
        return None
