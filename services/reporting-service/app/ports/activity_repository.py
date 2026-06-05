from __future__ import annotations

from datetime import date
from typing import Protocol

from app.domain.models import Activity


class ActivityRepository(Protocol):
    def add(self, activity: Activity) -> None: ...
    def get(self, church_id: str, activity_id: str) -> Activity | None: ...
    def list_in_period(
        self, church_id: str, start: date, end: date
    ) -> list[Activity]: ...
