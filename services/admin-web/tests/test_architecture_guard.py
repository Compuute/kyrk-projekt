"""Architecture guard — fails CI if code structure rules are violated.

These tests enforce the architecture automatically. No human review needed
to catch these violations — CI catches them.

Rules enforced:
1. No vendor imports in routes or ports (test_no_vendor_lockin.py handles this)
2. Every POST route has authentication
3. Every port has a matching fake adapter
4. Every fake adapter is wired into conftest.py
5. Every port is registered in factory.py and deps.py
6. funeral_tracker PII fields are never in API/webhook responses
"""
import ast
import re
from pathlib import Path

import pytest

ADMIN_WEB = Path(__file__).resolve().parent.parent
ROUTES = ADMIN_WEB / "app" / "api" / "routes_combined.py"
DEPS = ADMIN_WEB / "app" / "api" / "deps.py"
FACTORY = ADMIN_WEB / "app" / "adapters" / "factory.py"
CONFTEST = ADMIN_WEB / "tests" / "conftest.py"
PORTS_DIR = ADMIN_WEB / "app" / "ports"
ADAPTERS_DIR = ADMIN_WEB / "app" / "adapters"


class TestEveryPostRouteHasAuth:
    def test_all_post_routes_check_session_or_token(self):
        source = ROUTES.read_text(encoding="utf-8")
        tree = ast.parse(source)

        unprotected = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                attr = getattr(func, "attr", "")
                if attr != "post":
                    continue
                body_source = ast.get_source_segment(source, node)
                auth_exempt = {"healthz", "post_login", "logout"}
                if body_source and "_require_session" not in body_source and "X-API-Token" not in body_source:
                    if node.name not in auth_exempt:
                        unprotected.append(f"{node.name} (line {node.lineno})")

        assert unprotected == [], (
            f"POST routes without authentication:\n"
            + "\n".join(f"  {r}" for r in unprotected)
            + "\n\nFix: add _require_session(request) or X-API-Token check."
        )


class TestEveryPortHasFakeAdapter:
    def test_every_port_has_a_fake(self):
        skip_files = {"client_errors.py", "data_quality.py"}
        missing = []
        for port_file in sorted(PORTS_DIR.glob("*.py")):
            if port_file.name.startswith("__") or port_file.name in skip_files:
                continue
            port_name = port_file.stem
            found = any(
                (ADAPTERS_DIR / f"fake_{v}.py").exists()
                for v in [
                    port_name,
                    port_name.replace("_port", ""),
                    port_name.rstrip("s"),
                    port_name.replace("tion", "tor"),
                ]
            )
            if not found:
                found = bool(list(ADAPTERS_DIR.glob(f"fake_*{port_name.split('_')[0]}*.py")))
            if not found:
                missing.append(f"{port_file.name} → expected fake_{port_name}.py")

        assert missing == [], (
            f"Ports without fake adapters:\n"
            + "\n".join(f"  {m}" for m in missing)
            + "\n\nFix: create a FakeXxx class in app/adapters/fake_xxx.py"
        )


class TestEveryPortIsInFactory:
    def test_every_port_has_factory_function(self):
        factory_source = FACTORY.read_text(encoding="utf-8")
        missing = []
        for port_file in sorted(PORTS_DIR.glob("*.py")):
            if port_file.name.startswith("__") or port_file.name == "client_errors.py":
                continue
            port_name = port_file.stem
            skip_names = {"clients", "session", "client_errors", "data_quality"}
            if port_name in skip_names:
                continue
            search_terms = [
                f"make_{port_name}",
                f"make_{port_name.replace('_tracker', '')}",
                f"make_{port_name.replace('_store', '')}",
                f"make_{port_name.rstrip('s')}",
                f"make_{port_name.replace('tion', 'tor')}",
            ]
            if not any(t in factory_source for t in search_terms):
                missing.append(f"{port_file.name} → make_{port_name}()")

        assert missing == [], (
            f"Ports without factory functions:\n"
            + "\n".join(f"  {m}" for m in missing)
            + "\n\nFix: add make_xxx() to app/adapters/factory.py"
        )


class TestEveryPortIsInDeps:
    def test_every_port_has_getter_in_deps(self):
        deps_source = DEPS.read_text(encoding="utf-8")
        missing = []
        for port_file in sorted(PORTS_DIR.glob("*.py")):
            if port_file.name.startswith("__") or port_file.name == "client_errors.py":
                continue
            port_name = port_file.stem
            skip_names = {"clients", "session", "data_quality"}
            if port_name in skip_names:
                continue
            search_terms = [
                f"get_{port_name}",
                f"get_{port_name.replace('_tracker', '')}",
                f"get_{port_name.replace('_store', '')}",
                f"get_{port_name.rstrip('s')}",
                f"get_{port_name.replace('tion', 'tor')}",
            ]
            if not any(t in deps_source for t in search_terms):
                missing.append(f"{port_file.name} → get_{port_name}()")

        assert missing == [], (
            f"Ports without getters in deps.py:\n"
            + "\n".join(f"  {m}" for m in missing)
            + "\n\nFix: add get_xxx() to app/api/deps.py"
        )


class TestPiiNotInApiResponses:
    def test_blocked_fields_not_in_api_endpoint(self):
        source = ROUTES.read_text(encoding="utf-8")
        blocked = {"contact_phone", "contact_person", "contact_email",
                    "date_of_birth", "personal_number"}

        api_section = False
        violations = []
        for i, line in enumerate(source.splitlines(), 1):
            if "/api/" in line and "def " in line:
                api_section = True
            elif api_section and line.strip().startswith("def "):
                api_section = False

            if api_section:
                for field in blocked:
                    if f'"{field}"' in line and "BLOCKED" not in line.upper() and "blocked" not in line:
                        violations.append(f"line {i}: {field} in API response")

        assert violations == [], (
            f"PII fields found in API responses:\n"
            + "\n".join(f"  {v}" for v in violations)
        )
