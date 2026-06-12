"""Sunday school teacher UI: group list, roster, attendance registration.

After attendance is saved in membership-service, the route reports the
derived aggregate (no names) to reporting-service so every lesson becomes
grant evidence automatically.
"""
from __future__ import annotations

import pytest

from app.ports.client_errors import ClientError
from app.ports.sunday_school import AttendanceRecord, SchoolEnrollment, SchoolGroup


@pytest.fixture
def teacher_client(client):
    client.cookies.set("kyrk_session", "t1:c1:teacher")
    return client


@pytest.fixture
def seeded_school(sunday_school):
    sunday_school.seed_group(SchoolGroup(
        group_id="g-grunderna", name="Grunderna",
        description="Grundkurs", teacher_user_ids=("t1",),
    ))
    sunday_school.seed_group(SchoolGroup(
        group_id="g-krar", name="Krar",
        description="Kralektioner", teacher_user_ids=("t2",),
    ))
    sunday_school.seed_enrollment("g-grunderna", SchoolEnrollment(
        enrollment_id="e1", child_first_name="Maria",
        child_last_name="Tesfaye", birth_year=2017,
    ))
    sunday_school.seed_enrollment("g-grunderna", SchoolEnrollment(
        enrollment_id="e2", child_first_name="Dawit",
        child_last_name="Bekele", birth_year=2012,
    ))
    return sunday_school


def test_groups_page_redirects_unauthenticated(client):
    r = client.get("/sunday-school")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_login_form_accepts_teacher_role(client):
    r = client.post(
        "/login", data={"user_id": "t1", "church_id": "c1", "role": "teacher"}
    )
    assert r.status_code == 303
    assert "kyrk_session" in r.headers.get("set-cookie", "")


def test_teacher_sees_only_own_groups(teacher_client, seeded_school):
    r = teacher_client.get("/sunday-school")
    assert r.status_code == 200
    assert "Grunderna" in r.text
    assert "Krar" not in r.text


def test_admin_sees_all_groups(authed_client, seeded_school):
    r = authed_client.get("/sunday-school")
    assert r.status_code == 200
    assert "Grunderna" in r.text
    assert "Krar" in r.text


def test_attendance_form_shows_roster(teacher_client, seeded_school):
    r = teacher_client.get("/sunday-school/g-grunderna")
    assert r.status_code == 200
    assert "Maria" in r.text
    assert "Dawit" in r.text
    assert 'name="present"' in r.text
    assert 'name="attendance_date"' in r.text


def test_record_attendance_saves_and_reports_aggregate(
    teacher_client, seeded_school, activity
):
    r = teacher_client.post(
        "/sunday-school/g-grunderna/attendance",
        data={"attendance_date": "2026-06-14", "present": ["e1", "e2"]},
    )
    assert r.status_code == 303
    assert "/sunday-school/g-grunderna" in r.headers["location"]

    saved = seeded_school.recorded
    assert len(saved) == 1
    assert saved[0]["group_id"] == "g-grunderna"
    assert saved[0]["present_enrollment_ids"] == ["e1", "e2"]

    # The aggregate reaches reporting-service as a YELLOW-zone activity.
    assert len(activity.logged) == 1
    logged = activity.logged[0]
    assert logged["activity_type"] == "sunday_school"
    assert logged["date"] == "2026-06-14"
    assert logged["participants_total"] == 2
    assert logged["age_band_counts"]["7-12"] == 1
    assert logged["age_band_counts"]["13-17"] == 1


def test_reported_aggregate_contains_no_child_names(
    teacher_client, seeded_school, activity
):
    """Zone boundary: nothing that crosses to reporting-service may carry PII."""
    teacher_client.post(
        "/sunday-school/g-grunderna/attendance",
        data={"attendance_date": "2026-06-14", "present": ["e1"]},
    )
    payload_text = str(activity.logged)
    for forbidden in ("Maria", "Dawit", "Tesfaye", "Bekele", "e1"):
        assert forbidden not in payload_text


def test_attendance_failure_flashes_error_and_logs_nothing(
    teacher_client, seeded_school, activity
):
    seeded_school.record_error = ClientError("forbidden", status_code=403)
    r = teacher_client.post(
        "/sunday-school/g-grunderna/attendance",
        data={"attendance_date": "2026-06-14", "present": ["e1"]},
    )
    assert r.status_code == 303
    assert "level=error" in r.headers["location"]
    assert activity.logged == []


def test_attendance_saved_even_if_reporting_fails(
    teacher_client, seeded_school, activity
):
    activity.log_error = ClientError("reporting down", status_code=500)
    r = teacher_client.post(
        "/sunday-school/g-grunderna/attendance",
        data={"attendance_date": "2026-06-14", "present": ["e1"]},
    )
    assert r.status_code == 303
    assert len(seeded_school.recorded) == 1


def test_attendance_history_shown_on_group_page(teacher_client, seeded_school):
    seeded_school.seed_attendance("g-grunderna", AttendanceRecord(
        date="2026-06-07", present_enrollment_ids=("e1",),
        participants_total=1,
        age_band_counts={"0-6": 0, "7-12": 1, "13-17": 0, "18-25": 0, "26+": 0},
    ))
    r = teacher_client.get("/sunday-school/g-grunderna")
    assert "2026-06-07" in r.text


# ----------------------------------------------------------------- bilingual


