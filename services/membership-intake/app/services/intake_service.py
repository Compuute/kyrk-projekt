"""Intake use case. No framework imports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.errors import ConsentMissing, RateLimited
from app.domain.models import IntakeSubmission
from app.ports.notifier import NotifierPort
from app.ports.rate_limiter import RateLimiterPort
from app.ports.submission_repository import SubmissionRepository


@dataclass(frozen=True)
class IntakePayload:
    church_id: str
    first_name: str
    last_name: str
    phone: str
    email: str
    personal_number: str
    gdpr_consent: bool
    consent_timestamp: datetime


class IntakeService:
    def __init__(
        self,
        repo: SubmissionRepository,
        notifier: NotifierPort,
        limiter: RateLimiterPort,
    ) -> None:
        self._repo = repo
        self._notifier = notifier
        self._limiter = limiter

    def submit(self, payload: IntakePayload, client_ip: str) -> IntakeSubmission:
        if not payload.gdpr_consent:
            raise ConsentMissing("gdpr_consent is required")

        # Rate limit on a composite key: we care about both per-IP abuse and per-church floods.
        ip_key = f"ip:{client_ip}"
        church_key = f"church:{payload.church_id}"
        if not self._limiter.check(ip_key) or not self._limiter.check(church_key):
            raise RateLimited("too many submissions")

        submission = IntakeSubmission(
            church_id=payload.church_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            email=payload.email,
            personal_number=payload.personal_number,
            gdpr_consent=payload.gdpr_consent,
            consent_timestamp=payload.consent_timestamp,
        )
        self._repo.add(submission)
        self._notifier.notify_new_pending(submission)
        return submission
