"""Membership use cases. No framework imports here — this layer is pure logic."""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.errors import (
    ChurchMismatch,
    MemberNotFound,
    NotAuthorized,
)
from app.domain.models import Actor, Member, MemberStatus, Role
from app.ports.audit import AuditEvent, AuditPort
from app.ports.encryption import EncryptionPort
from app.ports.member_repository import MemberRepository


_WRITE_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR, Role.SECRETARY}
_READ_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR, Role.SECRETARY}
_DEACTIVATE_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR}


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
