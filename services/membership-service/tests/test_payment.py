"""Tests for payment domain — autogiro mandates, Swish, bank reports, tezkar."""
from datetime import date, datetime, timezone

from app.adapters.fake_payment import (
    FakeBankReportAdapter,
    FakeMandateAdapter,
    FakePaymentAdapter,
    FakeSwishAdapter,
    FakeTezkarAdapter,
)
from app.ports.payment import (
    AutogiroMandate,
    MandateStatus,
    Payment,
    PaymentCategory,
    PaymentMethod,
    PaymentStatus,
)
from app.ports.tezkar import TezkarRequest, TezkarStatus, compute_memorial_dates


# ---------------------------------------------------------------------------
# Autogiro mandates
# ---------------------------------------------------------------------------

class TestAutogiroMandate:
    def test_create_and_activate(self):
        adapter = FakeMandateAdapter()
        m = adapter.create_mandate(AutogiroMandate(
            member_id="m1", church_id="nacka", amount_sek=200,
        ))
        assert m.status == MandateStatus.PENDING
        assert m.created_at is not None

        activated = adapter.activate_mandate(m.mandate_id)
        assert activated.status == MandateStatus.ACTIVE
        assert activated.activated_at is not None

    def test_revoke_mandate(self):
        adapter = FakeMandateAdapter()
        m = adapter.create_mandate(AutogiroMandate(
            member_id="m1", church_id="nacka", amount_sek=200,
        ))
        adapter.activate_mandate(m.mandate_id)
        revoked = adapter.revoke_mandate(m.mandate_id)
        assert revoked.status == MandateStatus.REVOKED

    def test_list_active_mandates(self):
        adapter = FakeMandateAdapter()
        m1 = adapter.create_mandate(AutogiroMandate(
            member_id="m1", church_id="nacka", amount_sek=200,
        ))
        m2 = adapter.create_mandate(AutogiroMandate(
            member_id="m2", church_id="nacka", amount_sek=200,
        ))
        adapter.create_mandate(AutogiroMandate(
            member_id="m3", church_id="goteborg", amount_sek=200,
        ))
        adapter.activate_mandate(m1.mandate_id)
        adapter.activate_mandate(m2.mandate_id)

        active = adapter.list_active_mandates("nacka")
        assert len(active) == 2

    def test_amount_200kr(self):
        m = AutogiroMandate(member_id="m1", church_id="nacka", amount_sek=200)
        assert m.amount_sek == 200


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class TestPayment:
    def test_initiate_and_complete(self):
        adapter = FakePaymentAdapter()
        p = adapter.initiate_payment(Payment(
            member_id="m1", church_id="nacka", amount_sek=200,
            category=PaymentCategory.MEMBERSHIP_FEE,
            method=PaymentMethod.AUTOGIRO,
        ))
        assert p.status == PaymentStatus.PENDING

        completed = adapter.complete_payment(p.payment_id, "BG-REF-001")
        assert completed.status == PaymentStatus.COMPLETED
        assert completed.reference == "BG-REF-001"

    def test_fail_payment(self):
        adapter = FakePaymentAdapter()
        p = adapter.initiate_payment(Payment(
            member_id="m1", church_id="nacka", amount_sek=200,
            category=PaymentCategory.MEMBERSHIP_FEE,
            method=PaymentMethod.AUTOGIRO,
        ))
        failed = adapter.fail_payment(p.payment_id, "insufficient funds")
        assert failed.status == PaymentStatus.FAILED
        assert failed.failed_reason == "insufficient funds"

    def test_list_by_category(self):
        adapter = FakePaymentAdapter()
        adapter.initiate_payment(Payment(
            member_id="m1", church_id="nacka", amount_sek=200,
            category=PaymentCategory.MEMBERSHIP_FEE, method=PaymentMethod.AUTOGIRO,
        ))
        adapter.initiate_payment(Payment(
            member_id="m1", church_id="nacka", amount_sek=500,
            category=PaymentCategory.TEZKAR, method=PaymentMethod.SWISH,
        ))
        fees = adapter.list_payments("nacka", category=PaymentCategory.MEMBERSHIP_FEE)
        assert len(fees) == 1
        assert fees[0].amount_sek == 200

    def test_all_categories_exist(self):
        categories = [c.value for c in PaymentCategory]
        assert "membership_fee" in categories
        assert "tezkar" in categories
        assert "donation" in categories
        assert "building_fund" in categories


# ---------------------------------------------------------------------------
# Swish
# ---------------------------------------------------------------------------

class TestSwish:
    def test_create_payment_request(self):
        adapter = FakeSwishAdapter()
        req_id = adapter.create_payment_request(
            amount_sek=500, phone_number="+46701234567",
            message="Tezkar — Abebe", callback_url="https://example.com/callback",
        )
        assert req_id.startswith("SWISH-FAKE-")
        assert adapter.check_payment_status(req_id) == PaymentStatus.COMPLETED

    def test_refund(self):
        adapter = FakeSwishAdapter()
        req_id = adapter.create_payment_request(
            amount_sek=500, phone_number="+46701234567",
            message="test", callback_url="https://example.com/callback",
        )
        refund_id = adapter.refund(req_id, 500)
        assert refund_id.startswith("REFUND-")


