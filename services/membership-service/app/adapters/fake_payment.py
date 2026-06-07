"""In-memory payment adapters for dev/test. No external dependencies."""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.ports.payment import (
    AutogiroMandate,
    BankReportPort,
    MandatePort,
    MandateStatus,
    Payment,
    PaymentCategory,
    PaymentPort,
    PaymentStatus,
    PaymentSummary,
    SwishPort,
)
from app.ports.tezkar import TezkarPort, TezkarRequest, TezkarStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FakeMandateAdapter:
    def __init__(self) -> None:
        self._mandates: dict[str, AutogiroMandate] = {}

    def create_mandate(self, mandate: AutogiroMandate) -> AutogiroMandate:
        mandate.created_at = _now()
        self._mandates[mandate.mandate_id] = mandate
        return mandate

    def activate_mandate(self, mandate_id: str) -> AutogiroMandate:
        m = self._mandates[mandate_id]
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


class FakePaymentAdapter:
    def __init__(self) -> None:
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


class FakeSwishAdapter:
    def __init__(self) -> None:
        self._requests: dict[str, PaymentStatus] = {}
        self._counter = 0

    def create_payment_request(
        self, amount_sek: int, phone_number: str, message: str, callback_url: str,
    ) -> str:
        self._counter += 1
        req_id = f"SWISH-FAKE-{self._counter:06d}"
        self._requests[req_id] = PaymentStatus.COMPLETED
        return req_id

    def check_payment_status(self, request_id: str) -> PaymentStatus:
        return self._requests.get(request_id, PaymentStatus.FAILED)

    def refund(self, original_request_id: str, amount_sek: int) -> str:
        return f"REFUND-{original_request_id}"


class FakeBankReportAdapter:
    def __init__(self, payment_adapter: FakePaymentAdapter, mandate_adapter: FakeMandateAdapter) -> None:
        self._payments = payment_adapter
        self._mandates = mandate_adapter

    def generate_summary(
        self, church_id: str, period_start: date, period_end: date,
    ) -> PaymentSummary:
        payments = self._payments.list_payments(church_id)
        completed = [p for p in payments if p.status == PaymentStatus.COMPLETED]
        failed = [p for p in payments if p.status == PaymentStatus.FAILED]
        members = set(p.member_id for p in completed)
        total = sum(p.amount_sek for p in completed)
        mandates = self._mandates.list_active_mandates(church_id)
        months = max(1, (period_end - period_start).days // 30)
        categories = {}
        for p in completed:
            categories[p.category.value] = categories.get(p.category.value, 0) + p.amount_sek
        return PaymentSummary(
            church_id=church_id,
            period_start=period_start,
            period_end=period_end,
            total_members=len(members),
            paying_members=len(members),
            total_collected_sek=total,
            avg_monthly_income_sek=total // months,
            payment_regularity_pct=100.0 if not failed else
                len(completed) / max(1, len(completed) + len(failed)) * 100,
            active_mandates=len(mandates),
            failed_payments=len(failed),
            categories=categories,
        )

    def generate_member_payment_history(self, member_id: str) -> list[Payment]:
        return self._payments.list_member_payments(member_id)

    def export_csv(self, church_id: str, period_start: date, period_end: date) -> bytes:
        payments = self._payments.list_payments(church_id)
        lines = ["date,member_id,amount_sek,category,status"]
        for p in payments:
            lines.append(f"{p.created_at},{p.member_id},{p.amount_sek},{p.category.value},{p.status.value}")
        return "\n".join(lines).encode("utf-8")


class FakeTezkarAdapter:
    def __init__(self) -> None:
        self._requests: dict[str, TezkarRequest] = {}

    def create_request(self, request: TezkarRequest) -> TezkarRequest:
        request.created_at = _now()
        self._requests[request.tezkar_id] = request
        return request

    def mark_paid(self, tezkar_id: str, payment_ref: str) -> TezkarRequest:
        r = self._requests[tezkar_id]
        r.status = TezkarStatus.PAID
        r.payment_reference = payment_ref
        return r

    def mark_scheduled(self, tezkar_id: str) -> TezkarRequest:
        r = self._requests[tezkar_id]
        r.status = TezkarStatus.SCHEDULED
        return r

    def mark_completed(self, tezkar_id: str) -> TezkarRequest:
        r = self._requests[tezkar_id]
        r.status = TezkarStatus.COMPLETED
        return r

    def cancel(self, tezkar_id: str) -> TezkarRequest:
        r = self._requests[tezkar_id]
        r.status = TezkarStatus.CANCELLED
        return r

    def list_upcoming(self, church_id: str) -> list[TezkarRequest]:
        return [r for r in self._requests.values()
                if r.church_id == church_id
                and r.status in (TezkarStatus.PAID, TezkarStatus.SCHEDULED)]

    def list_by_member(self, member_id: str) -> list[TezkarRequest]:
        return [r for r in self._requests.values()
                if r.requester_member_id == member_id]

    def compute_schedule(self, death_date: date) -> list[tuple[date, str, str]]:
        from app.ports.tezkar import compute_memorial_dates
        return compute_memorial_dates(death_date)
