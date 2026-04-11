# Security review template

Use this checklist for every PR that touches a RED service, the sanitizer,
n8n workflows, OpenClaw templates, or Terraform IAM.

## Scope

- Service(s) touched:
- Zone(s) affected:
- New external dependencies:

## Data flow

- [ ] No RED data flows to YELLOW without explicit aggregation
- [ ] No YELLOW data flows to GREEN/LLM without sanitizer validation
- [ ] No GREEN output writes back to RED automatically

## Auth

- [ ] All new endpoints are protected by PropelAuth
- [ ] Role checks use shared FastAPI dependency
- [ ] No hard-coded secrets or tokens

## Input validation

- [ ] All new endpoints use Pydantic models
- [ ] All string fields have max_length
- [ ] All enum fields use Python `Enum`

## Audit

- [ ] Writes on RED data emit audit events
- [ ] Audit events include actor, church_id, action, target_id

## Tests

- [ ] Unauthorized access returns 401
- [ ] Insufficient role returns 403
- [ ] Malformed input returns 422
- [ ] Happy-path test exists
- [ ] Negative test for every new validation rule

## Secrets and IAM

- [ ] New secrets added to Secret Manager, not code
- [ ] New IAM grants are least-privilege and scoped to one service account
- [ ] No wildcards in IAM roles

## Reviewer notes
