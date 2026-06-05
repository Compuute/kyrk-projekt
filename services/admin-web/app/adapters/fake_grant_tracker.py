"""In-memory fake grant tracker for tests and local dev."""
from __future__ import annotations

from app.ports.grant_tracker import GrantApplication


class FakeGrantTracker:
    def __init__(self) -> None:
        self._store: dict[str, GrantApplication] = {}

    @staticmethod
    def _key(church_id: str, grant_id: str) -> str:
        return f"{church_id}::{grant_id}"

    def seed(self, app: GrantApplication) -> None:
        self._store[self._key(app.church_id, app.grant_id)] = app

    def list_applications(self, church_id: str) -> list[GrantApplication]:
        return [a for a in self._store.values() if a.church_id == church_id]

    def get_application(self, church_id: str, grant_id: str) -> GrantApplication | None:
        return self._store.get(self._key(church_id, grant_id))

    def save_application(self, app: GrantApplication) -> None:
        self._store[self._key(app.church_id, app.grant_id)] = app
