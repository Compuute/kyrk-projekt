"""Stub PDF generator for tests and local dev.

Returns deterministic bytes of a rendered text template. Production swaps
in a real PDF library (ReportLab or WeasyPrint).
"""
from __future__ import annotations

from app.domain.models import Certificate


_TEMPLATE = (
    "CERTIFICATE OF {type_upper}\n"
    "Church: {church_name}\n"
    "Issued: {issued_date}\n"
    "To: {member_name}\n"
    "Verification: https://example.org/verify/{cert_id}\n"
)


class StubPdfGenerator:
    def render(self, certificate: Certificate, member_full_name: str) -> bytes:
        text = _TEMPLATE.format(
            type_upper=certificate.certificate_type.value.upper(),
            church_name=certificate.church_name,
            issued_date=certificate.issued_date.isoformat(),
            member_name=member_full_name,
            cert_id=certificate.certificate_id,
        )
        return text.encode("utf-8")
