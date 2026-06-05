from __future__ import annotations

from datetime import date

from app.domain.models import Activity


class InMemoryActivityRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], Activity] = {}

    def add(self, activity: Activity) -> None:
        self._items[(activity.church_id, activity.activity_id)] = activity

    def get(self, church_id: str, activity_id: str) -> Activity | None:
        return self._items.get((church_id, activity_id))

    def list_in_period(
        self, church_id: str, start: date, end: date
    ) -> list[Activity]:
        return [
            a for (c, _), a in self._items.items()
            if c == church_id and start <= a.date <= end
        ]
