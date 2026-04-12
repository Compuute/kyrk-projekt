# 11 — Development guide

How to work in this codebase, what the adapter pattern means in practice,
and how to add new features without breaking anything.

## The one mental model

Every service has the same layered structure:

```
app/
├── domain/       # pure entities, value objects, errors (no framework)
├── ports/        # Protocol interfaces — what the service needs
├── adapters/     # concrete implementations of ports
│                 # + factory.py that selects memory vs production
├── services/     # use cases — pure business logic, takes ports as deps
└── api/          # FastAPI routes, dependency wiring, HTTP layer
```

**Business logic lives in `services/`**. It never imports from `api/` or
`adapters/`. It only imports from `domain/` and `ports/`. That's what
makes it testable without FastAPI and swappable between memory and
production adapters.

## Adapter modes

Every service reads one env var at startup:

```
ADAPTER_MODE=memory     # default — in-memory adapters, no external deps
ADAPTER_MODE=production # real Firestore / KMS / PropelAuth / BigQuery
```

The selection happens in `app/adapters/factory.py`. Tests never set
`ADAPTER_MODE` — they use `app.dependency_overrides` to inject in-memory
adapters directly. Production adapters **lazy-import** their GCP
libraries so the test environment never needs them installed.

### What swap looks like

```python
# app/adapters/factory.py
def make_member_repository() -> MemberRepository:
    if _mode() == "production":
        from app.adapters.firestore_member_repository import FirestoreMemberRepository
        return FirestoreMemberRepository()
    from app.adapters.in_memory_member_repository import InMemoryMemberRepository
    return InMemoryMemberRepository()
```

That's the entire pattern. Every new external dependency follows it.

## TDD workflow

Every new use case follows this loop:

1. **Write the failing test.** Put it in `tests/test_<use_case>.py`,
   using fresh in-memory adapters. Assert the exact behavior you want.
2. **Run pytest.** It should fail with a clear reason.
3. **Add the minimum code** in `services/` or `domain/` to pass.
4. **Run pytest again.** Green.
5. **Refactor.** Tests stay green.

Do NOT write the implementation first. The test is the spec.

## Adding a new endpoint

Example: add `PATCH /members/{id}/activate` to membership-service.

1. **Write the service-level test** in `tests/test_membership_service.py`:
   ```python
   def test_activate_sets_status_and_emits_audit(service, audit):
       m = service.create(_actor(Role.ADMIN), _payload())
       out = service.activate(_actor(Role.ADMIN), m.member_id)
       assert out.status is MemberStatus.ACTIVE
       assert any(e.action == "member.activate" for e in audit.events_for("c1"))
   ```
2. **Write the API test** in `tests/test_api_members.py`:
   ```python
   def test_activate_endpoint(client):
       mid = client.post("/members", ...).json()["member_id"]
       r = client.patch(f"/members/{mid}/activate", headers=_headers("admin"))
       assert r.status_code == 200
       assert r.json()["status"] == "active"
   ```
3. **Run pytest.** Both fail.
4. **Implement:** add `activate()` in `services/membership_service.py` and
   the route handler in `api/routes_members.py`.
5. **Run pytest.** Green.
6. **Commit.** One commit per feature, with the tests in the same commit.

## Adding a new port (new external dependency)

Example: add a `NotificationPort` that sends Slack messages.

1. **Define the port** in `app/ports/notification.py`:
   ```python
   from typing import Protocol

   class NotificationPort(Protocol):
       def notify(self, channel: str, message: str) -> None: ...
   ```
2. **Add an in-memory adapter** in `app/adapters/in_memory_notification.py`
   that records calls in a list. Tests use this.
3. **Add a production adapter** in `app/adapters/slack_notification.py`
   that lazy-imports a Slack SDK. Never import the SDK at module top —
   always inside the method that uses it.
4. **Wire the port into the factory** in `app/adapters/factory.py`:
   ```python
   def make_notification() -> NotificationPort:
       if _mode() == "production":
           from app.adapters.slack_notification import SlackNotification
           return SlackNotification(webhook=_require_env("SLACK_WEBHOOK"))
       from app.adapters.in_memory_notification import InMemoryNotification
       return InMemoryNotification()
   ```
5. **Add a lazy singleton** in `app/api/deps.py`:
   ```python
   _NOTIFICATION: NotificationPort | None = None
   def get_notification() -> NotificationPort:
       global _NOTIFICATION
       if _NOTIFICATION is None:
           _NOTIFICATION = make_notification()
       return _NOTIFICATION
   ```
