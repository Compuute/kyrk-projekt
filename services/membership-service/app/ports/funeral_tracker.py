"""Port for tracking funeral and repatriation cases."""
from __future__ import annotations

from typing import Protocol

from app.domain.models import FuneralCase


class FuneralTrackerPort(Protocol):
    def list_cases(self, church_id: str) -> list[FuneralCase]:
        """List all funeral cases for a specific church."""
        ...

    def get_case(self, church_id: str, case_id: str) -> FuneralCase | None:
        """Get a specific funeral case by ID."""
        ...

    def save_case(self, case: FuneralCase) -> None:
        """Save/Update a funeral case."""
        ...

    def delete_case(self, church_id: str, case_id: str) -> None:
        """Delete a funeral case."""
        ...
