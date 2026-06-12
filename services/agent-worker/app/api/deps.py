from __future__ import annotations

from functools import lru_cache

from app.adapters.factory import make_audit_log, make_reporting_client
from app.services.job_service import JobService


@lru_cache(maxsize=1)
def get_job_service() -> JobService:
    return JobService(reporting=make_reporting_client(), audit=make_audit_log())
