"""In-memory funeral tracker for local dev and tests."""
from __future__ import annotations

from app.domain.models import FuneralCase


class InMemoryFuneralTracker:
    def __init__(self) -> None:
        self._store: dict[str, FuneralCase] = {}

    @staticmethod
    def _key(church_id: str, case_id: str) -> str:
        return f"{church_id}::{case_id}"

    def list_cases(self, church_id: str) -> list[FuneralCase]:
        return [c for c in self._store.values() if c.church_id == church_id]

    def get_case(self, church_id: str, case_id: str) -> FuneralCase | None:
        return self._store.get(self._key(church_id, case_id))

    def save_case(self, case: FuneralCase) -> None:
        self._store[self._key(case.church_id, case.case_id)] = case

    def delete_case(self, church_id: str, case_id: str) -> None:
        key = self._key(church_id, case_id)
        self._store.pop(key, None)
