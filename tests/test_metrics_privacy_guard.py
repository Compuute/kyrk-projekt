"""Privacy guard for the aggregate metrics beacon (functions/m.ts).

The member portal promises "no tracking". This guard enforces that the metrics
endpoint stays an anonymous, aggregate-only YELLOW counter and never drifts into
collecting personal data:

  - it exists and validates events against an explicit allowlist (no free-form),
  - it never reads or sets cookies,
  - it never stores an IP address or any PII field,
  - it writes only to the dedicated metrics KV (never the content KV),
  - the frontend beacon honors Do-Not-Track and omits credentials.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = ROOT / "functions" / "m.ts"
APP_TS = ROOT / "frontend" / "member-portal" / "app.ts"


@pytest.fixture(scope="module")
def endpoint_src() -> str:
    assert ENDPOINT.exists(), "functions/m.ts metrics endpoint must exist"
    return ENDPOINT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_src() -> str:
    assert APP_TS.exists(), "frontend/member-portal/app.ts must exist"
    return APP_TS.read_text(encoding="utf-8")


class TestEndpointPrivacy:
    def test_has_closed_event_allowlist(self, endpoint_src: str) -> None:
        assert "ALLOWED_EVENTS" in endpoint_src
        assert "ALLOWED_EVENTS.includes" in endpoint_src, (
            "the endpoint must reject events that are not on the allowlist"
        )

    def test_never_touches_cookies(self, endpoint_src: str) -> None:
        # Ignore prose in // comments; only actual code must be cookie-free.
        code = "\n".join(
            line for line in endpoint_src.splitlines()
            if not line.lstrip().startswith("//")
        ).lower()
        assert "cookie" not in code, (
            "the metrics endpoint must not read or set cookies"
        )

    def test_stores_no_pii(self, endpoint_src: str) -> None:
        low = endpoint_src.lower()
        forbidden = [
            "personnummer", "personal_number", "email", "first_name",
            "last_name", "phone", "cf-connecting-ip", "x-forwarded-for",
        ]
        for token in forbidden:
            assert token not in low, (
                f"the metrics endpoint must not handle PII-like field '{token}'"
            )

    def test_writes_only_to_metrics_kv(self, endpoint_src: str) -> None:
        assert "kyrka_metrics" in endpoint_src
        assert "kyrka_content" not in endpoint_src, (
            "the metrics endpoint must never touch the content KV"
        )


class TestFrontendBeacon:
    def test_honors_do_not_track(self, app_src: str) -> None:
        assert "doNotTrack" in app_src

    def test_beacon_omits_credentials(self, app_src: str) -> None:
        assert "'/m'" in app_src, "app.ts must post to the /m beacon endpoint"
        assert "credentials: 'omit'" in app_src
