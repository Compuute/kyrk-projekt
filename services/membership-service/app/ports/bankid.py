"""BankID port.

Phase 1: interface + stub only. Phase 2 replaces the stub with a real
BankID client. Service code must not import any concrete BankID library.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class BankIdVerification:
    verified: bool
    personal_number: str | None
    issued_at: str | None  # ISO 8601


class BankIdPort(Protocol):
    def start(self, personal_number: str) -> str:
        """Start a verification flow; return a session token."""
        ...

    def poll(self, session_token: str) -> BankIdVerification:
        """Poll the session; return the current verification state."""
        ...
