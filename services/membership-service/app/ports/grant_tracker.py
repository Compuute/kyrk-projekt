"""Port for tracking grant applications per church."""
from __future__ import annotations

from typing import Protocol

from app.domain.models import GrantApplication


class GrantTrackerPort(Protocol):
    def list_applications(self, church_id: str) -> list[GrantApplication]:
        """List all grant applications for a specific church."""
        ...

    def get_application(self, church_id: str, grant_id: str) -> GrantApplication | None:
        """Get a specific grant application by grant id."""
        ...

    def save_application(self, app: GrantApplication) -> None:
        """Save/update a grant application."""
        ...
