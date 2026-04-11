# membership-service

RED-zone service. Owns member lifecycle: create (from approved intake), read,
update, deactivate. Enforces PropelAuth RBAC and emits audit events on every
write.

## Zone

**RED** — sensitive identity data, field-level encrypted.

## Responsibilities

- Member CRUD (no public search)
- RBAC via PropelAuth (admin / pastor / secretary / viewer)
- Field-level encryption for `personal_number`
- Audit trail of admin actions
- BankID integration interface (stub for MVP, real impl in Phase 2)

## Architecture

Clean architecture with explicit ports/adapters:

```
app/
├── main.py               FastAPI app factory
├── domain/               entities, value objects, errors
├── ports/                interfaces (Protocols)
├── adapters/             in-memory implementations for MVP + tests
├── services/             use cases
└── api/                  HTTP layer + dependency wiring
```

## Running

```bash
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## Tests

TDD-first. Run `pytest -q`. All tests use in-memory adapters and a fake
PropelAuth client — no network calls.

## Endpoints (MVP)

| Method | Path | Role |
|---|---|---|
| POST | `/members` | admin, pastor, secretary |
| GET | `/members/{member_id}` | admin, pastor, secretary |
| PATCH | `/members/{member_id}` | admin, pastor, secretary |
| POST | `/members/{member_id}/deactivate` | admin, pastor |

Every response is scoped to the caller's `church_id`. Cross-church reads
return 404.

## Security

- No public search endpoint.
- `personal_number` is encrypted at rest (field-level).
- All writes emit an audit event: `{actor, church_id, action, target_id, at}`.
- Unauthorized → 401, insufficient role → 403, not found → 404.
