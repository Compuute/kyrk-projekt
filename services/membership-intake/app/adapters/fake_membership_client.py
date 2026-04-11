"""In-memory membership-service client for tests.

Keeps a list of every create_member call so tests can assert the handoff.
Can be programmed to raise DownstreamFailure for negative tests.
"""
from __future__ import annotations

from uuid import uuid4

from app.domain.errors import DownstreamFailure
from app.ports.membership_client import (
    CreateMemberRequest,
    CreateMemberResult,
)


class FakeMembershipClient:
    def __init__(self, *, fail_with: Exception | None = None) -> None:
        self.calls: list[tuple[str, CreateMemberRequest]] = []
        self._fail_with = fail_with

    def create_member(
        self,
        actor_token: str,
        request: CreateMemberRequest,
    ) -> CreateMemberResult:
        self.calls.append((actor_token, request))
        if self._fail_with is not None:
            raise DownstreamFailure(str(self._fail_with))
        return CreateMemberResult(member_id=str(uuid4()))