# ---------------------------------------------------------------------------
# Bank report (lånunderlag)
# ---------------------------------------------------------------------------

class TestBankReport:
    def test_generate_summary(self):
        mandates = FakeMandateAdapter()
        payments = FakePaymentAdapter()
        report = FakeBankReportAdapter(payments, mandates)

        m1 = mandates.create_mandate(AutogiroMandate(
            member_id="m1", church_id="nacka", amount_sek=200,
        ))
        mandates.activate_mandate(m1.mandate_id)

        for i in range(12):
            p = payments.initiate_payment(Payment(
                member_id="m1", church_id="nacka", amount_sek=200,
                category=PaymentCategory.MEMBERSHIP_FEE,
                method=PaymentMethod.AUTOGIRO,
            ))
            payments.complete_payment(p.payment_id, f"BG-{i}")

        summary = report.generate_summary(
            "nacka", date(2025, 1, 1), date(2025, 12, 31),
        )
        assert summary.total_collected_sek == 2400
        assert summary.paying_members == 1
        assert summary.active_mandates == 1
        assert summary.payment_regularity_pct == 100.0

    def test_export_csv(self):
        payments = FakePaymentAdapter()
        mandates = FakeMandateAdapter()
        report = FakeBankReportAdapter(payments, mandates)

        p = payments.initiate_payment(Payment(
            member_id="m1", church_id="nacka", amount_sek=200,
            category=PaymentCategory.MEMBERSHIP_FEE,
            method=PaymentMethod.AUTOGIRO,
        ))
        payments.complete_payment(p.payment_id, "BG-001")

        csv = report.export_csv("nacka", date(2025, 1, 1), date(2025, 12, 31))
        lines = csv.decode("utf-8").split("\n")
        assert lines[0] == "date,member_id,amount_sek,category,status"
        assert "200" in lines[1]

    def test_revenue_projection_3250_members(self):
        """3,250 members × 200 kr/mån = 7.8M SEK/år — bankunderlag."""
        members = 3250
        monthly_fee = 200
        annual = members * monthly_fee * 12
        assert annual == 7_800_000


# ---------------------------------------------------------------------------
# Tezkar (memorial prayers)
# ---------------------------------------------------------------------------

class TestTezkar:
    def test_create_and_mark_paid(self):
        adapter = FakeTezkarAdapter()
        req = adapter.create_request(TezkarRequest(
            church_id="nacka",
            requester_member_id="m1",
            deceased_name="Abebe Kebede",
            deceased_name_amharic="አበበ ከበደ",
            death_date=date(2025, 6, 1),
            memorial_type="arbaa",
            requested_date=date(2025, 7, 11),
            amount_sek=500,
        ))
        assert req.status == TezkarStatus.REQUESTED

        paid = adapter.mark_paid(req.tezkar_id, "SWISH-001")
        assert paid.status == TezkarStatus.PAID

    def test_full_lifecycle(self):
        adapter = FakeTezkarAdapter()
        req = adapter.create_request(TezkarRequest(
            church_id="nacka",
            requester_member_id="m1",
            deceased_name="Abebe",
            memorial_type="seleste",
            amount_sek=300,
        ))
        adapter.mark_paid(req.tezkar_id, "SWISH-001")
        adapter.mark_scheduled(req.tezkar_id)
        completed = adapter.mark_completed(req.tezkar_id)
        assert completed.status == TezkarStatus.COMPLETED

    def test_list_upcoming(self):
        adapter = FakeTezkarAdapter()
        r1 = adapter.create_request(TezkarRequest(
            church_id="nacka", requester_member_id="m1",
            deceased_name="A", memorial_type="arbaa", amount_sek=500,
        ))
        adapter.mark_paid(r1.tezkar_id, "SWISH-001")

        r2 = adapter.create_request(TezkarRequest(
            church_id="nacka", requester_member_id="m2",
            deceased_name="B", memorial_type="seleste", amount_sek=300,
        ))
        # r2 still REQUESTED, not paid

        upcoming = adapter.list_upcoming("nacka")
        assert len(upcoming) == 1

    def test_compute_memorial_dates(self):
        dates = compute_memorial_dates(date(2025, 6, 1))
        keys = [d[1] for d in dates]
        assert "seleste" in keys
        assert "arbaa" in keys
        assert "amet" in keys
        assert "tezkar_year_2" in keys
        assert len(dates) >= 7 + 6  # 7 initial + 6 yearly

    def test_memorial_day_40(self):
        dates = compute_memorial_dates(date(2025, 6, 1))
        arbaa = [d for d in dates if d[1] == "arbaa"][0]
        assert arbaa[0] == date(2025, 7, 11)  # 40 days after June 1
