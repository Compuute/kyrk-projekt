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
# memory mode (default)
uvicorn app.main:app --reload
# production mode
ADAPTER_MODE=production \
KMS_KEY_NAME=projects/<p>/locations/europe-north1/keyRings/kyrk/cryptoKeys/member-pn \
PROPELAUTH_URL=https://auth.<tenant>.propelauthtest.com \
PROPELAUTH_API_KEY=$(gcloud secrets versions access latest --secret=propelauth-api-key) \
uvicorn app.main:app --port 8080
```

## Tests

TDD-first. Run `pytest -q`. All tests use in-memory adapters and a fake
PropelAuth client — no network calls. Factory-selection logic is tested
in `tests/test_factory.py` using monkeypatched env vars; the production
adapters are never instantiated against real GCP services in tests.

## Adapter modes

The service reads `ADAPTER_MODE` at startup (see `app/adapters/factory.py`):

| Mode | Repository | Auth | Encryption | Audit |
|---|---|---|---|---|
| `memory` (default) | `InMemoryMemberRepository` | `FakeAuthAdapter` | `InMemoryEncryptionAdapter` | `InMemoryAuditAdapter` |
| `production` | `FirestoreMemberRepository` | `PropelAuthAdapter` | `KmsEncryptionAdapter` | `FirestoreAuditAdapter` |

Production adapters lazy-import `google-cloud-firestore`,
`google-cloud-kms`, and `propelauth-fastapi` so the test environment
does not need them installed.

## Least privilege (production IAM)

Each adapter requires **only** the minimum role for its scope. Grant
these to the `sa-membership-service` service account:

| Resource | Role | Why |
|---|---|---|
| Firestore database | `roles/datastore.user` | read/write `members` + write `audit_events` (security rules enforce per-collection scoping) |
| Cloud KMS key `member-pn` | `roles/cloudkms.cryptoKeyEncrypterDecrypter` | encrypt/decrypt `personal_number` only — no key admin, no list, no destroy |
| Secret `propelauth-api-key` | `roles/secretmanager.secretAccessor` (on that one secret) | load at startup — not the whole Secret Manager |

Do **not** grant `roles/editor`, `roles/owner`, or `roles/datastore.owner`.
If the service cannot perform an action with the above, the right answer
is usually that it should not perform that action at all.

## Security

- No public search endpoint.
- `personal_number` is encrypted at rest (field-level via KMS in production).
- All writes emit an audit event: `{actor, church_id, action, target_id, at}`.
- The service is **write-only on its own audit log** — reading the audit
  log is a separate tool with its own service account.
- `PropelAuthAdapter` reads only `user_id`, `org_id`, and `role` from the
  validated token. Profile, email, and other claims are deliberately
  ignored — if the service doesn't use a field, it should not load it.
- Unauthorized → 401, insufficient role → 403, not found → 404 (cross-church
  reads are hidden as 404, not 403 — no existence disclosure).

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
