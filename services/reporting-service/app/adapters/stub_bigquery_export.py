from __future__ import annotations

from app.domain.models import Report


class StubBigQueryExport:
    def __init__(self) -> None:
        self.published: list[Report] = []

    def publish(self, report: Report) -> None:
        self.published.append(report)
