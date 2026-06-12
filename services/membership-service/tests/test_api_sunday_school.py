"""Tests for Sunday school API: groups, enrollments, attendance.

Groups are courses (Grunderna, Fortsättning, Krar, Begena, ...) — a child
can be enrolled in several groups, and a teacher can teach several groups.
Teachers only see and record attendance for their own groups; staff
(admin/pastor/editor) manage groups and enrollments.
"""
from __future__ import annotations


def _headers(role: str, church: str = "c1", user: str = "u1") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}:{church}:{role}"}


def _group(group_id: str = "g-grunderna", church_id: str = "c1", teachers=None):
    return {
        "group_id": group_id,
        "church_id": church_id,
        "name": "Grunderna",
        "description": "Söndagsskolans grundkurs",
        "teacher_user_ids": teachers if teachers is not None else ["t1"],
    }


def _enrollment(child: str = "Maria", birth_year: int = 2017, consent: bool = True):
    return {
        "child_first_name": child,
        "child_last_name": "Tesfaye",
        "birth_year": birth_year,
        "guardian_name": "Sara Tesfaye",
        "guardian_phone": "+46700000001",
        "guardian_consent": consent,
    }


def _create_group(client, body=None):
    r = client.post("/sunday-school/groups", json=body or _group(), headers=_headers("admin"))
    assert r.status_code == 201, r.text
    return r.json()


