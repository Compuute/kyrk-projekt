from datetime import datetime, timezone

import pytest

from app.adapters.fake_membership_client import FakeMembershipClient
from app.domain.errors import (
    DownstreamFailure,
    NotAuthorized,
    SubmissionAlreadyProcessed,
    SubmissionNotFound,
)
from app.domain.models import Actor, Role, SubmissionStatus
from app.services.intake_service import IntakePayload, IntakeService


def _actor(role: Role, church_id: str = "c1", user_id: str = "u-admin") -> Actor:
    return Actor(user_id=user_id, church_id=church_id, role=role)


def _payload(**overrides) -> IntakePayload:
    defaults = dict(
        church_id="c1",
        first_name="Anna",
        last_name="Andersson",
        phone="+4670000000",
        email="anna@example.se",
        personal_number="19800101-1231",
        gdpr_consent=True,
        consent_timestamp=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return IntakePayload(**defaults)


def _submit(service: IntakeService, **overrides):
    return service.submit(_payload(**overrides), client_ip="1.2.3.4")


# --------------------------------------------------------------------- list


def test_list_pending_requires_admin_role(service):
    _submit(service)
    with pytest.raises(NotAuthorized):
        service.list_pending(_actor(Role.VIEWER))


def test_list_pending_scoped_by_church(service):
    _submit(service, church_id="c1")
    _submit(service, church_id="c2")
    items = service.list_pending(_actor(Role.ADMIN, "c1"))
    assert len(items) == 1
    assert items[0].church_id == "c1"


def test_list_pending_excludes_already_processed(service, membership_client):
    submitted = _submit(service)
    service.approve(
        actor=_actor(Role.ADMIN),
        actor_token="u-admin:c1:admin",
        submission_id=submitted.submission_id,
    )
    items = service.list_pending(_actor(Role.ADMIN))
    assert items == []


# ------------------------------------------------------------------ approve


def test_approve_calls_membership_service_and_redacts(service, membership_client, repo):
    submitted = _submit(service)

    result = service.approve(
        actor=_actor(Role.ADMIN, user_id="u-1"),
        actor_token="u-1:c1:admin",
        submission_id=submitted.submission_id,
    )

    # Downstream call was made with the correct payload
    assert len(membership_client.calls) == 1
    forwarded_token, forwarded_req = membership_client.calls[0]
    assert forwarded_token == "u-1:c1:admin"
    assert forwarded_req.first_name == "Anna"
    assert forwarded_req.personal_number == "19800101-1231"

    # Approval result points to the new member
    assert result.status == SubmissionStatus.APPROVED.value
    assert result.created_member_id

    # Stored submission is redacted — no PII left behind
    stored = repo.get(submitted.submission_id)
    assert stored is not None
    assert stored.status is SubmissionStatus.APPROVED
    assert stored.processed_by_user_id == "u-1"
    assert stored.created_member_id == result.created_member_id
    assert "1980" not in stored.personal_number
    assert stored.phone == "***redacted***"
    assert stored.email == "***redacted***"
    # First/last name are kept — they're needed for the audit trail and
    # are low-sensitivity compared to personnummer/phone/email.
    assert stored.first_name == "Anna"


def test_approve_viewer_forbidden(service):
    submitted = _submit(service)
    with pytest.raises(NotAuthorized):
        service.approve(
            actor=_actor(Role.VIEWER),
            actor_token="u:c1:viewer",
            submission_id=submitted.submission_id,
        )


def test_approve_missing_returns_not_found(service):
    with pytest.raises(SubmissionNotFound):
        service.approve(
            actor=_actor(Role.ADMIN),
            actor_token="u-admin:c1:admin",
            submission_id="does-not-exist",
        )


def test_approve_cross_church_hidden_as_not_found(service):
    submitted = _submit(service, church_id="c1")
    with pytest.raises(SubmissionNotFound):
        service.approve(
            actor=_actor(Role.ADMIN, church_id="c2"),
            actor_token="u:c2:admin",
            submission_id=submitted.submission_id,
        )


def test_approve_twice_is_conflict(service):
    submitted = _submit(service)
    service.approve(
        actor=_actor(Role.ADMIN),
        actor_token="u:c1:admin",
        submission_id=submitted.submission_id,
    )
    with pytest.raises(SubmissionAlreadyProcessed):
        service.approve(
            actor=_actor(Role.ADMIN),
            actor_token="u:c1:admin",
            submission_id=submitted.submission_id,
        )


def test_approve_downstream_failure_leaves_submission_pending(repo, notifier, limiter):
    client = FakeMembershipClient(fail_with=RuntimeError("boom"))
    service = IntakeService(
        repo=repo, notifier=notifier, limiter=limiter, membership_client=client
    )
    submitted = _submit(service)

    with pytest.raises(DownstreamFailure):
        service.approve(
            actor=_actor(Role.ADMIN),
            actor_token="u:c1:admin",
            submission_id=submitted.submission_id,
        )

    # On failure we leave the submission pending so an admin can retry.
    stored = repo.get(submitted.submission_id)
    assert stored is not None
    assert stored.status is SubmissionStatus.PENDING
    assert stored.personal_number == "19800101-1231"  # not redacted


# ------------------------------------------------------------------- reject


def test_reject_marks_submission_and_redacts(service, repo):
    submitted = _submit(service)
    result = service.reject(
        actor=_actor(Role.ADMIN, user_id="u-admin"),
        submission_id=submitted.submission_id,
    )
    assert result.status is SubmissionStatus.REJECTED
    stored = repo.get(submitted.submission_id)
    assert stored is not None
    assert stored.status is SubmissionStatus.REJECTED
    assert stored.processed_by_user_id == "u-admin"
    assert "1980" not in stored.personal_number


def test_reject_viewer_forbidden(service):
    submitted = _submit(service)
    with pytest.raises(NotAuthorized):
        service.reject(actor=_actor(Role.VIEWER), submission_id=submitted.submission_id)


def test_reject_already_processed_is_conflict(service):
    submitted = _submit(service)
    service.reject(actor=_actor(Role.ADMIN), submission_id=submitted.submission_id)
    with pytest.raises(SubmissionAlreadyProcessed):
        service.reject(actor=_actor(Role.ADMIN), submission_id=submitted.submission_id)
