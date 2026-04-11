"""BankID port — mirrors membership-service.

Phase 1: stub only. Phase 2: real client.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class BankIdVerification:
    verified: bool
    personal_number: str | None


class BankIdPort(Protocol):
    def start(self, personal_number: str) -> str: ...
    def poll(self, session_token: str) -> BankIdVerification: ...
