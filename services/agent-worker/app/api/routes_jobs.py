"""Pub/Sub push endpoint.

Pub/Sub acks on any 2xx and redelivers on everything else, so:
- terminal outcomes (success, duplicate, unparseable, unknown job) → 204
- transient failures (JobFailed) → 500, Pub/Sub retries with backoff

In production the endpoint sits behind Cloud Run IAM
(--no-allow-unauthenticated); the push subscription authenticates with
an OIDC token. No application-level auth here by design.
"""
from __future__ import annotations

import base64
import binascii
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_job_service
from app.domain.errors import JobFailed
from app.services.job_service import JobService

router = APIRouter(tags=["jobs"])


def _parse_envelope(body: dict) -> tuple[str, dict]:
    message = body["message"]
    message_id = str(message["messageId"])
    raw = base64.b64decode(message["data"], validate=True)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("payload is not an object")
    return message_id, payload


@router.post("/pubsub", status_code=status.HTTP_204_NO_CONTENT)
async def pubsub_push(
    request: Request,
    svc: JobService = Depends(get_job_service),
) -> None:
    try:
        body = await request.json()
        message_id, payload = _parse_envelope(body)
    except (KeyError, ValueError, TypeError, binascii.Error) as exc:
        # Permanently unparseable — ack so Pub/Sub stops redelivering,
        # but leave an audit trace instead of dropping it silently.
        svc.reject("unparseable", detail=f"malformed push envelope: {exc}")
        return

    try:
        svc.handle(message_id, payload)
    except JobFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
