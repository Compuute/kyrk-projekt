from __future__ import annotations

from app.domain.models import Report


class InMemoryReportRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], Report] = {}

    def add(self, report: Report) -> None:
        self._items[(report.church_id, report.report_id)] = report

    def get(self, church_id: str, report_id: str) -> Report | None:
        return self._items.get((church_id, report_id))
