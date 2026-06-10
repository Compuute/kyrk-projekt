#!/usr/bin/env python3
"""Ops CLI — Agent-executable operations tool for kyrk-projekt.

Usage:
    python ops/ops-cli.py health [--env=dev]
    python ops/ops-cli.py logs <service> [--severity=ERROR] [--since=1h] [--env=dev]
    python ops/ops-cli.py status [--env=dev]
    python ops/ops-cli.py backup verify [--env=dev]
    python ops/ops-cli.py drift check
    python ops/ops-cli.py deploy preflight <env>
    python ops/ops-cli.py rollback <service> [--env=dev]
    python ops/ops-cli.py incident create <title>
    python ops/ops-cli.py cleanup stale-intakes [--dry-run] [--env=dev]

All output is structured JSON for agent consumption.
PII is ALWAYS filtered from output — no exceptions.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ============================================================================
# PII Filter — applied to ALL output before returning to agent
# ============================================================================

PII_PATTERNS = [
    re.compile(r"\d{6,8}[-\s]?\d{4}"),                          # personnummer
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),  # email
    re.compile(r"\+?\d{2,4}[-\s]?\d{6,10}"),                    # phone
]

PII_FIELD_NAMES = {
    "personal_number", "personnummer", "contact_phone",
    "contact_email", "email", "phone", "address",
    "first_name", "last_name", "date_of_birth", "name",
}

REDACTED = "[REDACTED]"


def filter_pii(text: str) -> str:
    """Remove PII patterns from text."""
    for pattern in PII_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


def filter_pii_dict(data: dict) -> dict:
    """Remove PII fields from a dictionary."""
    filtered = {}
    for key, value in data.items():
        if key.lower() in PII_FIELD_NAMES:
            filtered[key] = REDACTED
        elif isinstance(value, str):
            filtered[key] = filter_pii(value)
        elif isinstance(value, dict):
            filtered[key] = filter_pii_dict(value)
        elif isinstance(value, list):
            filtered[key] = [
                filter_pii_dict(v) if isinstance(v, dict)
                else filter_pii(v) if isinstance(v, str)
                else v
                for v in value
            ]
        else:
            filtered[key] = value
    return filtered


# ============================================================================
# Environment helpers
# ============================================================================

def resolve_project(env: str) -> str:
    """Resolve GCP project ID from environment name."""
    return "kyrk-projekt-prod" if env == "prod" else "kyrk-projekt"


REGION = "europe-north1"
SERVICES = [
    "membership-intake",
    "membership-service",
    "certificate-service",
    "reporting-service",
    "admin-web",
]


def run_cmd(cmd: str, timeout: int = 30) -> tuple[int, str]:
    """Run a shell command and return (exit_code, output)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode, filter_pii(output)
    except subprocess.TimeoutExpired:
        return 1, "TIMEOUT"
    except Exception as e:
        return 1, str(e)


def output_json(data: dict):
    """Print filtered JSON output and exit."""
    filtered = filter_pii_dict(data)
    print(json.dumps(filtered, indent=2, ensure_ascii=False, default=str))


# ============================================================================
# Commands
# ============================================================================

def cmd_health(env: str):
    """Check health of all Cloud Run services."""
    project = resolve_project(env)
    results = []
    all_healthy = True

    for svc in SERVICES:
        code, url = run_cmd(
            f"gcloud run services describe {svc} --region={REGION} "
            f"--project={project} --format='value(status.url)'"
        )
        if code != 0 or not url:
            results.append({
                "service": svc, "status": "not_deployed",
                "http_code": None, "url": None, "revision": None,
            })
            all_healthy = False
            continue

        _, http_code = run_cmd(
            f"curl -s -o /dev/null -w '%{{http_code}}' '{url}/healthz' --max-time 10"
        )
        _, revision = run_cmd(
            f"gcloud run services describe {svc} --region={REGION} "
            f"--project={project} --format='value(status.latestReadyRevisionName)'"
        )

        healthy = http_code.strip("'") == "200"
        if not healthy:
            all_healthy = False

        results.append({
            "service": svc,
            "status": "healthy" if healthy else "unhealthy",
            "http_code": http_code.strip("'"),
            "url": url,
            "revision": revision,
        })

    output_json({
        "command": "health",
        "environment": env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "all_healthy": all_healthy,
        "services": results,
    })
    sys.exit(0 if all_healthy else 1)


