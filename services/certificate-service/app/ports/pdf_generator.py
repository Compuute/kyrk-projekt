from __future__ import annotations

from typing import Protocol

from app.domain.models import Certificate


class PdfGeneratorPort(Protocol):
    def render(self, certificate: Certificate, member_full_name: str) -> bytes: ...
