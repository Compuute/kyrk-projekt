"""Architecture & design-principle guard.

Runs in CI across ALL services. Catches violations regardless of which AI tool
or human developer wrote the code — a weaker model that ignores AI-RULES.md is
still blocked here, because these checks read the code, not the author.

Complements test_project_security_guard.py (vendor imports, PII in adapters,
secrets, tests, fakes, frontend). Rules enforced here:

1. Hexagonal layering — app/domain/ must not import app.api or app.adapters
   (the domain is the core; dependencies point inward, never out to I/O).
2. Structured logging — no bare print() in service code
   (well-architected-guidelines.md §6 mandates JSON logging to Cloud Logging).
3. Security-by-design — no eval/exec/os.system/subprocess(shell=True) in service code.
4. Reproducible builds — every service Dockerfile pins its base image (no :latest).
"""
import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVICES_DIR = ROOT / "services"


def _all_services() -> list[Path]:
    return sorted(d for d in SERVICES_DIR.iterdir() if d.is_dir() and (d / "app").exists())


def _app_py_files(service: Path) -> list[Path]:
    """All non-test python files under the service's app/ package."""
    return [p for p in (service / "app").rglob("*.py") if "test" not in p.name]


class TestHexagonalLayering:
    """The domain core must not depend on outer I/O layers (api, adapters)."""

    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_domain_does_not_import_api_or_adapters(self, service):
        domain = service / "app" / "domain"
        if not domain.exists():
            pytest.skip("no domain dir")
        violations = []
        for py in domain.rglob("*.py"):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                mod = None
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    # relative imports: level>0, e.g. `from ..adapters import x`
                    if node.level > 0:
                        mod = mod
                elif isinstance(node, ast.Import):
                    mod = ",".join(a.name for a in node.names)
                if not mod:
                    continue
                parts = {p for m in mod.split(",") for p in m.split(".")}
                if "adapters" in parts or "api" in parts:
                    violations.append(f"{py.relative_to(ROOT)}:{node.lineno} — {mod}")
        assert violations == [], (
            "Domain imports an outer layer (breaks hexagonal dependency direction):\n"
            + "\n".join(violations)
        )


class TestStructuredLogging:
    """No bare print() — services log structured JSON to Cloud Logging (§6)."""

    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_no_print_in_service_code(self, service):
        violations = []
        for py in _app_py_files(service):
            for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if re.match(r"\s*print\(", line):
                    violations.append(f"{py.relative_to(ROOT)}:{i}")
        assert violations == [], (
            "Bare print() in service code — use structured logging:\n" + "\n".join(violations)
        )


class TestNoDangerousCalls:
    """No eval/exec/os.system/subprocess(shell=True) in service code."""

    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_no_dangerous_calls(self, service):
        violations = []
        for py in _app_py_files(service):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                # eval(...) / exec(...)
                if isinstance(fn, ast.Name) and fn.id in {"eval", "exec"}:
                    violations.append(f"{py.relative_to(ROOT)}:{node.lineno} — {fn.id}()")
                # os.system(...)
                if isinstance(fn, ast.Attribute) and fn.attr == "system" and \
                        isinstance(fn.value, ast.Name) and fn.value.id == "os":
                    violations.append(f"{py.relative_to(ROOT)}:{node.lineno} — os.system()")
                # any call with shell=True
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        violations.append(f"{py.relative_to(ROOT)}:{node.lineno} — shell=True")
        assert violations == [], "Dangerous calls in service code:\n" + "\n".join(violations)


class TestReproducibleBuilds:
    """Every service Dockerfile pins its base image (no implicit/explicit latest)."""

    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_dockerfile_pins_base_image(self, service):
        dockerfile = service / "Dockerfile"
        if not dockerfile.exists():
            pytest.skip("no Dockerfile")
        bad = []
        for i, line in enumerate(dockerfile.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip().upper().startswith("FROM "):
                continue
            image = line.split()[1]  # FROM <image[:tag]> [AS stage]
            if ":" not in image or image.rsplit(":", 1)[1] == "latest":
                bad.append(f"{dockerfile.relative_to(ROOT)}:{i} — {image}")
        assert bad == [], "Unpinned base image (use an explicit tag, not latest):\n" + "\n".join(bad)
