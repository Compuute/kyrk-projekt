# admin-web

A minimal server-rendered admin UI for pastors and secretaries to:

- Review pending intake submissions (list, approve, reject)
- Issue digital certificates

Built as a thin FastAPI + Jinja2 service that calls the existing backend
services (`membership-intake`, `certificate-service`). It holds **no
domain state of its own** — all writes go through the downstream services
so RBAC, audit, and encryption are enforced exactly once, in the right
place.

## Stack

- FastAPI + Jinja2 templates
- Plain HTML forms, no JavaScript frameworks, no CDN scripts
- Cookie-based session (fake token in MVP; replaced by PropelAuth in production)
- HTTP clients are behind a port so tests use fake in-memory clients

## Why no React / HTMX / framework?

Same reasons as the wifi-intake-portal:
- Zero dependencies → faster page loads, easier audit
- No build pipeline
- Works on any device with a browser
- Progressive enhancement (HTMX) can be added later if a screen actually
  benefits from partial updates

## Pages

| Route | Purpose |
|---|---|
| `GET /login` | Login form (fake for MVP) |
| `POST /login` | Set session cookie |
| `GET /` | Dashboard with pending count + quick links |
| `GET /submissions` | List pending intake submissions |
| `POST /submissions/{id}/approve` | Approve, redirect back with flash |
| `POST /submissions/{id}/reject` | Reject, redirect back with flash |
| `GET /certificates/new` | Issue-certificate form |
| `POST /certificates/new` | Issue, redirect with verify URL |
| `POST /logout` | Clear session cookie |
| `GET /healthz` | Health probe |

## Running

```bash
pip install -r requirements.txt
pytest -q
INTAKE_BASE_URL=http://localhost:8001 \
CERTIFICATE_BASE_URL=http://localhost:8002 \
uvicorn app.main:app --reload --port 8080
```

## Security

- No direct DB access — every action goes through a downstream service.
- The cookie holds an opaque session token. The FakeAuth adapter treats
  it as `user_id:church_id:role` for MVP. Production wires in PropelAuth.
- Cookie is `HttpOnly`, `Secure` (in production), `SameSite=Lax`.
- CSRF is avoided in MVP because the fake login accepts any shape; real
  PropelAuth login will add a proper anti-CSRF flow.

## What is explicitly out of scope

- Inline editing / HTMX partials (can be added in a later PR without
  changing routes)
- Member search (RED, and deliberately not exposed publicly)
- KPI dashboards (future — reads `reporting-service`)
- OpenClaw review queue (future — reads `openclaw-pending` bucket)
