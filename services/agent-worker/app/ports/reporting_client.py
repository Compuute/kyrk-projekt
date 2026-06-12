from __future__ import annotations

from datetime import date
from typing import Protocol


class ReportingClientPort(Protocol):
    """Outbound calls to reporting-service (YELLOW zone, aggregates only)."""

    def export_activities(self, start: date, end: date) -> list[dict]:
        """Aggregated activities for the period (GET /activities/export/period)."""
        ...

    def generate_monthly(
        self, period: str, activities: list[dict], finance: dict
    ) -> str:
        """Generate the monthly report; returns the report id."""
        ...
