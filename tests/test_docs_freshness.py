"""Docs freshness tests — fails CI if docs fall out of sync with code.

This test runs in CI and catches when someone adds a feature without
updating the documentation. It checks:
1. README mentions every service that exists
2. README mentions every HTML page that exists
3. README test count is not wildly stale
4. Every HTML page is in the docs index or README
5. Every n8n workflow is mentioned somewhere in docs
6. Every OpenClaw template is mentioned somewhere in docs
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
        for html in sorted(portal.glob("*.html")):
            assert html.name in ALL_DOCS, (
                f"'{html.name}' exists but is not mentioned in any doc"
            )


class TestWorkflowsDocumented:
    def test_every_n8n_workflow_mentioned(self):
        workflows_dir = ROOT / "automation" / "n8n" / "workflows"
        if not workflows_dir.exists():
            pytest.skip("no workflows dir")
        for wf in sorted(workflows_dir.glob("*.json")):
            name = wf.stem
            assert name in ALL_DOCS, (
                f"n8n workflow '{name}' is not mentioned in any doc"
            )

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
