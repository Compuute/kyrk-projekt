"""Audit-sidans dokumentlänkar: rollscoping + git som enda källa.

Säkerhetsdocs (defense-in-depth, säkerhetsprinciper, incident-runbook) är
rekon-material → endast admin/pastor. Compliance-docs (GDPR-register,
retention, integritetspolicy) → alla inloggade roller. Inget serveras från
containern; länkarna pekar på det åtkomststyrda GitHub-repot.
"""
from __future__ import annotations

import pytest

SECURITY_DOCS = [
    "16-defense-in-depth.md",
    "05-security-principles.md",
    "13-runbook.md",
]
COMPLIANCE_DOCS = [
    "gdpr-register.md",
    "policies.md",
]


def _login(client, role: str):
    client.cookies.set("kyrk_session", f"u-1:c1:{role}")
    return client


def test_audit_requires_auth(client):
    assert client.get("/audit").status_code == 302


@pytest.mark.parametrize("role", ["admin", "pastor"])
def test_security_docs_visible_to_admin_and_pastor(client, role):
    r = _login(client, role).get("/audit")
    assert r.status_code == 200
    for doc in SECURITY_DOCS:
        assert doc in r.text, f"{role} ska se {doc}"


@pytest.mark.parametrize("role", ["editor", "viewer"])
def test_security_docs_hidden_from_editor_and_viewer(client, role):
    r = _login(client, role).get("/audit")
    assert r.status_code == 200
    for doc in SECURITY_DOCS:
        assert doc not in r.text, f"{role} ska INTE se {doc} (rekon-material)"
    # Men compliance-docs ska synas för alla inloggade roller.
    for doc in COMPLIANCE_DOCS:
        assert doc in r.text, f"{role} ska se compliance-doc {doc}"


def test_docs_link_to_github_repo_not_served_from_container(client):
    """Git är enda källan — länkar pekar på repot, inget renderas från disk."""
    r = _login(client, "admin").get("/audit")
    assert "github.com/Compuute/kyrk-projekt/blob/main" in r.text
    # Sidan ska inte servera doc-innehåll via en egen route.
    assert "/audit/doc/" not in r.text
    assert "raw" not in r.text.lower() or "github" in r.text.lower()
