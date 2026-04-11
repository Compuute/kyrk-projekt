from __future__ import annotations

from typing import Protocol

from app.domain.models import Certificate


class CertificateRepository(Protocol):
    def add(self, certificate: Certificate) -> None: ...
    def get(self, certificate_id: str) -> Certificate | None: ...
    def update(self, certificate: Certificate) -> None: ...
