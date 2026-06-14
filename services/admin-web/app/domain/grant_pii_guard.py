"""PII guard for grant-draft generation.

Grant drafts are built from GREEN data only: aggregate KPIs, the funder's
public criteria, and board-authored project text. Before any of that is sent
to an external LLM we scan all string values for Swedish personnummer-like
patterns (10 or 12 digits, optionally separated) and reject — RED PII must
never leave the service. Free-text amounts (e.g. "2000000") are not matched.
"""
from __future__ import annotations

import re


class GrantPIIRejected(Exception):
    """Raised when a grant-draft payload contains personnummer-like PII."""


# YYMMDD-XXXX (10) or YYYYMMDD-XXXX (12), not embedded in a longer number.
_PNR_RE = re.compile(r"(?<!\d)(?:\d{8}|\d{6})[-+]?\d{4}(?!\d)")


def _scan(value: object) -> None:
    if isinstance(value, str):
        if _PNR_RE.search(value.replace(" ", "")):
            raise GrantPIIRejected("personnummer-like value in grant draft input")
    elif isinstance(value, dict):
        for v in value.values():
            _scan(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _scan(v)


def assert_no_pii(payload: object) -> None:
    """Raise GrantPIIRejected if any string value looks like a personnummer."""
    _scan(payload)
