"""Domain models for the agent worker.

The audit trail is the accountability mechanism from the Agent Operating
Model: every consumed job leaves exactly one AuditEvent, attributable to
a named agent, holding only GREEN/YELLOW data (period, report id, status
— never member data).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class JobStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    # Message acked without running: duplicate delivery of a completed job.
    SKIPPED = "skipped"
    # Message acked without running: permanently unprocessable (unknown job,
    # malformed envelope/payload). Retrying would never help.
    REJECTED = "rejected"


@dataclass(frozen=True)
class AuditEvent:
    message_id: str
    job: str
    status: JobStatus
    agent: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    period: str = ""
    report_id: str = ""
    detail: str = ""
