"""Membership use cases. No framework imports here — this layer is pure logic."""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.errors import (
    ChurchMismatch,
    MemberNotFound,
    NotAuthorized,
)
from app.domain.models import Actor, Member, MemberStatus, Role, _now
from app.ports.audit import AuditEvent, AuditPort
from app.ports.encryption import EncryptionPort
from app.ports.member_repository import MemberRepository


_WRITE_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR, Role.SECRETARY}
_READ_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR, Role.SECRETARY}
_DEACTIVATE_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR}


@dataclass(frozen=True)
class MemberStats:
    church_id: str
    total: int
    active: int
    inactive: int
    pending: int
    new_this_month: int
    new_this_quarter: int
    growth_rate_quarterly: float
    retention_rate: float


@dataclass(frozen=True)
class CreateMemberInput:
    first_name: str
    last_name: str
    phone: str
    email: str
    personal_number: str  # plaintext on the wire — encrypted before storage


@dataclass(frozen=True)
class UpdateMemberInput:
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None


class MembershipService:
    def __init__(
        self,
        repo: MemberRepository,
        encryption: EncryptionPort,
        audit: AuditPort,
    ) -> None:
        self._repo = repo
        self._encryption = encryption
        self._audit = audit

    # ------------------------------------------------------------------ writes

    def create(self, actor: Actor, data: CreateMemberInput) -> Member:
        self._require_role(actor, _WRITE_ROLES)
        member = Member(
            church_id=actor.church_id,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            email=data.email,
            personal_number_encrypted=self._encryption.encrypt(data.personal_number),
        )
        self._repo.add(member)
        self._audit.record(AuditEvent(
            actor_user_id=actor.user_id,
            church_id=actor.church_id,
            action="member.create",
            target_id=member.member_id,
        ))
        return member

    def update(self, actor: Actor, member_id: str, data: UpdateMemberInput) -> Member:
        self._require_role(actor, _WRITE_ROLES)
        member = self._load_scoped(actor, member_id)
        if data.first_name is not None:
            member.first_name = data.first_name
        if data.last_name is not None:
            member.last_name = data.last_name
        if data.phone is not None:
            member.phone = data.phone
        if data.email is not None:
            member.email = data.email
        self._repo.update(member)
        self._audit.record(AuditEvent(
            actor_user_id=actor.user_id,
            church_id=actor.church_id,
            action="member.update",
            target_id=member.member_id,
        ))
        return member

    def deactivate(self, actor: Actor, member_id: str) -> Member:
        self._require_role(actor, _DEACTIVATE_ROLES)
        member = self._load_scoped(actor, member_id)
        member.deactivate()
        self._repo.update(member)
        self._audit.record(AuditEvent(
            actor_user_id=actor.user_id,
            church_id=actor.church_id,
            action="member.deactivate",
            target_id=member.member_id,
        ))
        return member

    def activate(self, actor: Actor, member_id: str) -> Member:
        self._require_role(actor, _WRITE_ROLES)
        member = self._load_scoped(actor, member_id)
        member.activate()
        self._repo.update(member)
        self._audit.record(AuditEvent(
            actor_user_id=actor.user_id,
            church_id=actor.church_id,
            action="member.activate",
            target_id=member.member_id,
        ))
        return member

    # ------------------------------------------------------------------- reads

    def get(self, actor: Actor, member_id: str) -> Member:
        self._require_role(actor, _READ_ROLES)
        return self._load_scoped(actor, member_id)

    def stats(self, actor: Actor) -> MemberStats:
        """Aggregate membership statistics for the caller's church.

        Returns YELLOW-safe data only — counts and rates, never names
        or identity fields. Safe to display on the KPI dashboard and
        to include in grant applications.
        """
        self._require_role(actor, _READ_ROLES | {Role.VIEWER})
        members = self._repo.list_by_church(actor.church_id)
        now = _now()
        thirty_days_ago = now.replace(day=1) if now.day < 30 else now
        ninety_days_ago = now

        total = len(members)
        active = sum(1 for m in members if m.status is MemberStatus.ACTIVE)
        inactive = sum(1 for m in members if m.status is MemberStatus.INACTIVE)
        pending = sum(1 for m in members if m.status is MemberStatus.PENDING)

        # New members this month (created_at within current month)
        new_this_month = sum(
            1 for m in members
            if m.created_at.year == now.year and m.created_at.month == now.month
        )

        # New this quarter
        q_start_month = ((now.month - 1) // 3) * 3 + 1
        new_this_quarter = sum(
            1 for m in members
            if m.created_at.year == now.year and m.created_at.month >= q_start_month
        )

        # Growth rate: new this quarter / total at start of quarter
        total_at_q_start = total - new_this_quarter
        growth_rate = (
            new_this_quarter / total_at_q_start
            if total_at_q_start > 0
            else 0.0
        )

        # Retention: active / (active + inactive)
        retention_rate = active / (active + inactive) if (active + inactive) > 0 else 1.0

        return MemberStats(
            church_id=actor.church_id,
            total=total,
            active=active,
            inactive=inactive,
            pending=pending,
            new_this_month=new_this_month,
            new_this_quarter=new_this_quarter,
            growth_rate_quarterly=round(growth_rate, 4),
            retention_rate=round(retention_rate, 4),
        )

    # --------------------------------------------------------------- internals

    def _require_role(self, actor: Actor, allowed: set[Role]) -> None:
        if actor.role not in allowed:
            raise NotAuthorized(f"role {actor.role.value} cannot perform this action")

    def _load_scoped(self, actor: Actor, member_id: str) -> Member:
        member = self._repo.get(actor.church_id, member_id)
        if member is None:
            # Intentionally do not disclose existence across churches.
            raise MemberNotFound(member_id)
        if member.church_id != actor.church_id:
            raise ChurchMismatch(member_id)
        # Ensure the member is in a usable state for mutation.
        _ = MemberStatus(member.status)
        return member
