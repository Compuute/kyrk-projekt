"""Unit tests for ops-cli command logic (drift check + health probes).

Regression coverage for two verified bugs (2026-06-11):

1. cmd_drift_check trusted a substring match on "changes", which also matches
   terraform's "No changes." message — drift was always reported. The
   `| tail -20` pipe additionally replaced terraform's -detailed-exitcode
   status (0=no changes, 2=changes, 1=error) with tail's exit code.
2. cmd_health probed Cloud Run /healthz without authentication. The services
   are not public (unauthenticated requests get 403), so every healthy
   service was reported unhealthy. The probe must send an identity token.
   All services route /healthz (services/*/app/main.py) — /health does not
   exist and returns 404 even with a valid token.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = ROOT / "ops" / "ops-cli.py"


@pytest.fixture()
def ops_cli():
    spec = importlib.util.spec_from_file_location("ops_cli", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_and_capture(capsys):
    """Return (json_output, exit_code) from a command that calls sys.exit."""
    out = capsys.readouterr().out
    return json.loads(out)


class TestDriftCheck:
    def test_no_changes_output_is_not_drift(self, ops_cli, capsys, monkeypatch):
        """Terraform exit 0 + 'No changes.' message must NOT count as drift."""
        monkeypatch.setattr(
            ops_cli, "run_cmd",
            lambda cmd, timeout=30: (0, "No changes. Your infrastructure matches the configuration."),
        )
        with pytest.raises(SystemExit) as exc:
            ops_cli.cmd_drift_check()
        data = run_and_capture(capsys)
        assert data["has_drift"] is False
        assert exc.value.code == 0

    def test_exitcode_2_is_drift(self, ops_cli, capsys, monkeypatch):
        monkeypatch.setattr(
            ops_cli, "run_cmd",
            lambda cmd, timeout=30: (2, "Plan: 1 to add, 0 to change, 0 to destroy."),
        )
        with pytest.raises(SystemExit) as exc:
            ops_cli.cmd_drift_check()
        data = run_and_capture(capsys)
        assert data["has_drift"] is True
        assert exc.value.code == 1

    def test_exitcode_1_is_error_not_drift(self, ops_cli, capsys, monkeypatch):
        """Terraform errors must be reported as errors, not as drift."""
        monkeypatch.setattr(
            ops_cli, "run_cmd",
            lambda cmd, timeout=30: (1, "Error: Failed to load backend"),
        )
        with pytest.raises(SystemExit) as exc:
            ops_cli.cmd_drift_check()
        data = run_and_capture(capsys)
        assert data["has_drift"] is False
        assert data["error"] is True
        assert exc.value.code not in (0, 1)

    def test_terraform_exit_code_not_destroyed_by_pipe(self, ops_cli, monkeypatch):
        """No `| tail` pipe — it replaces terraform's -detailed-exitcode."""
        seen = []

        def fake_run_cmd(cmd, timeout=30):
            seen.append(cmd)
            return 0, "No changes."

        monkeypatch.setattr(ops_cli, "run_cmd", fake_run_cmd)
        with pytest.raises(SystemExit):
            ops_cli.cmd_drift_check()
        assert len(seen) == 1
        assert "| tail" not in seen[0]
        assert "-detailed-exitcode" in seen[0]

    def test_long_output_truncated_in_python(self, ops_cli, capsys, monkeypatch):
        long_output = "\n".join(f"resource line {i}" for i in range(200))
        monkeypatch.setattr(ops_cli, "run_cmd", lambda cmd, timeout=30: (2, long_output))
        with pytest.raises(SystemExit):
            ops_cli.cmd_drift_check()
        data = run_and_capture(capsys)
        assert len(data["summary"]) <= 500


class TestHealth:
    URL = "https://membership-service-oixhrgkhpq-lz.a.run.app"

    def make_run_cmd(self, seen, http_code="200", token_ok=True):
        def fake_run_cmd(cmd, timeout=30, **kwargs):
            seen.append(cmd)
            if "status.url" in cmd:
                return 0, self.URL
            if "latestReadyRevisionName" in cmd:
                return 0, "rev-001"
            if "print-identity-token" in cmd:
                if "--audiences" in cmd and not token_ok:
                    return 1, "ERROR: Invalid account type for `--audiences`."
                return 0, "tok-abc123"
            if "curl" in cmd:
                return 0, http_code
            raise AssertionError(f"unexpected command: {cmd}")
        return fake_run_cmd

    def patch_all(self, ops_cli, monkeypatch, **kwargs):
        seen = []
        fake = self.make_run_cmd(seen, **kwargs)
        monkeypatch.setattr(ops_cli, "run_cmd", fake)
        # get_identity_token must bypass the PII filter (it can corrupt
        # digit runs inside a JWT), so it may not go through run_cmd —
        # patch its unfiltered runner too if present.
        if hasattr(ops_cli, "run_cmd_unfiltered"):
            monkeypatch.setattr(ops_cli, "run_cmd_unfiltered", fake)
        monkeypatch.setattr(ops_cli, "SERVICES", ["membership-service"])
        return seen

    def test_healthy_with_authenticated_probe(self, ops_cli, capsys, monkeypatch):
        """200 from /healthz with identity token → healthy, exit 0."""
        seen = self.patch_all(ops_cli, monkeypatch)
        with pytest.raises(SystemExit) as exc:
            ops_cli.cmd_health("dev")
        data = run_and_capture(capsys)
        assert data["all_healthy"] is True
        assert data["services"][0]["status"] == "healthy"
        assert exc.value.code == 0

        curl_cmds = [c for c in seen if "curl" in c]
        assert len(curl_cmds) == 1
        assert "Authorization: Bearer tok-abc123" in curl_cmds[0]
        assert "/healthz" in curl_cmds[0]
        # /health does not exist on any service (404 even with valid token)
        assert "/health'" not in curl_cmds[0]

    def test_unhealthy_on_403(self, ops_cli, capsys, monkeypatch):
        self.patch_all(ops_cli, monkeypatch, http_code="403")
        with pytest.raises(SystemExit) as exc:
            ops_cli.cmd_health("dev")
        data = run_and_capture(capsys)
        assert data["all_healthy"] is False
        assert data["services"][0]["status"] == "unhealthy"
        assert exc.value.code == 1

    def test_token_falls_back_when_audiences_unsupported(self, ops_cli, capsys, monkeypatch):
        """User credentials reject --audiences; plain token must be used."""
        seen = self.patch_all(ops_cli, monkeypatch, token_ok=False)
        with pytest.raises(SystemExit) as exc:
            ops_cli.cmd_health("dev")
        data = run_and_capture(capsys)
        assert data["all_healthy"] is True
        assert exc.value.code == 0
        token_cmds = [c for c in seen if "print-identity-token" in c]
        assert any("--audiences" not in c for c in token_cmds), (
            "must fall back to a plain identity token when --audiences fails"
        )

    def test_token_never_printed_in_output(self, ops_cli, capsys, monkeypatch):
        """The identity token is a credential — it may not leak into JSON."""
        self.patch_all(ops_cli, monkeypatch)
        with pytest.raises(SystemExit):
            ops_cli.cmd_health("dev")
        assert "tok-abc123" not in capsys.readouterr().out
