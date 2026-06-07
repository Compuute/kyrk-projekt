"""Intake use cases. No framework imports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.errors import (
    ConsentMissing,
    DuplicateSubmission,
    NotAuthorized,
    RateLimited,
    SubmissionAlreadyProcessed,
    SubmissionNotFound,
)
from app.domain.models import Actor, IntakeSubmission, Role, SubmissionStatus
from app.ports.membership_client import (
    CreateMemberRequest,
    MembershipClientPort,
)
from app.ports.notifier import NotifierPort
from app.ports.rate_limiter import RateLimiterPort
from app.ports.submission_repository import SubmissionRepository


_ADMIN_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR, Role.SECRETARY}


@dataclass(frozen=True)
class FamilyMember:
    first_name: str
    last_name: str
    personal_number: str = ""
    relation: str = ""  # spouse, child


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
    source: str = "direct"
    membership_type: str = "individual"  # individual | family
    monthly_fee_sek: int = 200
    family_members: tuple[FamilyMember, ...] = ()


@dataclass(frozen=True)
class ApprovalResult:
    submission_id: str
    status: str
    created_member_id: str


class IntakeService:
    def __init__(
        self,
        repo: SubmissionRepository,
        notifier: NotifierPort,
        limiter: RateLimiterPort,
        membership_client: MembershipClientPort | None = None,
    ) -> None:
        self._repo = repo
        self._notifier = notifier
        self._limiter = limiter
        self._membership_client = membership_client

    # ------------------------------------------------------------------- public

    def submit(self, payload: IntakePayload, client_ip: str) -> IntakeSubmission:
        if not payload.gdpr_consent:
            raise ConsentMissing("gdpr_consent is required")

        # Rate limit on a composite key: per-IP abuse and per-church floods.
        ip_key = f"ip:{client_ip}"
        church_key = f"church:{payload.church_id}"
        if not self._limiter.check(ip_key) or not self._limiter.check(church_key):
            raise RateLimited("too many submissions")

        # Duplicate check on personal_number
        if payload.personal_number:
            existing = self._repo.find_by_personal_number(payload.personal_number)
            if existing is not None:
                raise DuplicateSubmission(
                    f"personnummer redan registrerat (submission {existing.submission_id})"
                )

        from app.domain.models import FamilyMemberRecord
        submission = IntakeSubmission(
            church_id=payload.church_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            email=payload.email,
            personal_number=payload.personal_number,
            gdpr_consent=payload.gdpr_consent,
            consent_timestamp=payload.consent_timestamp,
            source=payload.source,
            membership_type=payload.membership_type,
            monthly_fee_sek=payload.monthly_fee_sek,
            family_members=[
                FamilyMemberRecord(
                    first_name=fm.first_name,
                    last_name=fm.last_name,
                    personal_number=fm.personal_number,
                    relation=fm.relation,
                )
                for fm in payload.family_members
            ],
        )
        self._repo.add(submission)
        self._notifier.notify_new_pending(submission)
        return submission

    # -------------------------------------------------------------------- admin

    def list_pending(self, actor: Actor) -> list[IntakeSubmission]:
        self._require_admin(actor)
        return self._repo.list_pending(actor.church_id)

    def approve(
        self,
        actor: Actor,
        actor_token: str,
        submission_id: str,
    ) -> ApprovalResult:
        self._require_admin(actor)
        if self._membership_client is None:
            raise RuntimeError("approval requires a configured MembershipClientPort")
        submission = self._load_scoped_pending(actor, submission_id)

        result = self._membership_client.create_member(
            actor_token=actor_token,
            request=CreateMemberRequest(
                first_name=submission.first_name,
                last_name=submission.last_name,
                phone=submission.phone,
                email=submission.email,
                personal_number=submission.personal_number,
            ),
        )

        submission.mark_approved(actor.user_id, result.member_id)
        self._repo.update(submission)

        return ApprovalResult(
            submission_id=submission.submission_id,
            status=submission.status.value,
            created_member_id=result.member_id,
        )

    def reject(self, actor: Actor, submission_id: str) -> IntakeSubmission:
        self._require_admin(actor)
        submission = self._load_scoped_pending(actor, submission_id)
        submission.mark_rejected(actor.user_id)
        self._repo.update(submission)
        return submission

    # --------------------------------------------------------------- internals

    def _require_admin(self, actor: Actor) -> None:
        if actor.role not in _ADMIN_ROLES:
            raise NotAuthorized(f"role {actor.role.value} cannot perform this action")

    def _load_scoped_pending(self, actor: Actor, submission_id: str) -> IntakeSubmission:
        submission = self._repo.get(submission_id)
        if submission is None or submission.church_id != actor.church_id:
            raise SubmissionNotFound(submission_id)
        if submission.status is not SubmissionStatus.PENDING:
            raise SubmissionAlreadyProcessed(submission_id)
        return submission
