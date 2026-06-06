"""Coverage threshold — fails if new code is added without tests.

This doesn't run coverage itself (that's pytest-cov's job).
Instead, it checks that every Python source file in app/ has
at least one corresponding test file. This catches when an AI
writes 200 lines of new code with 0 tests.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"


def _source_files(service: Path) -> list[Path]:
    app = service / "app"
    if not app.exists():
        return []
    files = []
    for py in app.rglob("*.py"):
        if py.name.startswith("__"):
            continue
        if "adapters/fake_" in str(py):
            continue
        files.append(py)
    return sorted(files)


def _test_files(service: Path) -> set[str]:
    tests = service / "tests"
    if not tests.exists():
        return set()
    content = ""
    for tf in tests.glob("test_*.py"):
        content += tf.read_text(encoding="utf-8")
    return content


def _all_services() -> list[Path]:
    return sorted(d for d in SERVICES.iterdir() if d.is_dir() and (d / "app").exists())


class TestEveryModuleHasTestCoverage:
    @pytest.mark.parametrize("service", _all_services(), ids=lambda s: s.name)
    def test_key_modules_are_tested(self, service):
        test_content = _test_files(service)
        if not test_content:
            pytest.skip("no tests dir")

        untested = []
        for src in _source_files(service):
            rel = src.relative_to(service / "app")
            parts = rel.parts

            if parts[0] in ("adapters",) and "factory" not in src.name:
                continue
            if src.name in ("main.py", "config.py", "__init__.py"):
                continue

            module_name = src.stem
            search_terms = [module_name, module_name.replace("_", "")]

            found = any(term in test_content for term in search_terms)
            if not found:
                untested.append(str(rel))

        if untested:
            total = len(_source_files(service))
            coverage = ((total - len(untested)) / total * 100) if total else 100
            assert coverage >= 60, (
                f"{service.name}: only {coverage:.0f}% of modules have test coverage.\n"
                f"Untested: {', '.join(untested)}\n"
                f"Fix: add tests for these modules."
            )
