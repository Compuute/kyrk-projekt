# kyrk-projekt

Modular, secure, mobile-first church platform on Google Cloud Platform.

## TL;DR for a new engineer

```bash
git clone https://github.com/Compuute/.github.git
cd .github/kyrk-projekt

make install   # pip install all service requirements
make test      # run all 148+ tests across every service
```

Then pick one of:

- **Develop locally** → [`docs/10-getting-started.md`](docs/10-getting-started.md)
- **Add a feature** → [`docs/11-development-guide.md`](docs/11-development-guide.md)
- **Deploy to GCP** → [`docs/12-operations.md`](docs/12-operations.md) (runs `scripts/bootstrap.sh`)

## Architecture zones

- **RED** — sensitive identity, membership, certificates (encrypted, no public search)
- **YELLOW** — aggregates only, KPI, reporting, ROI
- **GREEN** — strategy, content, AI (OpenClaw), impact, Wi-Fi portal

## Principles

- Security by design
- Sovereignty by design (EU regions only)
- GDPR (Sweden)
- Data minimization (spårminimering)
- Human-in-the-loop for all AI outputs
- TDD-first, mobile-first, modular, multi-tenant (`church_id`)
- Low cost (nonprofit context)

## Services

| Service | Zone | Purpose |
|---|---|---|
| `services/membership-intake` | RED | Public intake form + admin approval flow |
| `services/membership-service` | RED | Member lifecycle, RBAC, audit, field-level encryption |
| `services/certificate-service` | RED | Digital certificates + privacy-preserving verification |
| `services/reporting-service` | YELLOW | Activity tracking + KPI/ROI reports + BigQuery export (merged from activity+reporting — see [ADR-010](docs/14-architecture-decisions.md)) |
| `services/admin-web` | mixed | Server-rendered admin UI. Intake approval, certificate issuance, **KPI dashboard** |

Each service:
- Ships a `Dockerfile` and runs as a non-root user
- Exposes `/healthz` for Cloud Run probes
- Has two adapter modes selected by `ADAPTER_MODE`: `memory` (default,
  in-process) for tests and local dev, `production` (Firestore + KMS +
  PropelAuth + BigQuery) for Cloud Run
- Has its own `requirements.txt` and `pytest.ini` — services never share a venv

## Frontend

| Module | Zone | Stack |
|---|---|---|
| `frontend/wifi-intake-portal` | GREEN | static HTML + vanilla JS, content pushed by n8n |
| `frontend/mobile-web` | mixed | placeholder for a future member-facing client |

The day-to-day admin UI lives in `services/admin-web` — see above.

## Automation

- `automation/n8n` — five workflow definitions (self-hosted n8n on Cloud Run)
- `automation/openclaw` — prompt templates + sanitizer profiles (Anthropic API via n8n)

## Infra

- `infra/terraform` — GCP baseline: Cloud Run, Firestore, GCS, Secret
  Manager, IAM, KMS, BigQuery, Workload Identity Federation, Artifact
  Registry. One `terraform apply` provisions the entire platform.

## CI / CD

Three GitHub Actions workflows live at the repo root in
[`.github/workflows/`](../.github/workflows/):

- `ci.yml` — pytest across all services, wifi-portal Node tests,
  Python syntax check, and `terraform validate` on every push and PR.
  No secrets, no GCP access.
- `deploy.yml` — manual workflow that builds container images, pushes
  them to Artifact Registry, and deploys to Cloud Run via Workload
  Identity Federation (no static GCP keys in GitHub). Uses GitHub
  environments (`dev`/`prod`) for per-environment secrets and
  required-reviewer protection.
- `e2e.yml` — runs automatically after a successful deploy; curls
  `/healthz` on all six services and runs a minimal smoke test of the
  public intake POST, certificate verify 404, and admin-web login page.

See [`.github/workflows/README.md`](../.github/workflows/README.md) for
the one-time GCP setup.

## Docs index

| File | What it covers |
|---|---|
| [`docs/00-vision.md`](docs/00-vision.md) | Mission, target users, product pillars, non-goals |
| [`docs/01-architecture-red-yellow-green.md`](docs/01-architecture-red-yellow-green.md) | The zone model and flow rules |
| [`docs/02-sovereignty.md`](docs/02-sovereignty.md) | EU data residency, vendor review |
| [`docs/03-mvp-scope.md`](docs/03-mvp-scope.md) | What's in and out of MVP |
| [`docs/04-ai-boundaries.md`](docs/04-ai-boundaries.md) | What OpenClaw may and may not see, incident response |
| [`docs/05-security-principles.md`](docs/05-security-principles.md) | Concrete security rules for code changes |
| [`docs/06-auth-strategy.md`](docs/06-auth-strategy.md) | PropelAuth today, BankID Phase 2 |
| [`docs/07-openclaw-production-flow.md`](docs/07-openclaw-production-flow.md) | n8n → sanitizer → Anthropic → human review |
| **[`docs/10-getting-started.md`](docs/10-getting-started.md)** | **Onboarding: git clone → tests green in 15 minutes** |
| **[`docs/11-development-guide.md`](docs/11-development-guide.md)** | **Adapter pattern, adding endpoints, adding services** |
| **[`docs/12-operations.md`](docs/12-operations.md)** | **Deploy, rollback, monitoring, incident response** |
| [`docs/ai-context.md`](docs/ai-context.md) | Copy-paste context block for Claude Code sessions |
| [`docs/governance/rbac.md`](docs/governance/rbac.md) | Role matrix |
| [`docs/governance/policies.md`](docs/governance/policies.md) | Retention, deletion, access reviews |
| [`docs/governance/security-review-template.md`](docs/governance/security-review-template.md) | PR checklist for RED / sanitizer / IAM changes |
| [`docs/13-runbook.md`](docs/13-runbook.md) | Incident playbooks for 5 common scenarios |
| **[`docs/14-architecture-decisions.md`](docs/14-architecture-decisions.md)** | **11 ADRs — why every major choice was made** |
| [`docs/15-ab-testing-strategy.md`](docs/15-ab-testing-strategy.md) | When to introduce A/B testing (Phase 3) |
| **[`docs/16-defense-in-depth.md`](docs/16-defense-in-depth.md)** | **Defense-in-depth policy — how to evaluate service merges/splits** |
| [`docs/architecture/threat-model.md`](docs/architecture/threat-model.md) | STRIDE walkthrough |
| [`docs/impact/impact-blueprint.md`](docs/impact/impact-blueprint.md) | Reusable module spec + three initial modules |
| [`.github/workflows/README.md`](../.github/workflows/README.md) | Full CI/CD reference |

## Common commands

```bash
make test                    # full suite
make test-membership-service # one service
make lint                    # syntax check + terraform fmt
make bootstrap ENV=dev       # first-time GCP + GitHub setup
make deploy ENV=dev          # trigger deploy.yml via gh
make smoke ENV=dev           # curl /healthz on all five services
make clean                   # remove caches
```

## Auth

MVP uses **PropelAuth** for multi-tenant RBAC. BankID is an
interface/stub for Phase 2. See
[`docs/06-auth-strategy.md`](docs/06-auth-strategy.md).
