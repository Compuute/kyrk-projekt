"""Port for loading and saving bilingual content for the member portal.

The content store manages a JSON structure with version, church info,
upcoming activities, announcements, links, and footer — all bilingual
(Swedish + Amharic).
"""
from __future__ import annotations

from typing import Protocol


class ContentStorePort(Protocol):
    def load(self) -> dict: ...
    def save(self, content: dict) -> None: ...
