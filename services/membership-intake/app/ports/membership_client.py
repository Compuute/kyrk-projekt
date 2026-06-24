"""Client port for talking to membership-service during approval."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CreateMemberRequest:
    first_name: str
    last_name: str
    phone: str
    email: str
    personal_number: str


@dataclass(frozen=True)
class CreateMemberResult:
    member_id: str


@dataclass(frozen=True)
class PublicEnrollmentRequest:
    """A guardian's public Fredagsskola/söndagsskola application. Minimal data
    only (GDPR Art. 8): no personnummer, no phone."""
    church_id: str
    group_id: str
    child_first_name: str
    child_last_name: str
    birth_year: int
    guardian_name: str
    guardian_consent: bool
    consent_timestamp: str


class MembershipClientPort(Protocol):
    def create_member(
        self,
        actor_token: str,
        request: CreateMemberRequest,
    ) -> CreateMemberResult:
        """Create a member in membership-service.

        Raises `DownstreamFailure` on any non-2xx response or network error.
        """
        ...

    def create_public_enrollment(
        self,
        request: PublicEnrollmentRequest,
        client_ip: str,
    ) -> None:
        """Forward a public (unauthenticated) education enrollment to
        membership-service's pending-enroll endpoint. No actor token — this is
        the public funnel; membership-intake is the public edge and holds the
        Cloud Run invoker binding. client_ip is forwarded (X-Forwarded-For) so
        the downstream rate-limiter keys on the real caller.

        Raises `RateLimited` on downstream 429, `DownstreamFailure` otherwise.
        """
        ...
