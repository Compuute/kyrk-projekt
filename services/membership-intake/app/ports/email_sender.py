"""Email sender port — used for donation receipts.

The receipt payload is assembled in the domain so adapters stay dumb: they
render and deliver, nothing else. The donor email address is PII (RED zone):
adapters must never log it or forward it anywhere except the email provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class DonationReceipt:
    to_email: str
    receipt_number: str
    church_name: str
    church_org_number: str
    amount_sek: int
    method: str  # swish | bankgiro
    donated_at: datetime
    verified_at: datetime


class EmailSenderPort(Protocol):
    def send_donation_receipt(self, receipt: DonationReceipt) -> None:
        """Deliver the receipt. Raises on failure — caller decides retry."""
        ...
