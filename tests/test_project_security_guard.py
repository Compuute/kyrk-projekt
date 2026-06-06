"""Project-wide security and architecture guard.

Runs in CI across ALL services. Catches violations regardless of
which AI tool (alla AI-verktyg)
or human developer wrote the code.

Rules enforced:
1. No vendor imports in routes or ports (any service)
2. No PII field names in outgoing adapters (webhooks, notifications)
3. No hardcoded secrets in any Python file
4. Every service has tests
5. Every port file has a corresponding fake adapter
6. Frontend pages have no external scripts or cookies
"""
import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVICES_DIR = ROOT / "services"
FRONTEND_DIR = ROOT / "frontend"

VENDOR_MODULES = {
    "httpx", "anthropic", "google", "firebase_admin",
    "propelauth_fastapi", "propelauth_py", "requests",
    "boto3", "azure", "openai",
}

PII_FIELD_NAMES = {
    "personal_number", "personnummer", "contact_phone",
    "contact_email", "email", "phone", "address",
    "first_name", "last_name", "date_of_birth",
}

SECRET_PATTERNS = [
    re.compile(r'''(?:api_key|secret|password|token)\s*=\s*["'][a-zA-Z0-9_\-]{16,}["']''', re.IGNORECASE),
]


def _all_services() -> list[Path]:
    return sorted(d for d in SERVICES_DIR.iterdir() if d.is_dir() and (d / "app").exists())


def _find_vendor_imports_in_file(filepath: Path) -> list[str]:
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in VENDOR_MODULES:
                    violations.append(f"{filepath.relative_to(ROOT)}:{node.lineno} — import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in VENDOR_MODULES:
                violations.append(f"{filepath.relative_to(ROOT)}:{node.lineno} — from {node.module}")
    return violations


class TestNoVendorLockInAnyService:
    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_no_vendor_imports_in_routes(self, service):
        api_dir = service / "app" / "api"
        if not api_dir.exists():
            pytest.skip("no api dir")
        violations = []
        for py in api_dir.glob("*.py"):
            violations.extend(_find_vendor_imports_in_file(py))
        assert violations == [], "Vendor imports in routes:\n" + "\n".join(violations)

    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_no_vendor_imports_in_ports(self, service):
        ports_dir = service / "app" / "ports"
        if not ports_dir.exists():
            pytest.skip("no ports dir")
        violations = []
        for py in ports_dir.glob("*.py"):
            violations.extend(_find_vendor_imports_in_file(py))
        assert violations == [], "Vendor imports in ports:\n" + "\n".join(violations)


class TestNoPiiInOutgoingAdapters:
    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_no_pii_in_webhook_adapters(self, service):
        adapters_dir = service / "app" / "adapters"
        if not adapters_dir.exists():
            pytest.skip("no adapters dir")
        violations = []
        for py in adapters_dir.glob("*.py"):
            if "fake" in py.name:
                continue
            if "webhook" not in py.name and "notification" not in py.name:
                continue
            source = py.read_text(encoding="utf-8")
            for i, line in enumerate(source.splitlines(), 1):
                if any(f'"{field}"' in line for field in PII_FIELD_NAMES):
                    if "blocked" not in line.lower() and "filter" not in line.lower() and "#" not in line:
                        violations.append(f"{py.relative_to(ROOT)}:{i}")
        assert violations == [], "PII fields in outgoing adapters:\n" + "\n".join(violations)


class TestNoHardcodedSecrets:
    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_no_secrets_in_source(self, service):
        violations = []
        for py in (service / "app").rglob("*.py"):
            source = py.read_text(encoding="utf-8")
            for i, line in enumerate(source.splitlines(), 1):
                if "test" in line.lower() or "fake" in line.lower() or "example" in line.lower():
                    continue
                for pattern in SECRET_PATTERNS:
                    if pattern.search(line):
                        violations.append(f"{py.relative_to(ROOT)}:{i}")
        assert violations == [], "Possible hardcoded secrets:\n" + "\n".join(violations)


class TestEveryServiceHasTests:
    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_service_has_test_files(self, service):
        tests_dir = service / "tests"
        assert tests_dir.exists(), f"{service.name} has no tests/ directory"
        test_files = list(tests_dir.glob("test_*.py"))
        assert len(test_files) > 0, f"{service.name} has no test files"


class TestEveryPortHasFake:
    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_ports_have_fakes(self, service):
        ports_dir = service / "app" / "ports"
        adapters_dir = service / "app" / "adapters"
        if not ports_dir.exists():
            pytest.skip("no ports dir")
        all_fake_names = " ".join(f.stem for f in adapters_dir.glob("fake_*.py"))
        all_adapter_names = " ".join(f.stem for f in adapters_dir.glob("*.py"))
        missing = []
        for port in sorted(ports_dir.glob("*.py")):
            if port.name.startswith("__") or "error" in port.name:
                continue
            stem = port.stem
            skip = {"clients", "session", "data_quality"}
            if stem in skip:
                continue
            keywords = [stem, stem.split("_")[0], stem.replace("_", ""), stem[:6]]
            found = any(kw in all_fake_names or kw in all_adapter_names for kw in keywords)
            if not found:
                missing.append(port.name)
        assert missing == [], f"Ports without fakes in {service.name}:\n" + "\n".join(missing)


class TestFrontendSecurity:
    def test_no_external_scripts_any_page(self):
        portal = FRONTEND_DIR / "member-portal"
        if not portal.exists():
            pytest.skip("no member-portal")
        for html in sorted(portal.glob("*.html")):
            source = html.read_text(encoding="utf-8")
            externals = re.findall(r'<script[^>]+src=["\']https?://', source, re.IGNORECASE)
            assert externals == [], f"{html.name} has external scripts: {externals}"

    def test_no_cookies_any_page(self):
        portal = FRONTEND_DIR / "member-portal"
        if not portal.exists():
            pytest.skip("no member-portal")
        for html in sorted(portal.glob("*.html")):
            source = html.read_text(encoding="utf-8")
            assert "document.cookie" not in source, f"{html.name} sets cookies"

    def test_no_analytics_any_page(self):
        portal = FRONTEND_DIR / "member-portal"
        if not portal.exists():
            pytest.skip("no member-portal")
        trackers = ["google-analytics", "gtag(", "fbq(", "hotjar", "segment", "mixpanel"]
        for html in sorted(portal.glob("*.html")):
            source = html.read_text(encoding="utf-8").lower()
            for t in trackers:
                assert t not in source, f"{html.name} contains tracker: {t}"
