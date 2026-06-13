"""Church list for admin-web dropdowns.

Loaded from app/data/churches.json, which is a copy of the canonical
frontend/member-portal/churches.json. tests/test_churches_sync.py fails
CI if the copy drifts — edit the canonical file and resync, never patch
one copy.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parent / "data" / "churches.json"


@dataclass(frozen=True)
class Church:
    id: str
    name_sv: str
    name_am: str
    city: str


@lru_cache(maxsize=1)
def list_churches() -> list[Church]:
    raw = json.loads(_DATA.read_text(encoding="utf-8"))
    return [
        Church(
            id=c["id"],
            name_sv=c["name"]["sv"],
            name_am=c["name"]["am"],
            city=c["city"],
        )
        for c in raw["churches"]
    ]


def get_church(church_id: str) -> Church | None:
    for c in list_churches():
        if c.id == church_id:
            return c
    return None
