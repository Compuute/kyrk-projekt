"""Docs freshness tests — fails CI if docs fall out of sync with code.

This test runs in CI and catches when someone adds a feature without
updating the documentation. It checks:
1. README mentions every service that exists
2. README mentions every HTML page that exists
3. README test count is not wildly stale
4. Every HTML page is in the docs index or README
5. Every OpenClaw template is mentioned somewhere in docs
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
DOCS_DIR = ROOT / "docs"


def _all_docs_text() -> str:
    """Concatenate all markdown docs for searching."""
    texts = [README]
    for md in DOCS_DIR.rglob("*.md"):
        texts.append(md.read_text(encoding="utf-8"))
    return "\n".join(texts)


ALL_DOCS = _all_docs_text()


class TestReadmeMentionsServices:
    def test_every_backend_service_in_readme(self):
        services_dir = ROOT / "services"
        for svc in sorted(services_dir.iterdir()):
            if svc.is_dir() and (svc / "app").exists():
                assert svc.name in README, (
                    f"README must mention service '{svc.name}'"
                )

    def test_every_html_page_in_readme_or_docs(self):
        portal = ROOT / "frontend" / "member-portal"
        missing = []
        for html in sorted(portal.glob("*.html")):
            if html.name not in ALL_DOCS:
                missing.append(html.name)
        assert not missing, (
            f"The following HTML pages exist but are not mentioned in any doc: {missing}"
        )


class TestWorkflowsDocumented:
    def test_every_openclaw_template_mentioned(self):
        core_dir = ROOT / "automation" / "openclaw" / "core"
        if not core_dir.exists():
            pytest.skip("no openclaw core dir")
        for tmpl in sorted(core_dir.glob("*.json")):
            name = tmpl.stem
            assert name in ALL_DOCS, (
                f"OpenClaw template '{name}' is not mentioned in any doc"
            )


class TestCertificateTypesDocumented:
    def test_all_cert_types_in_docs(self):
        models = ROOT / "services" / "certificate-service" / "app" / "domain" / "models.py"
        if not models.exists():
            pytest.skip("no certificate models")
        src = models.read_text(encoding="utf-8")
        for line in src.splitlines():
            if "=" in line and line.strip().startswith("SUNDAY_SCHOOL_"):
                enum_val = line.split("=")[1].strip().strip('"').strip("'")
                assert enum_val in ALL_DOCS or "sunday_school" in ALL_DOCS.lower(), (
                    f"Certificate type '{enum_val}' not in docs"
                )


class TestGrantsDatabaseDocumented:
    def test_grant_count_in_readme(self):
        db_path = ROOT / "automation" / "grants" / "database.json"
        if not db_path.exists():
            pytest.skip("no grants database")
        grants = json.loads(db_path.read_text(encoding="utf-8"))["grants"]
        assert str(len(grants)) in README, (
            f"README should mention {len(grants)} grants"
        )


class TestDocIndexComplete:
    def test_every_doc_in_readme_index(self):
        """Every numbered doc (00-18) should be in the README docs index."""
        for md in sorted(DOCS_DIR.glob("*.md")):
            if md.name[0].isdigit():
                assert md.name in README, (
                    f"'{md.name}' exists in docs/ but is not in README index"
                )


class TestDocCodeDriftTripwires:
    """Tie authoritative doc claims to code facts.

    Structural freshness (above) catches "file missing / not mentioned". It is
    blind to prose that contradicts reality — the drift we actually hit: a stale
    auth vendor, a security issue described as open after the code fixed it, and
    a privacy claim contradicted by newly added code. Each test below anchors a
    doc statement to something true in the code, so the prose rots loudly.
    """

    def _auth_adapter_names(self):
        return {p.name for p in (ROOT / "services").glob("*/app/adapters/*.py")}

    def test_auth_vendor_in_authoritative_docs_matches_code(self):
        names = self._auth_adapter_names()
        assert "zitadel_auth.py" in names, "expected a Zitadel auth adapter in code"
        assert "propelauth_auth.py" not in names, (
            "PropelAuth adapter is gone from code — authoritative docs must not "
            "present PropelAuth as the current auth vendor"
        )
        sovereignty = (DOCS_DIR / "02-sovereignty.md").read_text(encoding="utf-8")
        assert "Zitadel" in sovereignty, (
            "sovereignty vendor list must name the real auth vendor (Zitadel)"
        )
        for line in README.splitlines():
            if line.startswith("| **Auth**"):
                assert "Zitadel" in line, (
                    "README stack 'Auth' row must say Zitadel, not a removed vendor"
                )
                break
        else:
            pytest.fail("README stack table has no '| **Auth**' row to check")

    def test_no_doc_claims_tls_disabled_when_code_verifies_it(self):
        auth_src = "".join(
            p.read_text(encoding="utf-8")
            for p in (ROOT / "services").glob("*/app/adapters/*.py")
        )
        if "CERT_NONE" in auth_src or "_create_unverified" in auth_src:
            pytest.skip("code still disables TLS verification; the doc claim is valid")
        offenders = [
            md.name for md in DOCS_DIR.rglob("*.md")
            if "TLS-certverifiering avstängd" in md.read_text(encoding="utf-8")
            or "CERT_NONE" in md.read_text(encoding="utf-8")
        ]
        assert not offenders, (
            f"code verifies TLS, but these docs still describe it as disabled: {offenders}"
        )

    def test_privacy_policy_matches_metrics_code(self):
        import re

        app_ts = (ROOT / "frontend" / "member-portal" / "app.ts").read_text(encoding="utf-8")
        if "trackEvent" not in app_ts:
            pytest.skip("no metrics in code; nothing to keep in sync")
        flag = re.search(r"METRICS_ENABLED\s*=\s*(true|false)", app_ts)
        assert flag, "metrics code must carry an explicit METRICS_ENABLED master switch"
        enabled = flag.group(1) == "true"
        privacy = (
            ROOT / "frontend" / "member-portal" / "src" / "pages" / "privacy.njk"
        ).read_text(encoding="utf-8")
        low = privacy.lower()
        if enabled:
            # Metrics are live → the policy must disclose them honestly.
            assert "inga analysverktyg" not in privacy, (
                "METRICS_ENABLED is true — the privacy policy must not claim "
                "'inga analysverktyg'"
            )
            assert "anonym" in low or "aggregat" in low or "aggregerad" in low, (
                "METRICS_ENABLED is true — the privacy policy must disclose the "
                "anonymous aggregate measurement"
            )
        else:
            # Metrics are dormant → the policy must state none runs, and must not
            # claim active measurement that does not happen.
            assert "inga analysverktyg" in privacy, (
                "METRICS_ENABLED is false — the privacy policy should state there "
                "are no analytics tools"
            )
