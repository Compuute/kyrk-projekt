from __future__ import annotations

from typing import Protocol

from app.domain.models import Actor


class AuthPort(Protocol):
    def authenticate(self, token: str) -> Actor: ...
