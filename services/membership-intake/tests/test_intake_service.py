from datetime import datetime, timezone

import pytest

from app.domain.errors import ConsentMissing, RateLimited
from app.domain.models import SubmissionStatus
from app.services.intake_service import IntakePayload


def _payload(**overrides) -> IntakePayload:
    defaults = dict(
        church_id="c1",
        first_name="Anna",
        last_name="Andersson",
        phone="+4670000000",
        email="anna@example.se",
        personal_number="19800101-1234",
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


def test_missing_consent_rejected(service):
    with pytest.raises(ConsentMissing):
        service.submit(_payload(gdpr_consent=False), client_ip="1.2.3.4")


def test_rate_limit_per_ip(service):
    for _ in range(3):
        service.submit(_payload(), client_ip="1.2.3.4")
    with pytest.raises(RateLimited):
        service.submit(_payload(), client_ip="1.2.3.4")


def test_rate_limit_is_per_ip_or_church(service):
    # Different IPs, same church — limited once church bucket fills.
    for i in range(3):
        service.submit(_payload(), client_ip=f"1.2.3.{i}")
    with pytest.raises(RateLimited):
        service.submit(_payload(), client_ip="9.9.9.9")
