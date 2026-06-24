"""Firestore-backed Sunday school tracker."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import (
    SundaySchoolAttendance,
    SundaySchoolEnrollment,
    SundaySchoolGroup,
)

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_GROUPS = "sunday_school_groups"
_ENROLLMENTS = "sunday_school_enrollments"
_ATTENDANCE = "sunday_school_attendance"


def _parse_created_at(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if value:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _group_to_doc(g: SundaySchoolGroup) -> dict:
    return {
        "group_id": g.group_id,
        "church_id": g.church_id,
        "name": g.name,
        "description": g.description,
        "teacher_user_ids": g.teacher_user_ids,
        "active": g.active,
        "funding_tag": g.funding_tag,
        "created_at": g.created_at.isoformat(),
    }


def _doc_to_group(data: dict) -> SundaySchoolGroup:
    return SundaySchoolGroup(
        church_id=data["church_id"],
        name=data["name"],
        description=data.get("description", ""),
        teacher_user_ids=data.get("teacher_user_ids", []),
        active=data.get("active", True),
        funding_tag=data.get("funding_tag", "sondagsskola"),
        group_id=data["group_id"],
        created_at=_parse_created_at(data.get("created_at")),
    )


def _enrollment_to_doc(e: SundaySchoolEnrollment) -> dict:
    return {
        "enrollment_id": e.enrollment_id,
        "church_id": e.church_id,
        "group_id": e.group_id,
        "child_first_name": e.child_first_name,
        "child_last_name": e.child_last_name,
        "birth_year": e.birth_year,
        "guardian_name": e.guardian_name,
        "guardian_phone": e.guardian_phone,
        "guardian_consent": e.guardian_consent,
        "member_id": e.member_id,
        "active": e.active,
        "pending": e.pending,
        "consent_timestamp": e.consent_timestamp,
        "created_at": e.created_at.isoformat(),
    }


def _doc_to_enrollment(data: dict) -> SundaySchoolEnrollment:
    return SundaySchoolEnrollment(
        church_id=data["church_id"],
        group_id=data["group_id"],
        child_first_name=data.get("child_first_name", ""),
        child_last_name=data.get("child_last_name", ""),
        birth_year=data.get("birth_year", 0),
        guardian_name=data.get("guardian_name", ""),
        guardian_phone=data.get("guardian_phone", ""),
        guardian_consent=data.get("guardian_consent", False),
        member_id=data.get("member_id", ""),
        active=data.get("active", True),
        pending=data.get("pending", False),
        consent_timestamp=data.get("consent_timestamp", ""),
        enrollment_id=data["enrollment_id"],
        created_at=_parse_created_at(data.get("created_at")),
    )


def _attendance_to_doc(a: SundaySchoolAttendance) -> dict:
    return {
        "attendance_id": a.attendance_id,
        "church_id": a.church_id,
        "group_id": a.group_id,
        "date": a.date,
        "present_enrollment_ids": a.present_enrollment_ids,
        "registered_by_user_id": a.registered_by_user_id,
        "created_at": a.created_at.isoformat(),
    }


def _doc_to_attendance(data: dict) -> SundaySchoolAttendance:
    return SundaySchoolAttendance(
        church_id=data["church_id"],
        group_id=data["group_id"],
        date=data["date"],
        present_enrollment_ids=data.get("present_enrollment_ids", []),
        registered_by_user_id=data.get("registered_by_user_id", ""),
        attendance_id=data["attendance_id"],
        created_at=_parse_created_at(data.get("created_at")),
    )


class FirestoreSundaySchoolTracker:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self, name: str):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(name)

    def list_groups(self, church_id: str) -> list[SundaySchoolGroup]:
        query = self._coll(_GROUPS).where("church_id", "==", church_id)
        return [_doc_to_group(doc.to_dict()) for doc in query.stream()]

    def get_group(self, church_id: str, group_id: str) -> SundaySchoolGroup | None:
        snap = self._coll(_GROUPS).document(f"{church_id}__{group_id}").get()
        if not snap.exists:
            return None
        return _doc_to_group(snap.to_dict())

    def save_group(self, group: SundaySchoolGroup) -> None:
        self._coll(_GROUPS).document(f"{group.church_id}__{group.group_id}").set(
            _group_to_doc(group)
        )

    def list_enrollments(self, church_id: str, group_id: str) -> list[SundaySchoolEnrollment]:
        query = (
            self._coll(_ENROLLMENTS)
            .where("church_id", "==", church_id)
            .where("group_id", "==", group_id)
        )
        return [_doc_to_enrollment(doc.to_dict()) for doc in query.stream()]

    def list_pending_enrollments(self, church_id: str) -> list[SundaySchoolEnrollment]:
        query = (
            self._coll(_ENROLLMENTS)
            .where("church_id", "==", church_id)
            .where("pending", "==", True)
        )
        return [_doc_to_enrollment(doc.to_dict()) for doc in query.stream()]

    def get_enrollment(
        self, church_id: str, enrollment_id: str
    ) -> SundaySchoolEnrollment | None:
        snap = self._coll(_ENROLLMENTS).document(f"{church_id}__{enrollment_id}").get()
        if not snap.exists:
            return None
        return _doc_to_enrollment(snap.to_dict())

    def save_enrollment(self, enrollment: SundaySchoolEnrollment) -> None:
        doc_id = f"{enrollment.church_id}__{enrollment.enrollment_id}"
        self._coll(_ENROLLMENTS).document(doc_id).set(_enrollment_to_doc(enrollment))

    def list_attendance(self, church_id: str, group_id: str) -> list[SundaySchoolAttendance]:
        query = (
            self._coll(_ATTENDANCE)
            .where("church_id", "==", church_id)
            .where("group_id", "==", group_id)
        )
        return [_doc_to_attendance(doc.to_dict()) for doc in query.stream()]

    def get_attendance(
        self, church_id: str, group_id: str, date: str
    ) -> SundaySchoolAttendance | None:
        snap = self._coll(_ATTENDANCE).document(f"{church_id}__{group_id}__{date}").get()
        if not snap.exists:
            return None
        return _doc_to_attendance(snap.to_dict())

    def save_attendance(self, record: SundaySchoolAttendance) -> None:
        doc_id = f"{record.church_id}__{record.group_id}__{record.date}"
        self._coll(_ATTENDANCE).document(doc_id).set(_attendance_to_doc(record))
