"""Payment ports — vendor-agnostic interfaces for recurring and one-time payments.

Supports two flows:
  1. Autogiro: recurring membership fees (200 kr/mån) via Bankgirot
  2. Swish:    one-time service payments (tezkar, donations, certificates)

The ports define WHAT the system needs. Adapters (autogiro_adapter.py,
swish_adapter.py, fake_payment.py) define HOW — swap providers without
touching domain logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Protocol
from uuid import uuid4


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class PaymentMethod(str, Enum):
    AUTOGIRO = "autogiro"
    SWISH = "swish"
    MANUAL = "manual"  # cash / bankgiro inbetalning


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class MandateStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"
    FAILED = "failed"


class PaymentCategory(str, Enum):
    MEMBERSHIP_FEE = "membership_fee"
    TEZKAR = "tezkar"
    DONATION = "donation"
    CERTIFICATE = "certificate"
    SUNDAY_SCHOOL = "sunday_school"
    BUILDING_FUND = "building_fund"


# ---------------------------------------------------------------------------
# Domain entities
# ---------------------------------------------------------------------------

@dataclass
class AutogiroMandate:
    member_id: str
    church_id: str
    amount_sek: int  # öre ej — hela kronor
    bankgiro_number: str = ""
    mandate_id: str = field(default_factory=lambda: str(uuid4()))
    status: MandateStatus = MandateStatus.PENDING
    created_at: datetime | None = None
    activated_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass
class Payment:
    member_id: str
    church_id: str
    amount_sek: int
    category: PaymentCategory
    method: PaymentMethod
    reference: str = ""  # extern referens (Swish callback, autogiro batch)
    description: str = ""
    payment_id: str = field(default_factory=lambda: str(uuid4()))
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime | None = None
    completed_at: datetime | None = None
    failed_reason: str = ""


@dataclass
class PaymentSummary:
    """Aggregerad betalningsstatistik — bankunderlag för lånansökan."""
    church_id: str
    period_start: date
    period_end: date
    total_members: int = 0
    paying_members: int = 0
    total_collected_sek: int = 0
    avg_monthly_income_sek: int = 0
    payment_regularity_pct: float = 0.0  # % som betalat i tid
    active_mandates: int = 0
    failed_payments: int = 0
    categories: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Port: Mandate management (Autogiro)
# ---------------------------------------------------------------------------

class MandatePort(Protocol):
    def create_mandate(self, mandate: AutogiroMandate) -> AutogiroMandate: ...
    def activate_mandate(self, mandate_id: str) -> AutogiroMandate: ...
    def revoke_mandate(self, mandate_id: str) -> AutogiroMandate: ...
    def get_mandate(self, mandate_id: str) -> AutogiroMandate | None: ...
    def list_active_mandates(self, church_id: str) -> list[AutogiroMandate]: ...
    def list_member_mandates(self, member_id: str) -> list[AutogiroMandate]: ...


# ---------------------------------------------------------------------------
# Port: Payment processing (Swish + Autogiro callbacks)
# ---------------------------------------------------------------------------

class PaymentPort(Protocol):
    def initiate_payment(self, payment: Payment) -> Payment: ...
    def complete_payment(self, payment_id: str, reference: str) -> Payment: ...
    def fail_payment(self, payment_id: str, reason: str) -> Payment: ...
    def get_payment(self, payment_id: str) -> Payment | None: ...
    def list_payments(
        self,
        church_id: str,
        category: PaymentCategory | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Payment]: ...
    def list_member_payments(self, member_id: str) -> list[Payment]: ...


# ---------------------------------------------------------------------------
# Port: Swish integration
# ---------------------------------------------------------------------------

class SwishPort(Protocol):
    """Swish Commerce API — payment requests + callbacks."""
    def create_payment_request(
        self,
        amount_sek: int,
        phone_number: str,
        message: str,
        callback_url: str,
    ) -> str:
        """Returns Swish payment request ID."""
        ...

    def check_payment_status(self, request_id: str) -> PaymentStatus: ...

    def refund(self, original_request_id: str, amount_sek: int) -> str: ...


# ---------------------------------------------------------------------------
# Port: Bank reporting (lånunderlag)
# ---------------------------------------------------------------------------

class BankReportPort(Protocol):
    """Generera rapporter som banken vill se för lånansökan."""
    def generate_summary(
        self,
        church_id: str,
        period_start: date,
        period_end: date,
    ) -> PaymentSummary: ...

    def generate_member_payment_history(
        self,
        member_id: str,
    ) -> list[Payment]: ...

    def export_csv(
        self,
        church_id: str,
        period_start: date,
        period_end: date,
    ) -> bytes: ...
