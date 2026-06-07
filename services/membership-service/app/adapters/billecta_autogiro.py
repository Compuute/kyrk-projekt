"""Billecta adapter — abstracts Bankgirot Autogiro behind a REST API.

Billecta handles:
  - Mandate management (medgivanden)
  - File generation and submission to Bankgirot
  - Report parsing from Bankgirot
  - Recurring payment scheduling

Requires: Billecta account + API credentials.
Cost: 0 kr/mån + 9 kr/transaktion.

API docs: https://docs.billecta.com/reference
"""
from __future__ import annotations

import base64
import os
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.ports.payment import (
    AutogiroMandate,
    MandatePort,
    MandateStatus,
    Payment,
    PaymentCategory,
    PaymentPort,
    PaymentStatus,
    PaymentSummary,
    BankReportPort,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BillectaClient:
    BASE_URL = "https://api.billecta.com"

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        creditor_public_id: str | None = None,
    ) -> None:
        self._username = username or os.getenv("BILLECTA_USERNAME", "")
        self._password = password or os.getenv("BILLECTA_PASSWORD", "")
        self._creditor_id = creditor_public_id or os.getenv("BILLECTA_CREDITOR_ID", "")
        self._token: str = ""

    def _authenticate(self) -> str:
        if self._token:
            return self._token
        creds = base64.b64encode(
            f"{self._username}:{self._password}".encode()
        ).decode()
        resp = httpx.post(
            f"{self.BASE_URL}/v1/authentication/apiauthenticate",
            headers={"Authorization": f"Basic {creds}"},
        )
        resp.raise_for_status()
        self._token = resp.json().get("SecureToken", "")
        return self._token

    def _headers(self) -> dict[str, str]:
        token = self._authenticate()
        encoded = base64.b64encode(token.encode()).decode()
        return {
            "Authorization": f"SecureToken {encoded}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        resp = httpx.post(
            f"{self.BASE_URL}{path}",
            headers=self._headers(),
            json=data,
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str) -> dict[str, Any]:
        resp = httpx.get(
            f"{self.BASE_URL}{path}",
            headers=self._headers(),
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = httpx.put(
            f"{self.BASE_URL}{path}",
            headers=self._headers(),
            json=data or {},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()

    def create_recurring_autogiro(
        self,
        debtor_id: str,
        amount_sek: int,
        description: str = "Medlemsavgift",
    ) -> str:
        result = self._post(
            "/v1/contractinvoice/monthlyrecurringautogiro",
            {
                "CreditorPublicId": self._creditor_id,
                "DebtorPublicId": debtor_id,
                "AutogiroWithdrawalEnabled": True,
                "Records": [
                    {
                        "ProductPublicId": "",
                        "Description": description,
                        "UnitPrice": {"Value": amount_sek * 100, "CurrencyCode": "SEK"},
                        "Units": 1,
                    }
                ],
            },
        )
        return result.get("PublicId", "")

    def resume_contract(self, contract_id: str) -> None:
        self._put(f"/v1/contractinvoice/resume/{contract_id}")

    def get_contract_invoices(self, contract_id: str) -> list[dict[str, Any]]:
        return self._get(f"/v1/contractinvoice/generatedinvoices/{contract_id}")

    def create_debtor(
        self,
        member_id: str,
        name: str,
        personal_number: str,
        email: str = "",
        phone: str = "",
    ) -> str:
        result = self._post(
            f"/v1/debtors/{self._creditor_id}",
            {
                "Name": name,
                "OrgNo": personal_number,
                "DebtorType": "Private",
                "ExternalId": member_id,
                "Email": email,
                "Phone": phone,
            },
        )
        return result.get("PublicId", "")


class BillectaMandateAdapter:
    def __init__(self, client: BillectaClient) -> None:
        self._client = client
        self._mandates: dict[str, AutogiroMandate] = {}
        self._contract_map: dict[str, str] = {}  # mandate_id → billecta contract_id

    def create_mandate(self, mandate: AutogiroMandate) -> AutogiroMandate:
        mandate.created_at = _now()
        self._mandates[mandate.mandate_id] = mandate
        return mandate

    def activate_mandate(self, mandate_id: str) -> AutogiroMandate:
        m = self._mandates[mandate_id]
        contract_id = self._client.create_recurring_autogiro(
            debtor_id=m.member_id,
            amount_sek=m.amount_sek,
            description=f"Medlemsavgift — {m.church_id}",
        )
        self._contract_map[mandate_id] = contract_id
        self._client.resume_contract(contract_id)
        m.status = MandateStatus.ACTIVE
        m.activated_at = _now()
        return m

    def revoke_mandate(self, mandate_id: str) -> AutogiroMandate:
        m = self._mandates[mandate_id]
        m.status = MandateStatus.REVOKED
        m.revoked_at = _now()
        return m

    def get_mandate(self, mandate_id: str) -> AutogiroMandate | None:
        return self._mandates.get(mandate_id)

    def list_active_mandates(self, church_id: str) -> list[AutogiroMandate]:
        return [m for m in self._mandates.values()
                if m.church_id == church_id and m.status == MandateStatus.ACTIVE]

    def list_member_mandates(self, member_id: str) -> list[AutogiroMandate]:
        return [m for m in self._mandates.values() if m.member_id == member_id]


class BillectaPaymentAdapter:
    def __init__(self, client: BillectaClient) -> None:
        self._client = client
        self._payments: dict[str, Payment] = {}

    def initiate_payment(self, payment: Payment) -> Payment:
        payment.created_at = _now()
        self._payments[payment.payment_id] = payment
        return payment

    def complete_payment(self, payment_id: str, reference: str) -> Payment:
        p = self._payments[payment_id]
        p.status = PaymentStatus.COMPLETED
        p.reference = reference
        p.completed_at = _now()
        return p

    def fail_payment(self, payment_id: str, reason: str) -> Payment:
        p = self._payments[payment_id]
        p.status = PaymentStatus.FAILED
        p.failed_reason = reason
        return p

    def get_payment(self, payment_id: str) -> Payment | None:
        return self._payments.get(payment_id)

    def list_payments(
        self,
        church_id: str,
        category: PaymentCategory | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Payment]:
        result = [p for p in self._payments.values() if p.church_id == church_id]
        if category:
            result = [p for p in result if p.category == category]
        return result

    def list_member_payments(self, member_id: str) -> list[Payment]:
        return [p for p in self._payments.values() if p.member_id == member_id]
