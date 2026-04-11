from __future__ import annotations

from fastapi import Depends

from app.adapters.in_memory_notifier import InMemoryNotifier
from app.adapters.in_memory_rate_limiter import InMemoryRateLimiter
from app.adapters.in_memory_submission_repository import InMemorySubmissionRepository
from app.ports.notifier import NotifierPort
from app.ports.rate_limiter import RateLimiterPort
from app.ports.submission_repository import SubmissionRepository
from app.services.intake_service import IntakeService


_REPO: SubmissionRepository = InMemorySubmissionRepository()
_NOTIFIER: NotifierPort = InMemoryNotifier()
_LIMITER: RateLimiterPort = InMemoryRateLimiter(max_hits=5, window_seconds=60)


def get_repo() -> SubmissionRepository:
    return _REPO


def get_notifier() -> NotifierPort:
    return _NOTIFIER


def get_limiter() -> RateLimiterPort:
    return _LIMITER


def get_service(
    repo: SubmissionRepository = Depends(get_repo),
    notifier: NotifierPort = Depends(get_notifier),
    limiter: RateLimiterPort = Depends(get_limiter),
) -> IntakeService:
    return IntakeService(repo=repo, notifier=notifier, limiter=limiter)
