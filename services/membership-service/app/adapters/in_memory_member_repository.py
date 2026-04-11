"""In-memory member repository. Used by tests and local dev."""
from __future__ import annotations

from app.domain.models import Member


class InMemoryMemberRepository:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], Member] = {}

    def add(self, member: Member) -> None:
        self._by_key[(member.church_id, member.member_id)] = member

    def get(self, church_id: str, member_id: str) -> Member | None:
        return self._by_key.get((church_id, member_id))

    def update(self, member: Member) -> None:
        self._by_key[(member.church_id, member.member_id)] = member

    def list_by_church(self, church_id: str) -> list[Member]:
        return [m for (c, _), m in self._by_key.items() if c == church_id]
