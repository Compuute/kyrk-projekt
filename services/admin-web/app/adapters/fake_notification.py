"""In-memory fake notification adapter for tests."""
from __future__ import annotations


class FakeNotification:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def notify_new_funeral_case(self, payload: dict) -> None:
        self.sent.append(payload)