def _enroll(client, group_id: str, body=None):
    r = client.post(
        f"/sunday-school/groups/{group_id}/enrollments",
        json=body or _enrollment(),
        headers=_headers("admin"),
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- auth basics


def test_groups_require_bearer(client):
    assert client.get("/sunday-school/groups").status_code == 401


def test_groups_reject_viewer(client):
    r = client.get("/sunday-school/groups", headers=_headers("viewer"))
    assert r.status_code == 403


def test_teacher_role_is_valid(client):
    r = client.get("/sunday-school/groups", headers=_headers("teacher", user="t1"))
    assert r.status_code == 200


# -------------------------------------------------------------------- groups


def test_admin_creates_group(client):
    created = _create_group(client)
    assert created["name"] == "Grunderna"
    assert created["teacher_user_ids"] == ["t1"]


def test_teacher_cannot_create_group(client):
    r = client.post("/sunday-school/groups", json=_group(), headers=_headers("teacher", user="t1"))
    assert r.status_code == 403


def test_create_group_rejects_church_mismatch(client):
    r = client.post(
        "/sunday-school/groups",
        json=_group(church_id="c2"),
        headers=_headers("admin", church="c1"),
    )
    assert r.status_code == 400


def test_teacher_lists_only_own_groups(client):
    _create_group(client, _group("g-grunderna", teachers=["t1"]))
    _create_group(client, _group("g-krar", teachers=["t2"]))
    _create_group(client, _group("g-begena", teachers=["t1", "t2"]))

    r = client.get("/sunday-school/groups", headers=_headers("teacher", user="t1"))
    assert r.status_code == 200
    ids = sorted(g["group_id"] for g in r.json())
    assert ids == ["g-begena", "g-grunderna"]

    r = client.get("/sunday-school/groups", headers=_headers("admin"))
    assert len(r.json()) == 3


def test_groups_are_church_isolated(client):
    _create_group(client)
    r = client.get("/sunday-school/groups", headers=_headers("admin", church="c2"))
    assert r.json() == []


# --------------------------------------------------------------- enrollments


def test_admin_enrolls_child(client):
    _create_group(client)
    created = _enroll(client, "g-grunderna")
    assert created["child_first_name"] == "Maria"
    assert created["group_id"] == "g-grunderna"
    assert created["enrollment_id"]


def test_enrollment_requires_guardian_consent(client):
    _create_group(client)
    r = client.post(
        "/sunday-school/groups/g-grunderna/enrollments",
        json=_enrollment(consent=False),
        headers=_headers("admin"),
    )
    assert r.status_code == 422
    assert "consent" in r.json()["detail"].lower()


def test_enrollment_unknown_group_404(client):
    r = client.post(
        "/sunday-school/groups/missing/enrollments",
        json=_enrollment(),
        headers=_headers("admin"),
    )
    assert r.status_code == 404


def test_child_can_be_enrolled_in_multiple_groups(client):
    _create_group(client, _group("g-grunderna", teachers=["t1"]))
    _create_group(client, _group("g-krar", teachers=["t2"]))
    _enroll(client, "g-grunderna")
    _enroll(client, "g-krar")

    r = client.get(
        "/sunday-school/groups/g-krar/enrollments", headers=_headers("teacher", user="t2")
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_teacher_cannot_view_other_groups_roster(client):
    _create_group(client, _group("g-grunderna", teachers=["t1"]))
    r = client.get(
        "/sunday-school/groups/g-grunderna/enrollments",
        headers=_headers("teacher", user="t2"),
    )
    assert r.status_code == 403


def test_teacher_enrolls_child_into_own_group(client):
    """A child not on the list is registered on the spot by the teacher."""
    _create_group(client, _group("g-grunderna", teachers=["t1"]))
    r = client.post(
        "/sunday-school/groups/g-grunderna/enrollments",
        json=_enrollment(),
        headers=_headers("teacher", user="t1"),
    )
    assert r.status_code == 201, r.text


def test_teacher_cannot_enroll_into_other_group(client):
    _create_group(client, _group("g-grunderna", teachers=["t1"]))
    r = client.post(
        "/sunday-school/groups/g-grunderna/enrollments",
        json=_enrollment(),
        headers=_headers("teacher", user="t2"),
    )
    assert r.status_code == 403


# ---------------------------------------------------------------- attendance


def _setup_group_with_children(client):
    _create_group(client, _group("g-grunderna", teachers=["t1"]))
    e1 = _enroll(client, "g-grunderna", _enrollment("Maria", 2017))
    e2 = _enroll(client, "g-grunderna", _enrollment("Dawit", 2012))
    e3 = _enroll(client, "g-grunderna", _enrollment("Ruth", 2019))
    return e1, e2, e3


def test_teacher_records_attendance_with_aggregate(client):
    e1, e2, e3 = _setup_group_with_children(client)
    r = client.post(
        "/sunday-school/groups/g-grunderna/attendance",
        json={
            "date": "2026-06-14",
            "present_enrollment_ids": [e1["enrollment_id"], e2["enrollment_id"]],
        },
        headers=_headers("teacher", user="t1"),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["participants_total"] == 2
    # Maria born 2017 → 9 år (7-12), Dawit born 2012 → 14 år (13-17)
    assert body["age_band_counts"]["7-12"] == 1
    assert body["age_band_counts"]["13-17"] == 1
    assert body["age_band_counts"]["0-6"] == 0
    assert body["registered_by_user_id"] == "t1"


def test_attendance_aggregate_has_no_names(client):
    """Zone boundary: the derived aggregate must never carry child names."""
    e1, _, _ = _setup_group_with_children(client)
    r = client.post(
        "/sunday-school/groups/g-grunderna/attendance",
        json={"date": "2026-06-14", "present_enrollment_ids": [e1["enrollment_id"]]},
        headers=_headers("teacher", user="t1"),
    )
    text = str(r.json().get("age_band_counts")) + str(r.json().get("participants_total"))
    assert "Maria" not in text


def test_teacher_cannot_record_other_groups_attendance(client):
    _setup_group_with_children(client)
    r = client.post(
        "/sunday-school/groups/g-grunderna/attendance",
        json={"date": "2026-06-14", "present_enrollment_ids": []},
        headers=_headers("teacher", user="t2"),
    )
    assert r.status_code == 403


def test_attendance_rejects_unknown_enrollment_ids(client):
    _setup_group_with_children(client)
    r = client.post(
        "/sunday-school/groups/g-grunderna/attendance",
        json={"date": "2026-06-14", "present_enrollment_ids": ["not-enrolled"]},
        headers=_headers("teacher", user="t1"),
    )
    assert r.status_code == 422


def test_attendance_same_date_upserts(client):
    e1, e2, _ = _setup_group_with_children(client)
    for ids in ([e1["enrollment_id"]], [e1["enrollment_id"], e2["enrollment_id"]]):
        r = client.post(
            "/sunday-school/groups/g-grunderna/attendance",
            json={"date": "2026-06-14", "present_enrollment_ids": ids},
            headers=_headers("teacher", user="t1"),
        )
        assert r.status_code == 201

    r = client.get(
        "/sunday-school/groups/g-grunderna/attendance",
        headers=_headers("teacher", user="t1"),
    )
    records = r.json()
    assert len(records) == 1
    assert records[0]["participants_total"] == 2


def test_attendance_history_supports_certificates(client):
    """Per-child attendance over time is the basis for level certificates."""
    e1, e2, _ = _setup_group_with_children(client)
    client.post(
        "/sunday-school/groups/g-grunderna/attendance",
        json={"date": "2026-06-07", "present_enrollment_ids": [e1["enrollment_id"]]},
        headers=_headers("teacher", user="t1"),
    )
    client.post(
        "/sunday-school/groups/g-grunderna/attendance",
        json={
            "date": "2026-06-14",
            "present_enrollment_ids": [e1["enrollment_id"], e2["enrollment_id"]],
        },
        headers=_headers("teacher", user="t1"),
    )
    r = client.get(
        "/sunday-school/groups/g-grunderna/attendance", headers=_headers("admin")
    )
    records = {rec["date"]: rec for rec in r.json()}
    assert e1["enrollment_id"] in records["2026-06-07"]["present_enrollment_ids"]
    assert len(records["2026-06-14"]["present_enrollment_ids"]) == 2


def test_attendance_church_isolated(client):
    _setup_group_with_children(client)
    r = client.get(
        "/sunday-school/groups/g-grunderna/attendance",
        headers=_headers("admin", church="c2"),
    )
    assert r.status_code == 404
