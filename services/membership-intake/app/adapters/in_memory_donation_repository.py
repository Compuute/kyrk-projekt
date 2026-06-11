from __future__ import annotations

from app.domain.models import DonationRecord, DonationStatus


class InMemoryDonationRepository:
    def __init__(self) -> None:
        self._items: dict[str, DonationRecord] = {}

    def add(self, donation: DonationRecord) -> None:
        self._items[donation.donation_id] = donation

    def get(self, donation_id: str) -> DonationRecord | None:
        return self._items.get(donation_id)

    def update(self, donation: DonationRecord) -> None:
        self._items[donation.donation_id] = donation

    def list_pending(self, church_id: str) -> list[DonationRecord]:
        return [
            d
            for d in self._items.values()
            if d.church_id == church_id
            and d.status is DonationStatus.PENDING_VERIFICATION
        ]
