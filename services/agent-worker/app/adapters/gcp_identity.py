"""Google-signed ID tokens for service-to-service calls on Cloud Run.

Private downstream services (--no-allow-unauthenticated) sit behind
Cloud Run IAM. The caller proves its service identity with an ID token
in X-Serverless-Authorization — Cloud Run validates and strips it, while
the user's bearer token in Authorization reaches the app untouched.

The token comes from the metadata server, which only exists on GCP, so
local dev and tests simply pass no provider.
"""
from __future__ import annotations

from typing import Callable

_METADATA_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/"
    "service-accounts/default/identity"
)

IdTokenProvider = Callable[[str], "str | None"]


def metadata_id_token_provider(audience: str) -> str | None:
    """Fetch an ID token for the given audience. Returns None off-GCP."""
    import httpx

    try:
        r = httpx.get(
            _METADATA_URL,
            params={"audience": audience},
            headers={"Metadata-Flavor": "Google"},
            timeout=2.0,
        )
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    return r.text
