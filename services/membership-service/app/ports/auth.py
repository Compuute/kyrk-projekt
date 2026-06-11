"""Auth port. The real adapter is ZitadelAuthAdapter (OIDC via pyjwt).

We keep an interface so tests use a fake and the service code is independent
of the auth provider.
"""
from __future__ import annotations

from typing import Protocol

from app.domain.models import Actor


class AuthPort(Protocol):
    def authenticate(self, token: str) -> Actor:
        """Return the Actor for a bearer token, or raise NotAuthorized."""
        ...
