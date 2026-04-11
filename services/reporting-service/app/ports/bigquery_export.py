"""BigQuery export port. MVP has an in-memory stub; Phase 2 wires real BQ."""
from __future__ import annotations

from typing import Protocol

from app.domain.models import Report


class BigQueryExportPort(Protocol):
    def publish(self, report: Report) -> None: ...
