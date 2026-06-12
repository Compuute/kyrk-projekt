"""Job dispatch for agent jobs. No framework imports.

Outcome contract (drives the Pub/Sub ack semantics in the route):
- SUCCEEDED / SKIPPED / REJECTED — terminal, the message must be acked.
- JobFailed raised — transient, the message must be redelivered.

Every handled message leaves exactly one AuditEvent (AOM: agent actions
are attributable and observable). Dedupe on message_id makes redelivery
of an already-completed job a no-op.
"""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Callable

from app.domain.errors import JobFailed
from app.domain.models import AuditEvent, JobStatus
from app.ports.audit_log import AuditLogPort
from app.ports.reporting_client import ReportingClientPort

_AGENT = "report-agent"
_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _month_bounds(period: str) -> tuple[date, date]:
    year, month = int(period[:4]), int(period[5:7])
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def _previous_month(now: datetime) -> str:
    year, month = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
    return f"{year:04d}-{month:02d}"


class JobService:
    def __init__(
        self,
        reporting: ReportingClientPort,
        audit: AuditLogPort,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._reporting = reporting
        self._audit = audit
        self._now_fn = now_fn

    def handle(self, message_id: str, payload: dict) -> JobStatus:
        if self._audit.seen(message_id):
            return self._record(message_id, payload.get("job", ""), JobStatus.SKIPPED,
                                detail="duplicate delivery")

        job = payload.get("job", "")
        if job != "monthly-report":
            return self._record(message_id, job, JobStatus.REJECTED,
                                detail=f"unknown job: {job!r}")

        period = payload.get("period") or _previous_month(self._now_fn())
        if not _PERIOD_RE.match(period):
            return self._record(message_id, job, JobStatus.REJECTED,
                                detail=f"invalid period: {period!r}")

        try:
            start, end = _month_bounds(period)
            activities = self._reporting.export_activities(start, end)
            report_id = self._reporting.generate_monthly(period, activities, finance={})
        except Exception as exc:
            self._record(message_id, job, JobStatus.FAILED, period=period, detail=str(exc))
            raise JobFailed(str(exc)) from exc

        return self._record(message_id, job, JobStatus.SUCCEEDED,
                            period=period, report_id=report_id)

    def reject(self, message_id: str, detail: str) -> JobStatus:
        """Ack-and-audit a message that cannot even be parsed."""
        return self._record(message_id, "", JobStatus.REJECTED, detail=detail)

    def _record(
        self,
        message_id: str,
        job: str,
        status: JobStatus,
        period: str = "",
        report_id: str = "",
        detail: str = "",
    ) -> JobStatus:
        self._audit.record(
            AuditEvent(
                message_id=message_id,
                job=job,
                status=status,
                agent=_AGENT,
                created_at=self._now_fn(),
                period=period,
                report_id=report_id,
                detail=detail,
            )
        )
        return status
