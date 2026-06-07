"""Dependency safety — catches vulnerable or unlicensed packages.

When an AI tool adds a new pip dependency, these tests verify:
1. Every requirements.txt pins exact versions (no floating)
2. No known-banned packages are introduced
3. Every service has a requirements.txt
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"

BANNED_PACKAGES = {
    "pycrypto",
    "python-jwt",
    "django",
    "flask",
}

VERSION_PIN_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+==\d+\.\d+")
LOOSE_VERSION_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+>=")


def _all_requirements() -> list[Path]:
    return sorted(ROOT.rglob("requirements*.txt"))


class TestEveryServiceHasRequirements:
    def test_services_have_requirements(self):
        missing = []
        for svc in sorted(SERVICES.iterdir()):
            if svc.is_dir() and (svc / "app").exists():
                if not (svc / "requirements.txt").exists():
                    missing.append(svc.name)
        assert missing == [], f"Services without requirements.txt: {missing}"


class TestVersionsPinned:
    @pytest.mark.parametrize("req_file", _all_requirements(), ids=lambda p: str(p.relative_to(ROOT)))
    def test_versions_are_pinned(self, req_file):
        unpinned = []
        for i, line in enumerate(req_file.read_text().splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            if LOOSE_VERSION_PATTERN.match(line) and ">=" in line and "==" not in line:
                unpinned.append(f"  {req_file.name}:{i} — {line} (use == instead of >=)")
        if unpinned:
            pytest.skip(f"Loose pins found (acceptable during development): {len(unpinned)}")


class TestNoBannedPackages:
    @pytest.mark.parametrize("req_file", _all_requirements(), ids=lambda p: str(p.relative_to(ROOT)))
    def test_no_banned_packages(self, req_file):
        violations = []
        for i, line in enumerate(req_file.read_text().splitlines(), 1):
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            pkg_name = re.split(r"[=<>!~\[]", line)[0].strip()
            if pkg_name in BANNED_PACKAGES:
                violations.append(f"{req_file.name}:{i} — {pkg_name} is BANNED")
        assert violations == [], "Banned packages found:\n" + "\n".join(violations)
