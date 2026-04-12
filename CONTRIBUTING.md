# Contributing to kyrk-projekt

This is a nonprofit church platform handling sensitive identity data.
Every change lands under the rules in
[`docs/05-security-principles.md`](docs/05-security-principles.md) and
[`docs/governance/security-review-template.md`](docs/governance/security-review-template.md).
Read those before your first PR.

## Before you start

1. **Read the docs in this order:**
   - [`docs/10-getting-started.md`](docs/10-getting-started.md) — 15 min
     setup, git clone → green tests.
   - [`docs/01-architecture-red-yellow-green.md`](docs/01-architecture-red-yellow-green.md)
     — the zone model everything else is built on.
   - [`docs/11-development-guide.md`](docs/11-development-guide.md) —
     adapter pattern, TDD loop, how to add a new endpoint/service.
   - [`docs/05-security-principles.md`](docs/05-security-principles.md)
     — non-negotiables.

2. **Run the tests locally** with `make test`. You should see
   **158 passed** across all six services plus the wifi portal.
   If anything is red on `main`, open an issue — do not paper over it.

3. **Run local CI before pushing** with `./scripts/local-ci.sh`.
   This mirrors what GitHub Actions does in `ci.yml`: pytest matrix,
   node tests, compileall, terraform validate, Dockerfile static check,
   and workflow YAML lint. If `local-ci.sh` is green, GitHub will be too.

## The contribution loop

### 1. Branch

```bash
git checkout -b feat/<short-description>
# or fix/, docs/, chore/, refactor/ — follow conventional-ish style
```

Never commit directly to `main`. Even trivial typo fixes go through
CI.

### 2. Write the test first

TDD is non-negotiable for anything in `services/`, `app/domain/`, or
`app/services/`. The test is the spec — write it, make it fail, then
implement.

```bash
cd services/<service>
pytest -q tests/test_<file>.py::<test_name>   # runs a single failing test
```

If you're changing something you can't test cheaply (templates, HTML,
CSS), add a test for the *server-side data flow* that the template
consumes.

### 3. Implement

Follow the adapter pattern described in
[`docs/11-development-guide.md`](docs/11-development-guide.md):

- Business logic lives in `app/services/`. It never imports from
  `app/api/` or `app/adapters/`.
- External dependencies go behind a `Protocol` in `app/ports/`.
- Production adapters **lazy-import** their libraries — never put
  `from google.cloud import firestore` at module top-level.
- The factory in `app/adapters/factory.py` reads `ADAPTER_MODE`
  and returns memory or production.

### 4. Verify locally

```bash
# From kyrk-projekt/
./scripts/local-ci.sh

# Or using make:
make test        # just pytest + node
make lint        # compileall + terraform fmt
```

Every check must be green before you open a PR.

### 5. Commit

One logical change per commit. Use imperative mood in the subject line:

```
feat(membership-service): add activate endpoint
fix(reporting-service): reject FirstName in pii_guard
docs: add runbook for unauthorized RED access
chore(deps): bump propelauth-fastapi to 4.1
```

Allowed prefixes: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`,
`build`, `ci`, `perf`, `style`.

Scope in parentheses is optional but helps for large services.

Commit message body should explain **why** the change is needed, not
rephrase the diff. If the PR has a clear body, a one-line subject is
fine.

### 6. Push and open a PR

```bash
git push -u origin feat/<short-description>
gh pr create
```

The PR template asks you to fill in:

- **Summary** — 1–3 bullets on what changed and why.
- **Zone(s) touched** — RED / YELLOW / GREEN / Infra / Docs.
- **Checklist** — TDD, Pydantic models, PropelAuth, audit events,
  no secrets, docs updated.
- **How to test** — exact commands a reviewer can run.
- **Related** — issue, thread, or doc.

## PR review requirements

| Change touches | Minimum review |
|---|---|
| Docs only | 1 reviewer |
| Tests only | 1 reviewer |
| YELLOW-zone service | 1 reviewer + green CI |
| GREEN-zone (portal, OpenClaw, n8n) | 1 reviewer + green CI + read `docs/04-ai-boundaries.md` |
| RED-zone service | **2 reviewers**, one must be an admin + completed [security review template](docs/governance/security-review-template.md) |
| Sanitizer profile or pii_guard | **2 reviewers** + completed security review template |
| IAM bindings (Terraform or GCP) | **2 reviewers** + Terraform plan attached to PR |
| Cloud Run deploy workflow | **2 reviewers** + plan shown before merge |

Required CI checks (from `ci.yml`):

- All 6 service test suites green
- Wifi portal node tests green
- Python compileall
- Terraform fmt + validate

## What not to do

- **Don't push directly to `main`.** Ever. Even for "just a typo".
- **Don't disable tests to make CI green.** If a test is flaky,
  fix the flake or quarantine it with an issue link — never delete
  it silently.
- **Don't add a new external dependency without writing the port
  and factory first.** The test environment must stay lib-free.
- **Don't introduce new endpoint without Pydantic validation.**
- **Don't add identity fields to YELLOW or GREEN code paths.** If
  `pii_guard.FORBIDDEN_FIELDS` would reject your change, it's RED and
  belongs in a RED service.
- **Don't commit secrets.** Secret Manager is the only place.
  Pre-commit hooks don't exist yet — run `git diff --staged` before
  every commit and eyeball it.
- **Don't force-push to a branch someone else is reviewing.** Use
  `git commit --fixup` or add new commits instead.
- **Don't rewrite commit history on `main`.** If you need to revert,
  open a revert PR (see [`docs/13-runbook.md`](docs/13-runbook.md#3-bad-commit-pushed-to-main)).

## What to do

- **Read the existing code** before changing it. Clean architecture
  only works if you respect the layering.
- **Prefer small PRs.** 300 lines beats 3000 for the reviewer.
- **Fill in the PR template.** Empty PR bodies get bounced.
- **Run `make test` and `./scripts/local-ci.sh` before pushing.**
- **Commit the tests in the same commit as the implementation.**
  Not the next one, not "add tests" a week later.
- **Update docs in the same PR as the code.** If your change makes
  something in `docs/` stale, update it.
- **Ask for a second opinion on RED-zone changes.** Even if a single
  reviewer is technically enough, ping another admin for the audit
  trail.

## Reporting security issues

**Do not open a public issue** for security vulnerabilities. Instead:

1. Email the admin team directly (see org `.github/profile/README.md`).
2. Include reproduction steps and the commit SHA you tested against.
3. Give us 90 days to fix before any public disclosure.

Security reports that affect member identity data are triaged with
the same urgency as a PII leak incident (see
[`docs/13-runbook.md#4-suspected-pii-leaked-to-anthropic`](docs/13-runbook.md#4-suspected-pii-leaked-to-anthropic)).

## Code of conduct

Be kind. Assume good faith. Review the code, not the person. We're
building a platform for church communities — that tone should carry
into how we work together.

## Questions?

- **Setup issues** → [`docs/10-getting-started.md`](docs/10-getting-started.md)
  or open a discussion.
- **"How do I…" code questions** → [`docs/11-development-guide.md`](docs/11-development-guide.md).
- **Deploy or incident questions** → [`docs/12-operations.md`](docs/12-operations.md)
  and [`docs/13-runbook.md`](docs/13-runbook.md).
- **Architecture decisions** → open a discussion before opening a PR.
  We'd rather talk for an hour than rewrite for a week.