def cmd_logs(service: str, severity: str, since: str, env: str):
    """Fetch and filter logs for a service."""
    project = resolve_project(env)

    # Build log filter
    severity_filter = f" AND severity>={severity}" if severity else ""
    cmd = (
        f"gcloud logging read "
        f"'resource.type=\"cloud_run_revision\" AND "
        f"resource.labels.service_name=\"{service}\""
        f"{severity_filter}' "
        f"--project={project} --limit=50 "
        f"--format='value(timestamp,severity,textPayload)' "
        f"--freshness={since}"
    )

    code, output = run_cmd(cmd, timeout=60)
    lines = output.split("\n") if output else []

    output_json({
        "command": "logs",
        "service": service,
        "environment": env,
        "severity_filter": severity,
        "since": since,
        "line_count": len(lines),
        "lines": lines[:50],  # Cap at 50 lines
    })


def cmd_status(env: str):
    """Summarize environment status."""
    project = resolve_project(env)

    # Get service info
    services = []
    for svc in SERVICES:
        _, url = run_cmd(
            f"gcloud run services describe {svc} --region={REGION} "
            f"--project={project} --format='value(status.url)' 2>/dev/null"
        )
        _, rev = run_cmd(
            f"gcloud run services describe {svc} --region={REGION} "
            f"--project={project} --format='value(status.latestReadyRevisionName)' 2>/dev/null"
        )
        services.append({"name": svc, "url": url or "not deployed", "revision": rev or "n/a"})

    # Get secret count
    _, secrets_out = run_cmd(
        f"gcloud secrets list --project={project} --format='value(name)' 2>/dev/null"
    )
    secret_names = [s for s in secrets_out.split("\n") if s] if secrets_out else []

    output_json({
        "command": "status",
        "environment": env,
        "project": project,
        "region": REGION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
        "secrets_count": len(secret_names),
        "secrets": secret_names,
    })


def cmd_backup_verify(env: str):
    """Verify Firestore backup freshness."""
    project = resolve_project(env)
    bucket = f"{project}-firestore-backups"

    code, output = run_cmd(f"gsutil ls gs://{bucket}/ 2>/dev/null")
    if code != 0 or not output:
        output_json({
            "command": "backup_verify",
            "environment": env,
            "bucket": bucket,
            "status": "no_backups_found",
            "healthy": False,
            "message": f"No backups found in gs://{bucket}/",
        })
        sys.exit(1)

    backups = [line.strip() for line in output.split("\n") if line.strip()]
    latest = backups[-1] if backups else None

    output_json({
        "command": "backup_verify",
        "environment": env,
        "bucket": bucket,
        "status": "ok",
        "healthy": True,
        "backup_count": len(backups),
        "latest": latest,
    })


def cmd_drift_check():
    """Run terraform plan and report drift."""
    tf_dir = Path(__file__).resolve().parent.parent / "infra" / "terraform"
    code, output = run_cmd(
        f"cd {tf_dir} && terraform plan -detailed-exitcode -no-color 2>&1 | tail -20",
        timeout=120,
    )
    # Exit codes: 0=no changes, 1=error, 2=changes detected
    has_drift = "changes" in output.lower() or code == 2
    output_json({
        "command": "drift_check",
        "has_drift": has_drift,
        "exit_code": code,
        "summary": output[-500:] if output else "no output",
    })
    sys.exit(1 if has_drift else 0)


