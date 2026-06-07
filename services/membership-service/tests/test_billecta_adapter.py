"""Tests for the Billecta autogiro adapter — unit tests with mocked HTTP."""
from unittest.mock import MagicMock, patch
from datetime import date

from app.adapters.billecta_autogiro import (
    BillectaClient,
    BillectaMandateAdapter,
    BillectaPaymentAdapter,
)
from app.ports.payment import (
    AutogiroMandate,
    MandateStatus,
    Payment,
    PaymentCategory,
    PaymentMethod,
    PaymentStatus,
)


class TestBillectaClient:
    def test_init_from_env(self):
        client = BillectaClient(
            username="test", password="secret", creditor_public_id="cred-123",
        )
        assert client._username == "test"
        assert client._creditor_id == "cred-123"

    @patch("app.adapters.billecta_autogiro.httpx.post")
    def test_authenticate(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"SecureToken": "tok-abc"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = BillectaClient(username="u", password="p")
        token = client._authenticate()
        assert token == "tok-abc"
        mock_post.assert_called_once()

    @patch("app.adapters.billecta_autogiro.httpx.post")
    def test_create_debtor(self, mock_post):
        mock_auth = MagicMock()
        mock_auth.json.return_value = {"SecureToken": "tok"}
        mock_auth.raise_for_status = MagicMock()

        mock_create = MagicMock()
        mock_create.json.return_value = {"PublicId": "debtor-xyz"}
        mock_create.raise_for_status = MagicMock()

        mock_post.side_effect = [mock_auth, mock_create]

        client = BillectaClient(username="u", password="p", creditor_public_id="c")
        debtor_id = client.create_debtor(
            member_id="m1", name="Test Person", personal_number="199001011234",
        )
        assert debtor_id == "debtor-xyz"


class TestBillectaMandateAdapter:
    def _make_adapter(self):
        client = MagicMock(spec=BillectaClient)
        client.create_recurring_autogiro.return_value = "contract-123"
        client.resume_contract.return_value = None
        return BillectaMandateAdapter(client), client

    def test_create_mandate(self):
        adapter, _ = self._make_adapter()
        m = adapter.create_mandate(AutogiroMandate(
            member_id="m1", church_id="nacka", amount_sek=200,
        ))
        assert m.status == MandateStatus.PENDING
        assert m.created_at is not None

    def test_activate_calls_billecta(self):
        adapter, client = self._make_adapter()
        m = adapter.create_mandate(AutogiroMandate(
            member_id="m1", church_id="nacka", amount_sek=200,
        ))
        activated = adapter.activate_mandate(m.mandate_id)
        assert activated.status == MandateStatus.ACTIVE
        client.create_recurring_autogiro.assert_called_once_with(
            debtor_id="m1", amount_sek=200, description="Medlemsavgift — nacka",
        )
        client.resume_contract.assert_called_once_with("contract-123")

    def test_revoke_mandate(self):
        adapter, _ = self._make_adapter()
        m = adapter.create_mandate(AutogiroMandate(
            member_id="m1", church_id="nacka", amount_sek=200,
        ))
        adapter.activate_mandate(m.mandate_id)
        revoked = adapter.revoke_mandate(m.mandate_id)
        assert revoked.status == MandateStatus.REVOKED

    def test_list_active_per_church(self):
        adapter, _ = self._make_adapter()
        m1 = adapter.create_mandate(AutogiroMandate(
            member_id="m1", church_id="nacka", amount_sek=200,
        ))
        m2 = adapter.create_mandate(AutogiroMandate(
            member_id="m2", church_id="goteborg", amount_sek=200,
        ))
        adapter.activate_mandate(m1.mandate_id)
        adapter.activate_mandate(m2.mandate_id)
        assert len(adapter.list_active_mandates("nacka")) == 1
        assert len(adapter.list_active_mandates("goteborg")) == 1

    def test_family_mandate_500kr(self):
        adapter, client = self._make_adapter()
        m = adapter.create_mandate(AutogiroMandate(
            member_id="family1", church_id="nacka", amount_sek=500,
        ))
        adapter.activate_mandate(m.mandate_id)
        client.create_recurring_autogiro.assert_called_once_with(
            debtor_id="family1", amount_sek=500, description="Medlemsavgift — nacka",
        )


class TestBillectaPaymentAdapter:
    def test_initiate_and_complete(self):
        client = MagicMock(spec=BillectaClient)
        adapter = BillectaPaymentAdapter(client)
        p = adapter.initiate_payment(Payment(
            member_id="m1", church_id="nacka", amount_sek=200,
            category=PaymentCategory.MEMBERSHIP_FEE, method=PaymentMethod.AUTOGIRO,
        ))
        assert p.status == PaymentStatus.PENDING
        completed = adapter.complete_payment(p.payment_id, "BG-REF-001")
        assert completed.status == PaymentStatus.COMPLETED

    def test_multi_church_payments(self):
        client = MagicMock(spec=BillectaClient)
        adapter = BillectaPaymentAdapter(client)
        adapter.initiate_payment(Payment(
            member_id="m1", church_id="nacka", amount_sek=200,
            category=PaymentCategory.MEMBERSHIP_FEE, method=PaymentMethod.AUTOGIRO,
        ))
        adapter.initiate_payment(Payment(
            member_id="m2", church_id="goteborg", amount_sek=500,
            category=PaymentCategory.MEMBERSHIP_FEE, method=PaymentMethod.AUTOGIRO,
        ))
        assert len(adapter.list_payments("nacka")) == 1
        assert len(adapter.list_payments("goteborg")) == 1
