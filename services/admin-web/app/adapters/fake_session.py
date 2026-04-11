"""Fake session handling for MVP.

The cookie value is the raw bearer token in `user_id:church_id:role` form.
This is intentionally trivial — production swaps this for a PropelAuth
cookie + JWT validator without changing the route code.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionInfo:
    token: str
    user_id: str
    church_id: str
    role: str


def parse_session_cookie(value: str | None) -> SessionInfo | None:
    if not value or value.count(":") != 2:
        return None
    user_id, church_id, role = value.split(":")
    if role not in {"admin", "pastor", "secretary", "viewer"}:
        return None
    return SessionInfo(token=value, user_id=user_id, church_id=church_id, role=role)
