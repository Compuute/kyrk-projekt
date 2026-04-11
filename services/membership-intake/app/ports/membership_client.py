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
