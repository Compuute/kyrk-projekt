from datetime import datetime, timezone

_PNR = ["19800101-1231","19810101-1230","19820101-1239","19830101-1238","19840101-1237","19850101-1236","19860101-1235","19870101-1234","19880101-1233","19890101-1232"]
_pi = 0
def _next_pnr():
    global _pi; pnr = _PNR[_pi % len(_PNR)]; _pi += 1; return pnr

def _body(**overrides):
    body = {
        "church_id": "c1",
        "first_name": "Anna",
        "last_name": "Andersson",
        "phone": "+46701234567",
        "email": "anna@example.se",
        "personal_number": _next_pnr(),
        "gdpr_consent": True,
        "consent_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    body.update(overrides)
    return body


def _headers(role: str, church: str = "c1", user: str = "u-admin") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}:{church}:{role}"}


def _submit(client, **overrides) -> str:
    r = client.post("/intake", json=_body(**overrides))
    assert r.status_code == 202, r.text
    return r.json()["submission_id"]


# ---------------------------------------------------------------- list API


def test_list_pending_requires_auth(client):
    assert client.get("/submissions").status_code == 401


def test_list_pending_viewer_forbidden(client):
    r = client.get("/submissions", headers=_headers("viewer"))
    assert r.status_code == 403


def test_list_pending_returns_submitted_items(client):
    sid = _submit(client)
    r = client.get("/submissions", headers=_headers("admin"))
    assert r.status_code == 200
    ids = [item["submission_id"] for item in r.json()]
    assert sid in ids


def test_list_pending_scoped_per_church(client):
    _submit(client, church_id="c1")
    _submit(client, church_id="c2")
    r = client.get("/submissions", headers=_headers("admin", church="c1"))
    assert r.status_code == 200
    assert all(item["church_id"] == "c1" for item in r.json())


# ------------------------------------------------- church-tax (kyrkoskatt)


def test_already_member_tax_switch_is_captured(client):
    # "Redan medlem — vill bara byta kyrkoskatt": no new membership fee, but
    # the tax-switch intent + Skatteverket consent must reach the admin list.
    sid = _submit(
        client,
        action="already_member",
        tax_consent=True,
        monthly_fee_sek=0,
    )
    r = client.get("/submissions", headers=_headers("admin"))
    assert r.status_code == 200
    item = next(i for i in r.json() if i["submission_id"] == sid)
    assert item["action"] == "already_member"
    assert item["tax_consent"] is True


def test_submission_action_defaults_to_register_only(client):
    sid = _submit(client)
    r = client.get("/submissions", headers=_headers("admin"))
    item = next(i for i in r.json() if i["submission_id"] == sid)
    assert item["action"] == "register_only"
    assert item["tax_consent"] is False


def test_invalid_action_rejected(client):
    r = client.post("/intake", json=_body(action="not-a-real-action"))
    assert r.status_code == 422


# ------------------------------------------------------------- approve API


def test_approve_requires_auth(client):
    sid = _submit(client)
    assert client.post(f"/submissions/{sid}/approve").status_code == 401


def test_approve_viewer_forbidden(client):
    sid = _submit(client)
    r = client.post(f"/submissions/{sid}/approve", headers=_headers("viewer"))
    assert r.status_code == 403


def test_approve_happy_path(client, membership_client):
    sid = _submit(client)
    r = client.post(f"/submissions/{sid}/approve", headers=_headers("admin"))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "approved"
    assert data["created_member_id"]
    # The bearer token was forwarded to the downstream client.
    assert len(membership_client.calls) == 1
    assert membership_client.calls[0][0] == "u-admin:c1:admin"


def test_approve_unknown_submission_404(client):
    r = client.post("/submissions/does-not-exist/approve", headers=_headers("admin"))
    assert r.status_code == 404


def test_approve_twice_409(client):
    sid = _submit(client)
    client.post(f"/submissions/{sid}/approve", headers=_headers("admin"))
    r = client.post(f"/submissions/{sid}/approve", headers=_headers("admin"))
    assert r.status_code == 409


# ------------------------------------------------- Zitadel org-id resolution

# In production, Zitadel sets actor.church_id to the organization id —
# the registry maps it back to the portal church slug.
ZITADEL_ORG_ADMIN = {"Authorization": "Bearer u4:376720665740439161:admin"}   # Nacka-kyrkan
STOCKHOLM_ORG_ADMIN = {"Authorization": "Bearer u6:376720690671258678:admin"} # Hagsätra-kyrkan
UNKNOWN_ORG_ADMIN = {"Authorization": "Bearer u5:999999999999:admin"}


def test_zitadel_org_admin_sees_nacka_pending(client):
    sid = _submit(client, church_id="nacka")
    r = client.get("/submissions", headers=ZITADEL_ORG_ADMIN)
    assert r.status_code == 200
    assert [item["submission_id"] for item in r.json()] == [sid]


def test_zitadel_org_admin_can_approve(client):
    sid = _submit(client, church_id="nacka")
    r = client.post(f"/submissions/{sid}/approve", headers=ZITADEL_ORG_ADMIN)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"


def test_zitadel_org_admin_can_reject(client):
    sid = _submit(client, church_id="nacka")
    r = client.post(f"/submissions/{sid}/reject", headers=ZITADEL_ORG_ADMIN)
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_per_church_orgs_are_isolated(client):
    # Each church has its own Zitadel org. An admin in the Hagsätra org
    # (Medhane Alem/stockholm) sees only stockholm's submissions, never nacka's.
    nacka_sid = _submit(client, church_id="nacka")
    sthlm_sid = _submit(client, church_id="stockholm")

    sthlm = client.get("/submissions", headers=STOCKHOLM_ORG_ADMIN)
    assert sthlm.status_code == 200
    assert [item["submission_id"] for item in sthlm.json()] == [sthlm_sid]

    nacka = client.get("/submissions", headers=ZITADEL_ORG_ADMIN)
    assert [item["submission_id"] for item in nacka.json()] == [nacka_sid]


def test_unknown_org_id_sees_nothing(client):
    _submit(client, church_id="nacka")
    r = client.get("/submissions", headers=UNKNOWN_ORG_ADMIN)
    assert r.status_code == 200
    assert r.json() == []


def test_unknown_org_id_cannot_approve(client):
    sid = _submit(client, church_id="nacka")
    r = client.post(f"/submissions/{sid}/approve", headers=UNKNOWN_ORG_ADMIN)
    assert r.status_code == 404


# -------------------------------------------------------------- reject API


def test_reject_happy_path(client):
    sid = _submit(client)
    r = client.post(f"/submissions/{sid}/reject", headers=_headers("pastor"))
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_reject_viewer_forbidden(client):
    sid = _submit(client)
    r = client.post(f"/submissions/{sid}/reject", headers=_headers("viewer"))
    assert r.status_code == 403
