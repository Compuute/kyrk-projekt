"""Guard: routes and ports must NEVER import vendor libraries directly.

All external dependencies must go through the adapter layer (app/adapters/).
This test fails CI if someone accidentally imports httpx, anthropic,
google-cloud, firebase, or propelauth in routes.py or any port file.

The pattern:
  routes.py → ports (Protocol) → adapters (vendor-specific)
  NEVER: routes.py → vendor library directly
"""
import ast
from pathlib import Path

import pytest

ADMIN_WEB = Path(__file__).resolve().parent.parent

VENDOR_MODULES = {
    "httpx",
    "anthropic",
    "google",
    "google.cloud",
    "firebase_admin",
    "propelauth_fastapi",
    "propelauth_py",
    "requests",
    "boto3",
    "azure",
}

PROTECTED_DIRS = [
    ADMIN_WEB / "app" / "api",
    ADMIN_WEB / "app" / "ports",
]


def _find_vendor_imports(filepath: Path) -> list[str]:
    source = filepath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in VENDOR_MODULES:
                    violations.append(
                        f"{filepath.name}:{node.lineno} — import {alias.name}"
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in VENDOR_MODULES:
                violations.append(
                    f"{filepath.name}:{node.lineno} — from {node.module} import ..."
                )
    return violations


class TestNoVendorLockIn:
    @pytest.mark.parametrize("protected_dir", PROTECTED_DIRS, ids=["api", "ports"])
    def test_no_vendor_imports(self, protected_dir):
        violations = []
        for py in sorted(protected_dir.glob("*.py")):
            violations.extend(_find_vendor_imports(py))

        assert violations == [], (
            f"Vendor lock-in detected! These files import vendor libraries directly:\n"
            + "\n".join(f"  {v}" for v in violations)
            + "\n\nFix: move the vendor import to app/adapters/ and use a Port protocol."
        )
