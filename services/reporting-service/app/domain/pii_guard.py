"""PII guard — defense in depth behind the n8n sanitizer.

A payload is rejected if any of the forbidden field names appears at any
depth in a nested dict/list structure. Matching is case-insensitive to
catch mistakes like `FirstName` or `PersonalNumber`.
"""
from __future__ import annotations

from app.domain.errors import PIIRejected


FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "personal_number",
    "personnummer",
    "ssn",
    "name",
    "first_name",
    "last_name",
    "full_name",
    "email",
    "phone",
    "phone_number",
    "address",
    "street",
    "birth_date",
})


def assert_no_pii(payload: object, path: str = "$") -> None:
    """Walk the payload; raise PIIRejected on first forbidden field."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_FIELDS:
                raise PIIRejected(f"forbidden field at {path}.{key}")
            assert_no_pii(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            assert_no_pii(item, f"{path}[{i}]")
    # primitives: nothing to check
