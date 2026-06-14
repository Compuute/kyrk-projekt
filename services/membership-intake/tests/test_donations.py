"""Donation receipt flow.

Public POST /donations registers a donor's reported gift together with an
email address. Nothing is sent at that point — the site cannot verify that a
Swish/bankgiro payment actually happened. A kassör (admin) later matches the
registration against the bank statement and verifies it, which is when the
receipt email goes out. Dismissing a registration sends nothing.
"""
from __future__ import annotations


ADMIN_TOKEN = "Bearer u1:nacka:admin"
VIEWER_TOKEN = "Bearer u2:nacka:viewer"
OTHER_CHURCH_ADMIN_TOKEN = "Bearer u3:stockholm:admin"
# In production, Zitadel sets actor.church_id to the organization id —
# the registry maps it back to the portal church slug.
ZITADEL_ORG_ADMIN_TOKEN = "Bearer u4:376720665740439161:admin"  # Nacka-kyrkan org


def _body(**overrides) -> dict:
    body = {
        "church_id": "nacka",
        "amount_sek": 200,
        "method": "swish",
        "email": "givare@example.se",
        "gdpr_consent": True,
    }
    body.update(overrides)
    return body


# ----------------------------------------------------------------- public POST


def test_register_donation_returns_202_pending(client, email_sender):
    r = client.post("/donations", json=_body())
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "pending_verification"
    assert data["donation_id"]
    # No receipt before the kassör has verified the gift.
    assert email_sender.sent == []


def test_register_donation_requires_gdpr_consent(client):
    r = client.post("/donations", json=_body(gdpr_consent=False))
    assert r.status_code == 400


def test_register_donation_rejects_invalid_email(client):
    r = client.post("/donations", json=_body(email="not-an-email"))
    assert r.status_code == 422


def test_register_donation_rejects_unknown_method(client):
    r = client.post("/donations", json=_body(method="kontant"))
    assert r.status_code == 422


def test_register_donation_rejects_silly_amounts(client):
    assert client.post("/donations", json=_body(amount_sek=0)).status_code == 422
    assert client.post("/donations", json=_body(amount_sek=1_000_000)).status_code == 422


def test_register_donation_unknown_church_rejected(client):
    r = client.post("/donations", json=_body(church_id="okänd-kyrka"))
    assert r.status_code == 400


def test_register_donation_is_rate_limited(client):
    for _ in range(3):
        assert client.post("/donations", json=_body()).status_code == 202
    assert client.post("/donations", json=_body()).status_code == 429


# ------------------------------------------------------------------ admin list


def test_list_pending_requires_auth(client):
    assert client.get("/donations").status_code == 401


def test_list_pending_requires_admin_role(client):
    r = client.get("/donations", headers={"Authorization": VIEWER_TOKEN})
    assert r.status_code == 403


def test_list_pending_masks_email(client):
    client.post("/donations", json=_body())
    r = client.get("/donations", headers={"Authorization": ADMIN_TOKEN})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["amount_sek"] == 200
    assert "givare@example.se" not in str(items[0])
    assert items[0]["email_masked"].startswith("g")
    assert "***" in items[0]["email_masked"]


def test_list_pending_is_scoped_to_actor_church(client):
    client.post("/donations", json=_body())
    r = client.get("/donations", headers={"Authorization": OTHER_CHURCH_ADMIN_TOKEN})
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------- verify


def _register(client) -> str:
    return client.post("/donations", json=_body()).json()["donation_id"]


def test_verify_sends_receipt_and_marks_verified(client, email_sender):
    donation_id = _register(client)
    r = client.post(
        f"/donations/{donation_id}/verify", headers={"Authorization": ADMIN_TOKEN}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "verified"
    assert data["receipt_number"].startswith("GK-")

    assert len(email_sender.sent) == 1
    receipt = email_sender.sent[0]
    assert receipt.to_email == "givare@example.se"
    assert receipt.amount_sek == 200
    assert receipt.receipt_number == data["receipt_number"]
    assert receipt.church_org_number == "802492-9237"
    assert "Abune Tekle Haymanot" in receipt.church_name


def test_verify_redacts_email_after_receipt_sent(client, donation_repo):
    donation_id = _register(client)
    client.post(f"/donations/{donation_id}/verify", headers={"Authorization": ADMIN_TOKEN})
    stored = donation_repo.get(donation_id)
    assert "givare@example.se" not in stored.email


def test_verify_twice_conflicts(client, email_sender):
    donation_id = _register(client)
    client.post(f"/donations/{donation_id}/verify", headers={"Authorization": ADMIN_TOKEN})
    r = client.post(
        f"/donations/{donation_id}/verify", headers={"Authorization": ADMIN_TOKEN}
    )
    assert r.status_code == 409
    assert len(email_sender.sent) == 1  # no duplicate receipt


def test_verify_scoped_to_actor_church(client, email_sender):
    donation_id = _register(client)
    r = client.post(
        f"/donations/{donation_id}/verify",
        headers={"Authorization": OTHER_CHURCH_ADMIN_TOKEN},
    )
    assert r.status_code == 404
    assert email_sender.sent == []


def test_verify_unknown_donation_404(client):
    r = client.post("/donations/finns-inte/verify", headers={"Authorization": ADMIN_TOKEN})
    assert r.status_code == 404


def test_verify_when_email_delivery_fails_keeps_donation_pending(client, email_sender):
    email_sender.fail_next = True
    donation_id = _register(client)
    r = client.post(
        f"/donations/{donation_id}/verify", headers={"Authorization": ADMIN_TOKEN}
    )
    assert r.status_code == 502
    # Still pending — the kassör can retry once the email provider is back.
    r = client.get("/donations", headers={"Authorization": ADMIN_TOKEN})
    assert len(r.json()) == 1


# ------------------------------------------------- Zitadel org-id resolution


def test_zitadel_org_admin_sees_nacka_pending(client):
    client.post("/donations", json=_body())
    r = client.get("/donations", headers={"Authorization": ZITADEL_ORG_ADMIN_TOKEN})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_zitadel_org_admin_can_verify(client, email_sender):
    donation_id = _register(client)
    r = client.post(
        f"/donations/{donation_id}/verify",
        headers={"Authorization": ZITADEL_ORG_ADMIN_TOKEN},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "verified"
    assert len(email_sender.sent) == 1


def test_unknown_org_id_sees_nothing(client):
    client.post("/donations", json=_body())
    r = client.get(
        "/donations", headers={"Authorization": "Bearer u5:999999999999:admin"}
    )
    assert r.status_code == 200
    assert r.json() == []


# --------------------------------------------------------------------- dismiss


def test_dismiss_sends_nothing_and_removes_from_pending(client, email_sender):
    donation_id = _register(client)
    r = client.post(
        f"/donations/{donation_id}/dismiss", headers={"Authorization": ADMIN_TOKEN}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "dismissed"
    assert email_sender.sent == []
    r = client.get("/donations", headers={"Authorization": ADMIN_TOKEN})
    assert r.json() == []
