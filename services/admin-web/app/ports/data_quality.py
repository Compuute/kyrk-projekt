"""Port for data quality metrics."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DataQualityReport:
    total_members: int
    complete_profiles: int
    completeness_pct: float
    valid_personnummer: int
    personnummer_pct: float
    valid_phone: int
    phone_pct: float
    valid_email: int
    email_pct: float
    duplicates: int
    duplicate_pct: float
    missing_fields: dict[str, int]


def _luhn_check(digits: str) -> bool:
    if len(digits) != 10 or not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
        if d > 9:
            d -= 9
        total += d
    return total % 10 == 0


def validate_personnummer(pnr: str) -> bool:
    clean = re.sub(r"[-\s]", "", pnr)
    if len(clean) == 12:
        clean = clean[2:]
    return _luhn_check(clean)


def validate_phone(phone: str) -> bool:
    clean = re.sub(r"[-\s]", "", phone)
    return bool(re.match(r"^(\+46|0)\d{7,10}$", clean))


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def compute_quality(members: list[dict]) -> DataQualityReport:
    total = len(members)
    if total == 0:
        return DataQualityReport(
            total_members=0, complete_profiles=0, completeness_pct=0,
            valid_personnummer=0, personnummer_pct=0,
            valid_phone=0, phone_pct=0,
            valid_email=0, email_pct=0,
            duplicates=0, duplicate_pct=0,
            missing_fields={},
        )

    required = ["first_name", "last_name", "phone", "email", "personal_number"]
    complete = 0
    valid_pnr = 0
    valid_ph = 0
    valid_em = 0
    missing: dict[str, int] = {f: 0 for f in required}
    seen_pnr: dict[str, int] = {}

    for m in members:
        is_complete = True
        for f in required:
            val = m.get(f, "")
            if not val or val == "***redacted***":
                missing[f] += 1
                is_complete = False
        if is_complete:
            complete += 1

        pnr = m.get("personal_number", "")
        if pnr and pnr != "***redacted***":
            if validate_personnummer(pnr):
                valid_pnr += 1
            clean_pnr = re.sub(r"[-\s]", "", pnr)
            seen_pnr[clean_pnr] = seen_pnr.get(clean_pnr, 0) + 1

        phone = m.get("phone", "")
        if phone and validate_phone(phone):
            valid_ph += 1

        email = m.get("email", "")
        if email and validate_email(email):
            valid_em += 1

    duplicates = sum(c - 1 for c in seen_pnr.values() if c > 1)

    pct = lambda n: round(n / total * 100, 1) if total else 0

    return DataQualityReport(
        total_members=total,
        complete_profiles=complete,
        completeness_pct=pct(complete),
        valid_personnummer=valid_pnr,
        personnummer_pct=pct(valid_pnr),
        valid_phone=valid_ph,
        phone_pct=pct(valid_ph),
        valid_email=valid_em,
        email_pct=pct(valid_em),
        duplicates=duplicates,
        duplicate_pct=pct(duplicates),
        missing_fields={k: v for k, v in missing.items() if v > 0},
    )
