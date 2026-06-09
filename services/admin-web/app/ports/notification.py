"""Port for dispatching notifications (webhook, Telegram, etc).

The implementation is injected at startup. The route doesn't couple
to httpx, specific webhook structures, or any particular provider.
"""
from __future__ import annotations

from typing import Protocol


class NotificationPort(Protocol):
    def notify_new_funeral_case(self, payload: dict) -> None: ...
