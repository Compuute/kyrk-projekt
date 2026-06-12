"""Fake reporting client for tests and local dev."""
from __future__ import annotations

from datetime import date


class FakeReportingClient:
    def __init__(self) -> None:
        self.activities: list[dict] = []
        self.exported: list[tuple[str, date, date]] = []
        self.generated: list[tuple[str, list[dict], dict]] = []
        self.fail_next = False
        self.report_id = "r-fake-1"
        self._pending_period = ""

    def export_activities(self, start: date, end: date) -> list[dict]:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("boom")
        self._pending_period = f"{start.year:04d}-{start.month:02d}"
        self.exported.append((self._pending_period, start, end))
        return list(self.activities)

    def generate_monthly(
        self, period: str, activities: list[dict], finance: dict
    ) -> str:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("boom")
        self.generated.append((period, activities, finance))
        return self.report_id
