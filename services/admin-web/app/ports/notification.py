"""Port for dispatching notifications (webhook, Telegram, etc).

Abstracts away HOW notifications are sent so we're not locked
to n8n, httpx, or any specific webhook provider.
"""
from __future__ import annotations

from typing import Protocol


class NotificationPort(Protocol):
    def notify_new_funeral_case(self, payload: dict) -> None: ...
