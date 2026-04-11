from __future__ import annotations

from app.domain.models import Certificate


class InMemoryCertificateRepository:
    def __init__(self) -> None:
        self._items: dict[str, Certificate] = {}

    def add(self, certificate: Certificate) -> None:
        self._items[certificate.certificate_id] = certificate

    def get(self, certificate_id: str) -> Certificate | None:
        return self._items.get(certificate_id)

    def update(self, certificate: Certificate) -> None:
        self._items[certificate.certificate_id] = certificate
