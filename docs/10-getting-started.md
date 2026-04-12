# 10 — Getting started

From a fresh clone to a green test suite in under 15 minutes. No GCP
account needed, no secrets, nothing to register.

## Prerequisites

| Tool | Version | Used for |
|---|---|---|
| Python | 3.11+ | All six backend services |
| pip | 23+ | Installing service deps |
| Node | 20+ | wifi-intake-portal tests |
| git | any | Cloning and committing |
| (optional) Docker | 24+ | Building container images |
| (optional) Terraform | 1.5+ | Provisioning GCP infrastructure |
| (optional) gcloud | latest | GCP CLI for ops |
| (optional) gh | 2.0+ | GitHub CLI for setting repo secrets |

Only the first four are required for local development. The optional
tools are only needed when you're ready to deploy.

## Clone and install

```bash
git clone https://github.com/Compuute/.github.git
cd .github/kyrk-projekt

# Install dependencies for one service at a time. Each service has its
# own requirements.txt — they intentionally don't share a monorepo venv
# so a broken dep in one service can't break the others.
for svc in services/*/; do
  (cd "$svc" && pip install -q -r requirements.txt)
done
```

Or install them in editable mode in a single virtual environment — the
in-memory adapters mean none of the services need real GCP credentials.

## Run the tests

Every service is TDD-first. Run all of them:

```bash
# From kyrk-projekt/
for svc in services/*/; do
  echo "=== ${svc%/} ==="
  (cd "$svc" && pytest -q)
done

# And the Node-based portal tests
(cd frontend/wifi-intake-portal && node tests/test_content_decision.js)
```

Expected output: **148 passed** across all services, plus 6 Node asserts
in the portal. If anything is red, something is wrong with your install
— open an issue, don't paper over it.

## Run a service locally

Each service runs with **no external dependencies** in memory mode:

```bash
cd kyrk-projekt/services/membership-service
uvicorn app.main:app --reload --port 8001
```

Then:

```bash
# Health check
curl http://localhost:8001/healthz

# Create a member (the Fake auth adapter accepts `u-1:c-1:admin`)
curl -X POST http://localhost:8001/members \
  -H "Authorization: Bearer u-1:c-1:admin" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Anna",
    "last_name": "Andersson",
    "phone": "+4670000000",
    "email": "anna@example.se",
    "personal_number": "19800101-1234"
  }'
```

The service runs against the in-memory repository. Data is lost on
restart — that's intentional for local dev.

## Run the admin UI + two backends together

```bash
# Terminal 1 — membership-intake
cd kyrk-projekt/services/membership-intake
uvicorn app.main:app --reload --port 8002

# Terminal 2 — certificate-service
cd kyrk-projekt/services/certificate-service
uvicorn app.main:app --reload --port 8003

# Terminal 3 — admin-web pointing at both
cd kyrk-projekt/services/admin-web
INTAKE_BASE_URL=http://localhost:8002 \
CERTIFICATE_BASE_URL=http://localhost:8003 \
ADAPTER_MODE=production \
uvicorn app.main:app --reload --port 8080
```

Open <http://localhost:8080/login> in a browser and log in with any
`user:church:role` combo (e.g. `anna:stjohannes:pastor`). You'll see
the dashboard, submissions list, and certificate form. All data lives
in the two backend services' in-memory repos.

To seed test data, POST to the intake endpoint:

```bash
curl -X POST http://localhost:8002/intake \
  -H "Content-Type: application/json" \
  -d '{
    "church_id": "stjohannes",
    "first_name": "Anna",
    "last_name": "Andersson",
    "phone": "+4670000000",
    "email": "anna@example.se",
    "personal_number": "19800101-1234",
    "gdpr_consent": true,
    "consent_timestamp": "2025-06-01T10:00:00Z"
  }'
```

Refresh `/submissions` in the admin UI and the new pending submission
appears.

## Architecture in one diagram

```
RED (encrypted, authenticated)    YELLOW (aggregates)    GREEN (public / AI)
─────────────────────────────     ───────────────────    ────────────────────
membership-intake                 activity-service       wifi-intake-portal
membership-service                reporting-service      openclaw prompts
certificate-service                                      n8n sanitizer
admin-web (forwards user tokens)
```

RED → YELLOW is one-way aggregation. YELLOW → GREEN passes through the
sanitizer. GREEN → RED is forbidden. See
[`01-architecture-red-yellow-green.md`](01-architecture-red-yellow-green.md)
for the full rules.

## Next steps

- **Develop further** → [`11-development-guide.md`](11-development-guide.md)
- **Deploy to GCP** → [`12-operations.md`](12-operations.md)
- **Understand AI boundaries** → [`04-ai-boundaries.md`](04-ai-boundaries.md)
- **Auth strategy** → [`06-auth-strategy.md`](06-auth-strategy.md)
