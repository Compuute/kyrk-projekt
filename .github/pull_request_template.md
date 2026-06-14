# Pull Request

## Summary

<!-- 1-3 bullets describing the change -->

## Zone(s) touched

- [ ] RED
- [ ] YELLOW
- [ ] GREEN
- [ ] Infra / Terraform
- [ ] Docs only

## Checklist

- [ ] TDD: tests written before / alongside implementation
- [ ] Pydantic models for all new inputs
- [ ] Zitadel dependency on all new RED endpoints
- [ ] No PII in GREEN code paths
- [ ] Audit events for new RED writes
- [ ] No secrets committed
- [ ] Docs updated if behavior changed — ADR in `docs/14`, feature/flow doc in `docs/`, or a `ops/runbooks/*.yaml` so support agents can troubleshoot it
- [ ] Security review template completed for RED/sanitizer/IAM changes

## How to test

<!-- commands, curl snippets, or manual steps -->

## Related

<!-- issues, docs, threads -->
