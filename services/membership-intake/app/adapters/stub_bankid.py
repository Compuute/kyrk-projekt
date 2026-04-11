from __future__ import annotations

from app.ports.bankid import BankIdVerification


class StubBankIdAdapter:
    def start(self, personal_number: str) -> str:  # noqa: ARG002
        return "stub-session-token"

    def poll(self, session_token: str) -> BankIdVerification:  # noqa: ARG002
        return BankIdVerification(verified=False, personal_number=None)