6. **Add a factory test** in `tests/test_factory.py`:
   ```python
   def test_default_notification_is_in_memory():
       assert isinstance(make_notification(), InMemoryNotification)
   def test_production_notification_requires_webhook(monkeypatch):
       monkeypatch.setenv("ADAPTER_MODE", "production")
       with pytest.raises(RuntimeError, match="SLACK_WEBHOOK"):
           make_notification()
   ```
7. **Update the Dockerfile** if the production adapter needs a system
   package (usually not — most Python deps are pip-only).

Never add `from slack_sdk import ...` at module top-level in an adapter.
Lazy-import inside the method. This keeps the test environment clean.

## Adding a new service

The template is "clone membership-service and rename everything":

```bash
cp -r services/membership-service services/new-service
cd services/new-service
# Rename the domain model, routes, tests to match
# Remove anything you don't need (e.g. encryption if it's YELLOW zone)
# Update requirements.txt
# Update Dockerfile if needed
pytest -q  # should still pass with renamed tests
```

Then add the service to:

1. `infra/terraform/main.tf` — add to `locals.services` list
2. `infra/terraform/iam_bindings.tf` — add per-service bindings
3. `.github/workflows/ci.yml` — add to the `matrix.service` list
4. `.github/workflows/deploy.yml` — add a `build` matrix entry and a
   `deploy-<name>` job
5. `.github/workflows/e2e.yml` — add to the healthz list
6. `kyrk-projekt/README.md` — add a row to the services table

And open a PR with the security review template filled in.

## Running one service's tests

From `kyrk-projekt/`:

```bash
cd services/membership-service
pytest -q                                       # all tests
pytest -q tests/test_membership_service.py      # one file
pytest -q tests/test_membership_service.py::test_admin_can_create_member  # one test
pytest -q -k "cross_church"                     # by keyword
pytest -q --tb=short                            # shorter failure traces
```

## The RED / YELLOW / GREEN rule (day-to-day)

- **Does your code touch identity data?** It lives in `membership-*`,
  `certificate-*`, or `admin-web` only. Never in activity/reporting.
- **Are you aggregating numbers?** Goes in `activity-service` or
  `reporting-service`. Nothing else.
- **Are you generating content / prompts / public HTML?** Goes in
  `automation/openclaw`, `frontend/wifi-intake-portal`, or `docs/`.

When in doubt, check if `reporting-service`'s `pii_guard` would accept
your payload. If it would reject it, it's RED and belongs elsewhere.

## Running the admin-web screenshot harness

A small Playwright script in `scripts/` (if you add one) can take
screenshots of the admin UI for PRs. The pattern:

1. Start `admin-web` with seeded `FakeIntakeClient` / `FakeCertificateClient`
2. Open `/login`, fill the form, submit
3. Walk the happy path
4. Screenshot each step

See the git log for `feat(admin-web)` commits that used this pattern
during development.

## Common pitfalls

### "Why did my test fail with 401?"
You forgot to pass the `Authorization: Bearer user:church:role` header.
All RED-zone endpoints require it.

### "Why does my test see empty data across runs?"
Each test creates a fresh in-memory repo via the fixture. That's
intentional. If you need shared state, scope a fixture to the module.

### "Why can't I import google.cloud.firestore?"
You shouldn't need to, locally. The production adapter imports it
lazily. If tests are trying to hit it, something is misconfigured —
check that `dependency_overrides` is setting a fake adapter.

### "Why is the rate limiter firing in tests?"
The default rate limiter is 3 hits per 60 seconds in the test fixture.
Your test is probably running many requests in a loop. Override the
fixture with a higher limit or reset the limiter between assertions.

### "Why does my Firestore query return nothing in production?"
Check your query uses `church_id` in the filter. The Firestore
adapters use `{church_id}__{id}` doc ids — forgetting to scope by
church_id gives you nothing.

## Style

- **Names are concrete.** `create_member` not `do_member_action`.
- **Errors are typed.** Raise `MemberNotFound`, not `Exception("not found")`.
- **No print statements.** Use `sys.stderr.write` in adapters for
  startup errors, nothing else — logs are structured via the FastAPI
  / uvicorn stack in production.
- **Comments explain WHY, not WHAT.** If the code is self-evident,
  don't comment it. If there's a constraint that's not obvious, leave
  a one-line note.
- **No TODO comments without a tracking issue.** `# TODO: this is
  slow` is useless. `# TODO(#123): use batch reads when > 100 items`
  is useful.

## What to read next

- [`12-operations.md`](12-operations.md) — deploying, rolling back, and
  diagnosing incidents
- [`05-security-principles.md`](05-security-principles.md) — the
  security rules every change must follow
- [`governance/security-review-template.md`](governance/security-review-template.md)
  — the checklist you run before merging any RED-zone PR
