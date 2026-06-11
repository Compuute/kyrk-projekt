"""Brevo (EU email provider) adapter for donation receipts.

Chosen for EU data residency, matching the project's sovereignty stance.
Swapping provider = replacing this adapter; the port stays unchanged.

PII rule: the donor address goes to the provider's send endpoint and nowhere
else. Never log the address or the rendered body. Error messages must not
include the recipient.
"""
from __future__ import annotations

from app.domain.errors import ReceiptDeliveryFailure
from app.ports.email_sender import DonationReceipt

_API_URL = "https://api.brevo.com/v3/smtp/email"

_METHOD_LABELS = {"swish": "Swish", "bankgiro": "Bankgiro"}


def _render_html(r: DonationReceipt) -> str:
    method = _METHOD_LABELS.get(r.method, r.method)
    return f"""<!DOCTYPE html>
<html lang="sv">
<body style="font-family: sans-serif; max-width: 560px; margin: 0 auto; color: #222;">
  <h1 style="font-size: 20px;">Gåvokvitto</h1>
  <p>Tack för din gåva till {r.church_name}.</p>
  <table style="border-collapse: collapse; width: 100%;">
    <tr><td style="padding: 4px 8px 4px 0;"><strong>Kvittonummer</strong></td><td>{r.receipt_number}</td></tr>
    <tr><td style="padding: 4px 8px 4px 0;"><strong>Belopp</strong></td><td>{r.amount_sek} kr</td></tr>
    <tr><td style="padding: 4px 8px 4px 0;"><strong>Betalsätt</strong></td><td>{method}</td></tr>
    <tr><td style="padding: 4px 8px 4px 0;"><strong>Gåvodatum</strong></td><td>{r.donated_at.date().isoformat()}</td></tr>
    <tr><td style="padding: 4px 8px 4px 0;"><strong>Bekräftad av församlingen</strong></td><td>{r.verified_at.date().isoformat()}</td></tr>
    <tr><td style="padding: 4px 8px 4px 0;"><strong>Mottagare</strong></td><td>{r.church_name}</td></tr>
    <tr><td style="padding: 4px 8px 4px 0;"><strong>Org.nr</strong></td><td>{r.church_org_number}</td></tr>
  </table>
  <p style="margin-top: 16px;">{r.church_name} är godkänd gåvomottagare hos
  Skatteverket. För att gåvan ska ingå i underlaget för skattereduktion
  behöver församlingen ditt personnummer för kontrolluppgift — kontakta
  församlingen om du önskar detta. Spara kvittot.</p>
  <p style="color: #777; font-size: 12px;">Detta är en bekräftelse på en gåva
  som församlingens kassör har stämt av mot kontoutdraget.</p>
</body>
</html>"""


class BrevoEmailSender:
    def __init__(self, api_key: str, from_email: str, from_name: str, timeout_seconds: float = 10.0) -> None:
        self._api_key = api_key
        self._from_email = from_email
        self._from_name = from_name
        self._timeout = timeout_seconds

    def send_donation_receipt(self, receipt: DonationReceipt) -> None:
        import httpx  # vendor import allowed in adapters only

        payload = {
            "sender": {"email": self._from_email, "name": self._from_name},
            "to": [{"email": receipt.to_email}],
            "subject": f"Gåvokvitto {receipt.receipt_number} — {receipt.church_name}",
            "htmlContent": _render_html(receipt),
        }
        try:
            response = httpx.post(
                _API_URL,
                json=payload,
                headers={"api-key": self._api_key, "accept": "application/json"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ReceiptDeliveryFailure("email provider unreachable") from exc
        if response.status_code >= 400:
            # Status only — never echo the payload (it contains the address).
            raise ReceiptDeliveryFailure(
                f"email provider returned {response.status_code}"
            )
