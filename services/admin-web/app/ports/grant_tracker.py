"""Port for tracking grant applications per church.

Each church can have zero or one GrantApplication per grant_id.
The port stores application status, amounts, notes, and a reference
to the generated draft.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class GrantApplication:
    grant_id: str
    church_id: str
    status: str = "not_started"  # not_started | in_progress | submitted | approved | rejected
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    amount_requested: float | None = None
    amount_granted: float | None = None
    notes: str = ""
    generated_draft_url: str | None = None
    # Board-supplied fields for draft generation
    project_name: str = ""
    project_description: str = ""
    target_group: str = ""
    budget_amount: float | None = None
    own_contribution: float | None = None


class GrantTrackerPort(Protocol):
    def list_applications(self, church_id: str) -> list[GrantApplication]: ...

    def get_application(self, church_id: str, grant_id: str) -> GrantApplication | None: ...

    def save_application(self, app: GrantApplication) -> None: ...