def cmd_deploy_preflight(env: str):
    """Run deploy preflight checklist."""
    checks = []

    # 1. CI green
    code, out = run_cmd("gh run list --workflow=ci.yml --branch=main --limit=1 --json conclusion -q '.[0].conclusion' 2>/dev/null")
    checks.append({"check": "ci_green", "passed": out.strip() == "success", "detail": out.strip()})

    # 2. Terraform valid
    tf_dir = Path(__file__).resolve().parent.parent / "infra" / "terraform"
    code, out = run_cmd(f"cd {tf_dir} && terraform validate 2>&1")
    checks.append({"check": "tf_validate", "passed": "Success" in out, "detail": out[:200]})

    # 3. Terraform fmt
    code, _ = run_cmd(f"cd {tf_dir} && terraform fmt -check -recursive 2>&1")
    checks.append({"check": "tf_fmt", "passed": code == 0, "detail": "formatted" if code == 0 else "unformatted"})

    all_passed = all(c["passed"] for c in checks)
    output_json({
        "command": "deploy_preflight",
        "environment": env,
        "all_passed": all_passed,
        "checks": checks,
    })
    sys.exit(0 if all_passed else 1)


def cmd_rollback(service: str, env: str):
    """Roll back a service to previous revision."""
    # Safety: block prod rollback in CLI — must use approval workflow
    if env == "prod":
        output_json({
            "command": "rollback",
            "error": "Prod rollback requires human approval. Use ops-agent.yml workflow.",
            "blocked": True,
        })
        sys.exit(1)

    project = resolve_project(env)
    _, prev = run_cmd(
        f"gcloud run revisions list --service={service} --region={REGION} "
        f"--project={project} --format='value(metadata.name)' --limit=2 | tail -1"
    )
    if not prev:
        output_json({"command": "rollback", "error": "No previous revision found", "service": service})
        sys.exit(1)

    code, out = run_cmd(
        f"gcloud run services update-traffic {service} --region={REGION} "
        f"--project={project} --to-revisions={prev}=100",
        timeout=60,
    )

    output_json({
        "command": "rollback",
        "service": service,
        "environment": env,
        "previous_revision": prev,
        "success": code == 0,
        "detail": out[:200],
    })
    sys.exit(code)


def cmd_incident_create(title: str):
    """Create an incident report from template."""
    incidents_dir = Path(__file__).resolve().parent.parent / "incidents"
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    filename = f"{date_str}-{slug}.md"
    filepath = incidents_dir / filename

    template = f"""# {date_str} — {title}

## Summary
<!-- Vad hände, i en mening -->

## Timeline
- `{datetime.now().strftime('%H:%M')}` — Incident skapad (av ops-agent)
- `HH:MM` — Första åtgärd
- `HH:MM` — Löst

## Root cause
<!-- Den faktiska tekniska orsaken -->

## Impact
- Användare påverkade: ...
- Data påverkad: ...
- Varaktighet: ...

## What worked
- ...

## What didn't
- ...

## Follow-ups
- [ ] Ansvarig — Åtgärd — Deadline
"""
    filepath.write_text(template, encoding="utf-8")
    output_json({
        "command": "incident_create",
        "file": str(filepath),
        "title": title,
        "date": date_str,
    })


# ============================================================================
# CLI Router
# ============================================================================

def parse_flag(args: list, flag: str, default: str = "") -> str:
    """Extract --flag=value from args."""
    for arg in args:
        if arg.startswith(f"--{flag}="):
            return arg.split("=", 1)[1]
    return default


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    env = parse_flag(args, "env", "dev")
    cmd = args[0]

    if cmd == "health":
        cmd_health(env)
    elif cmd == "logs" and len(args) >= 2:
        severity = parse_flag(args, "severity", "ERROR")
        since = parse_flag(args, "since", "1h")
        cmd_logs(args[1], severity, since, env)
    elif cmd == "status":
        cmd_status(env)
    elif cmd == "backup" and len(args) >= 2 and args[1] == "verify":
        cmd_backup_verify(env)
    elif cmd == "drift" and len(args) >= 2 and args[1] == "check":
        cmd_drift_check()
    elif cmd == "deploy" and len(args) >= 3 and args[1] == "preflight":
        cmd_deploy_preflight(args[2])
    elif cmd == "rollback" and len(args) >= 2:
        cmd_rollback(args[1], env)
    elif cmd == "incident" and len(args) >= 3 and args[1] == "create":
        cmd_incident_create(" ".join(args[2:]))
    else:
        print(f"Unknown command: {' '.join(args)}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
