from __future__ import annotations

from typing import Protocol

from app.domain.models import Report


class ReportRepository(Protocol):
    def add(self, report: Report) -> None: ...
    def get(self, church_id: str, report_id: str) -> Report | None: ...
