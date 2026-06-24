"""Public education-enrollment endpoint (Fredagsskola/söndagsskola).

This is the PUBLIC edge for a guardian's child application. membership-service
holds the enrollment data but is --no-allow-unauthenticated (RED zone), so the
public site posts here and we forward server-to-server. Minimal data only
(GDPR Art. 8): child name + birth year + guardian name + consent. No
personnummer, no phone. Rate-limited per caller IP at this edge.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import get_limiter, get_membership_client
from app.domain.errors import DownstreamFailure, RateLimited
from app.ports.membership_client import MembershipClientPort, PublicEnrollmentRequest
from app.ports.rate_limiter import RateLimiterPort

router = APIRouter(tags=["education"])


class EducationRegistrationRequest(BaseModel):
    church_id: str = Field(min_length=1, max_length=64)
    group_id: str = Field(min_length=1, max_length=64)
    child_first_name: str = Field(min_length=1, max_length=100)
    child_last_name: str = Field(min_length=1, max_length=100)
    birth_year: int = Field(ge=1900, le=2100)
    guardian_name: str = Field(min_length=1, max_length=100)
    guardian_consent: bool = False
    consent_timestamp: str = ""
    # The public form may also send activity_id for its own bookkeeping; it is
    # not needed downstream and is ignored.


@router.post("/education-registration", status_code=status.HTTP_202_ACCEPTED)
def register_education(
    body: EducationRegistrationRequest,
    request: Request,
    limiter: RateLimiterPort = Depends(get_limiter),
    membership_client: MembershipClientPort = Depends(get_membership_client),
) -> dict[str, str]:
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.check(f"edu-enroll-ip:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many requests — try again later",
        )
    if not body.guardian_consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="guardian consent is required to enroll a child",
        )
    payload = PublicEnrollmentRequest(
        church_id=body.church_id,
        group_id=body.group_id,
        child_first_name=body.child_first_name,
        child_last_name=body.child_last_name,
        birth_year=body.birth_year,
        guardian_name=body.guardian_name,
        guardian_consent=body.guardian_consent,
        consent_timestamp=body.consent_timestamp,
    )
    try:
        membership_client.create_public_enrollment(payload, client_ip=client_ip)
    except RateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    except DownstreamFailure as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="kunde inte ta emot anmälan just nu",
        ) from exc
    return {"status": "accepted"}
