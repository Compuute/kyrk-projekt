from __future__ import annotations

from app.domain.errors import ReceiptDeliveryFailure
from app.ports.email_sender import DonationReceipt


class FakeEmailSender:
    """Test fake. Set `fail_next` to simulate a provider outage."""

    def __init__(self) -> None:
        self.sent: list[DonationReceipt] = []
        self.fail_next = False

    def send_donation_receipt(self, receipt: DonationReceipt) -> None:
        if self.fail_next:
            self.fail_next = False
            raise ReceiptDeliveryFailure("simulated provider outage")
        self.sent.append(receipt)