def test_pages_are_bilingual_swedish_amharic(teacher_client, seeded_school):
    r = teacher_client.get("/sunday-school")
    assert "Söndagsskola" in r.text
    assert "ሰንበት" in r.text  # Sunday school in Amharic

    r = teacher_client.get("/sunday-school/g-grunderna")
    assert "Närvaro" in r.text
    assert "መገኘት" in r.text  # attendance/presence in Amharic


# -------------------------------------------------------------- quick enroll


def test_teacher_quick_enrolls_new_child(teacher_client, seeded_school):
    """A child not on the list is registered on the spot from the group page."""
    r = teacher_client.post(
        "/sunday-school/g-grunderna/enroll",
        data={
            "child_first_name": "Ruth",
            "child_last_name": "Alemu",
            "birth_year": "2019",
            "guardian_name": "Hanna Alemu",
            "guardian_phone": "+46700000002",
            "guardian_consent": "true",
        },
    )
    assert r.status_code == 303
    assert "/sunday-school/g-grunderna" in r.headers["location"]
    assert len(seeded_school.enrolled) == 1
    assert seeded_school.enrolled[0]["child_first_name"] == "Ruth"


def test_quick_enroll_requires_guardian_consent(teacher_client, seeded_school):
    r = teacher_client.post(
        "/sunday-school/g-grunderna/enroll",
        data={
            "child_first_name": "Ruth",
            "child_last_name": "Alemu",
            "birth_year": "2019",
        },
    )
    assert r.status_code == 303
    assert "level=error" in r.headers["location"]
    assert seeded_school.enrolled == []


def test_quick_enroll_form_present_on_group_page(teacher_client, seeded_school):
    r = teacher_client.get("/sunday-school/g-grunderna")
    assert 'name="child_first_name"' in r.text
    assert 'name="guardian_consent"' in r.text


# ------------------------------------------------------------------- statistik


def _seed_two_months(school):
    school.seed_attendance("g-grunderna", AttendanceRecord(
        date="2026-05-03", present_enrollment_ids=("e1",),
        participants_total=1,
        age_band_counts={"0-6": 0, "7-12": 1, "13-17": 0, "18-25": 0, "26+": 0},
    ))
    school.seed_attendance("g-grunderna", AttendanceRecord(
        date="2026-05-10", present_enrollment_ids=("e1", "e2"),
        participants_total=2,
        age_band_counts={"0-6": 0, "7-12": 1, "13-17": 1, "18-25": 0, "26+": 0},
    ))
    school.seed_attendance("g-grunderna", AttendanceRecord(
        date="2026-06-07", present_enrollment_ids=("e1", "e2"),
        participants_total=2,
        age_band_counts={"0-6": 0, "7-12": 1, "13-17": 1, "18-25": 0, "26+": 0},
    ))


def test_monthly_stats_with_participation_score(teacher_client, seeded_school):
    _seed_two_months(seeded_school)
    r = teacher_client.get("/sunday-school/g-grunderna")
    # Both months appear with unique-children counts.
    assert "2026-05" in r.text
    assert "2026-06" in r.text
    # 2026-06: 2 of 2 children in 1 session → 100% → Bra; May → 75% → Bra.
    assert "Bra" in r.text


def test_low_participation_is_flagged(teacher_client, seeded_school):
    seeded_school.seed_attendance("g-grunderna", AttendanceRecord(
        date="2026-06-07", present_enrollment_ids=("e1",),
        participants_total=1,
        age_band_counts={"0-6": 0, "7-12": 1, "13-17": 0, "18-25": 0, "26+": 0},
    ))
    seeded_school.seed_attendance("g-grunderna", AttendanceRecord(
        date="2026-06-14", present_enrollment_ids=(),
        participants_total=0,
        age_band_counts={"0-6": 0, "7-12": 0, "13-17": 0, "18-25": 0, "26+": 0},
    ))
    r = teacher_client.get("/sunday-school/g-grunderna")
    # 1 of 4 possible attendances in June → 25% → Lågt.
    assert "Lågt" in r.text


def test_per_child_attendance_tracking(teacher_client, seeded_school):
    """Per-child attendance over time — the basis for tracking each
    child's progression and for level certificates."""
    _seed_two_months(seeded_school)
    r = teacher_client.get("/sunday-school/g-grunderna")
    # Maria (e1) attended 3 of 3 sessions, Dawit (e2) 2 of 3.
    assert "3/3" in r.text
    assert "2/3" in r.text


# ------------------------------------------------------------- create groups


def test_staff_sees_create_group_form(authed_client, seeded_school):
    r = authed_client.get("/sunday-school")
    assert 'name="group_name"' in r.text


def test_teacher_does_not_see_create_group_form(teacher_client, seeded_school):
    r = teacher_client.get("/sunday-school")
    assert 'name="group_name"' not in r.text


def test_staff_creates_group(authed_client, sunday_school):
    r = authed_client.post(
        "/sunday-school/groups",
        data={
            "group_name": "Begena",
            "description": "Begenalektioner",
            "teacher_user_ids": "t1, t2",
        },
    )
    assert r.status_code == 303
    created = sunday_school.created_groups
    assert len(created) == 1
    assert created[0]["name"] == "Begena"
    assert created[0]["teacher_user_ids"] == ["t1", "t2"]


def test_teacher_cannot_create_group(teacher_client, sunday_school):
    r = teacher_client.post(
        "/sunday-school/groups",
        data={"group_name": "Begena", "description": "", "teacher_user_ids": ""},
    )
    assert r.status_code == 303
    assert "level=error" in r.headers["location"]
    assert sunday_school.created_groups == []
