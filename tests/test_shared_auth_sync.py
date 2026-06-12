"""Shared auth adapter sync guard — fails CI if service copies drift.

The Zitadel and fake auth adapters are deliberately vendored into each
service (each copy imports the service's own `app.domain` models, and the
services deploy as independent containers). The canonical source lives in
`libs/shared-auth/`; `scripts/sync-shared-auth.py` copies it out. This
guard ensures a fix applied in one place reaches every service — the
intake church-scoping bug existed precisely because the copies drifted.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CANONICAL_DIR = ROOT / "libs" / "shared-auth"

SERVICES = [
    "membership-intake",
    "membership-service",
    "certificate-service",
    "reporting-service",
]

SHARED_FILES = ["zitadel_auth.py", "fake_auth.py"]


class TestCanonicalSourceExists:
    @pytest.mark.parametrize("filename", SHARED_FILES)
    def test_canonical_file_exists(self, filename):
        assert (CANONICAL_DIR / filename).exists(), (
            f"libs/shared-auth/{filename} missing — it is the canonical "
            "source for the per-service auth adapter copies"
        )


class TestServiceCopiesMatchCanonical:
    @pytest.mark.parametrize("service", SERVICES)
    @pytest.mark.parametrize("filename", SHARED_FILES)
    def test_copy_is_identical(self, service, filename):
        canonical = CANONICAL_DIR / filename
        copy = ROOT / "services" / service / "app" / "adapters" / filename
        if not canonical.exists():
            pytest.fail(f"canonical {filename} missing in libs/shared-auth/")
        assert copy.exists(), f"{service} is missing adapters/{filename}"
        assert copy.read_text(encoding="utf-8") == canonical.read_text(
            encoding="utf-8"
        ), (
            f"services/{service}/app/adapters/{filename} has drifted from "
            f"libs/shared-auth/{filename}. Edit the canonical file and run "
            "`python scripts/sync-shared-auth.py` — never patch a single copy."
        )


class TestSyncScriptExists:
    def test_sync_script_exists(self):
        assert (ROOT / "scripts" / "sync-shared-auth.py").exists()
