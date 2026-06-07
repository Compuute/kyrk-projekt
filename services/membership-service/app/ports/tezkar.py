"""Tezkar (ተዝካር) memorial prayer service — domain model.

Ethiopian Orthodox tradition prescribes memorial prayers at specific
intervals after death. Families book and pay per-event via Swish.
The priest receives a notification with the details.

Memorial days (Fetha Negest ch. 22):
  3rd   — ሦስተኛ (Seleste)     — Holy Trinity
  7th   — ሰባተኛ (Sebate)      — one week
  12th  — አሥራ ሁለተኛ (Asra Huletegna)
  40th  — አርብዓ (Arba'a)      — major, men (Christ's ascension)
  80th  — ሰማንያ (Semaniya)    — major, women
  6 mo  — ምንፈቅ (Menfeq)      — half-year
  1 yr  — አመት (Amet)         — annual
  +7yr  — yearly anniversaries (Tezkar)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Protocol
from uuid import uuid4


# ---------------------------------------------------------------------------
# Memorial day schedule
# ---------------------------------------------------------------------------

MEMORIAL_DAYS = [
    (3, "seleste", "ሦስተኛ", "3rd day"),
    (7, "sebate", "ሰባተኛ", "7th day"),
    (12, "asra_huletegna", "አሥራ ሁለተኛ", "12th day"),
    (40, "arbaa", "አርብዓ", "40th day — major"),
    (80, "semaniya", "ሰማንያ", "80th day — major"),
    (180, "menfeq", "ምንፈቅ", "6 months"),
    (365, "amet", "አመት", "1 year"),
]


def compute_memorial_dates(death_date: date) -> list[tuple[date, str, str]]:
    """Return list of (date, key, amharic_name) for all memorial days."""
    from datetime import timedelta
    result = []
    for days, key, am_name, _desc in MEMORIAL_DAYS:
        result.append((death_date + timedelta(days=days), key, am_name))
    for year in range(2, 8):
        result.append((
            death_date.replace(year=death_date.year + year)
            if _safe_replace(death_date, year) else
            date(death_date.year + year, death_date.month, 28),
            f"tezkar_year_{year}",
            f"ተዝካር — {year} ዓመት",
        ))
    return result


def _safe_replace(d: date, years: int) -> bool:
    try:
        d.replace(year=d.year + years)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class TezkarStatus(str, Enum):
    REQUESTED = "requested"
    PAID = "paid"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TezkarRequest:
    church_id: str
    requester_member_id: str
    deceased_name: str  # kristet/kyrkligt namn
    deceased_name_amharic: str = ""
    death_date: date | None = None
    memorial_type: str = ""  # seleste, sebate, arbaa, etc.
    requested_date: date | None = None
    amount_sek: int = 0  # suggested donation / set by church
    payment_method: str = "swish"
    payment_reference: str = ""
    notes: str = ""
    tezkar_id: str = field(default_factory=lambda: str(uuid4()))
    status: TezkarStatus = TezkarStatus.REQUESTED
    created_at: datetime | None = None
    priest_notified: bool = False


# ---------------------------------------------------------------------------
# Port
# ---------------------------------------------------------------------------

class TezkarPort(Protocol):
    def create_request(self, request: TezkarRequest) -> TezkarRequest: ...
    def mark_paid(self, tezkar_id: str, payment_ref: str) -> TezkarRequest: ...
    def mark_scheduled(self, tezkar_id: str) -> TezkarRequest: ...
    def mark_completed(self, tezkar_id: str) -> TezkarRequest: ...
    def cancel(self, tezkar_id: str) -> TezkarRequest: ...
    def list_upcoming(self, church_id: str) -> list[TezkarRequest]: ...
    def list_by_member(self, member_id: str) -> list[TezkarRequest]: ...
    def compute_schedule(self, death_date: date) -> list[tuple[date, str, str]]:
        """Return all memorial dates for a given death date."""
        ...
