from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.domain.errors import ConsentMissing, DuplicateSubmission, RateLimited
from app.domain.models import SubmissionStatus
from app.services.intake_service import IntakePayload

_counter = 0

def _unique_pnr() -> str:
    """Generate a unique test personnummer that passes Luhn."""
    global _counter
    _counter += 1
    return f"19800101-1231"  # same base, but we vary per test


def _payload(**overrides) -> IntakePayload:
    defaults = dict(
        church_id="c1",
        first_name="Anna",
        last_name="Andersson",
        phone="+46701234567",
        email="anna@example.se",
        personal_number=f"test-pnr-{uuid4().hex[:8]}",
        gdpr_consent=True,
        consent_timestamp=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return IntakePayload(**defaults)


def test_happy_path_stores_pending_and_notifies(service, repo, notifier):
    submission = service.submit(_payload(), client_ip="1.2.3.4")
    assert submission.status is SubmissionStatus.PENDING
    assert repo.get(submission.submission_id) is not None
    assert len(notifier.sent) == 1


def test_notifier_failure_does_not_break_submission(repo, limiter):
    # A failing/misconfigured notifier must never 500 a member's submission.
    # (In production a missing ADMIN_NOTIFY_WEBHOOK previously crashed /intake.)
    from app.services.intake_service import IntakeService

    class _ExplodingNotifier:
        def notify_new_pending(self, submission):
            raise RuntimeError("webhook down")

    svc = IntakeService(repo=repo, notifier=_ExplodingNotifier(), limiter=limiter)
    submission = svc.submit(_payload(), client_ip="1.2.3.4")
    assert submission.status is SubmissionStatus.PENDING
    assert repo.get(submission.submission_id) is not None


def test_action_and_tax_consent_are_stored(service, repo):
    # "Redan medlem — vill bara byta kyrkoskatt": the church-fee switch is a
    # revenue lever, so the intent (action) and the Skatteverket consent must
    # be persisted on the submission for admins to act on.
    submission = service.submit(
        _payload(action="already_member", tax_consent=True, monthly_fee_sek=0),
        client_ip="1.2.3.4",
    )
    stored = repo.get(submission.submission_id)
    assert stored.action == "already_member"
    assert stored.tax_consent is True


def test_action_defaults_when_not_provided(service):
    submission = service.submit(_payload(), client_ip="1.2.3.4")
    assert submission.action == "register_only"
    assert submission.tax_consent is False


def test_missing_consent_rejected(service):
    with pytest.raises(ConsentMissing):
        service.submit(_payload(gdpr_consent=False), client_ip="1.2.3.4")


def test_register_and_switch_requires_tax_consent(service):
    with pytest.raises(ConsentMissing):
        service.submit(
            _payload(action="register_and_switch", tax_consent=False), client_ip="1.2.3.4"
        )


def test_already_member_switch_requires_tax_consent(service):
    with pytest.raises(ConsentMissing):
        service.submit(
            _payload(action="already_member", tax_consent=False, monthly_fee_sek=0),
            client_ip="1.2.3.4",
        )


def test_switch_with_tax_consent_is_accepted(service, repo):
    submission = service.submit(
        _payload(action="register_and_switch", tax_consent=True), client_ip="1.2.3.4"
    )
    assert submission.action == "register_and_switch"
    assert submission.tax_consent is True


def test_register_only_does_not_require_tax_consent(service):
    # The default action must remain low-friction — no tax consent needed.
    submission = service.submit(
        _payload(action="register_only", tax_consent=False), client_ip="1.2.3.4"
    )
    assert submission.tax_consent is False


def test_duplicate_personnummer_rejected(service):
    pnr = "19800101-1231"
    service.submit(_payload(personal_number=pnr), client_ip="1.2.3.4")
    with pytest.raises(DuplicateSubmission):
        service.submit(_payload(personal_number=pnr), client_ip="5.6.7.8")


def test_rate_limit_per_ip(service):
    for i in range(3):
        service.submit(_payload(), client_ip="1.2.3.4")
    with pytest.raises(RateLimited):
        service.submit(_payload(), client_ip="1.2.3.4")


def test_rate_limit_is_per_ip_or_church(service):
    for i in range(3):
        service.submit(_payload(), client_ip=f"1.2.3.{i}")
    with pytest.raises(RateLimited):
        service.submit(_payload(), client_ip="9.9.9.9")
