"""Auth port for admin endpoints on membership-intake.

The public POST /intake endpoint does not use this port — it's anonymous
by design. Only the admin endpoints (list pending, approve, reject) do.
"""
from __future__ import annotations

from typing import Protocol

from app.domain.models import Actor


class AuthPort(Protocol):
    def authenticate(self, token: str) -> Actor: ...
