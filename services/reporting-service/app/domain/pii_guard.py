"""PII guard — defense in depth behind the n8n sanitizer.

A payload is rejected if any of the forbidden field names appears at any
depth in a nested dict/list structure. Matching is case-insensitive and
ignores underscores/hyphens so `first_name`, `FirstName`, `first-name`,
and `firstName` all match the same forbidden token.
"""
from __future__ import annotations

from app.domain.errors import PIIRejected


# Stored without separators so we can normalize incoming keys the same way.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "personalnumber",
    "personnummer",
    "ssn",
    "name",
    "firstname",
    "lastname",
    "fullname",
    "email",
    "phone",
    "phonenumber",
    "address",
    "street",
    "birthdate",
})


def _normalize(key: str) -> str:
    return key.replace("_", "").replace("-", "").lower()


def assert_no_pii(payload: object, path: str = "$") -> None:
    """Walk the payload; raise PIIRejected on first forbidden field."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and _normalize(key) in FORBIDDEN_FIELDS:
                raise PIIRejected(f"forbidden field at {path}.{key}")
            assert_no_pii(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            assert_no_pii(item, f"{path}[{i}]")
    # primitives: nothing to check
