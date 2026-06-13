# RBAC

Roles are modeled via Zitadel, scoped per `church_id` (Zitadel organization).

| Role | RED read | RED write | Certificate issue | YELLOW read | Approve AI output |
|---|---|---|---|---|---|
| `admin` | yes | yes | yes | yes | yes |
| `pastor` | yes | yes | yes | yes | no |
| `editor` | yes | intake / update only | no | yes | no |
| `viewer` | no | no | no | yes | no |

## Principles

- Roles are per-church. A user may have different roles in different churches.
- Write actions on RED data emit audit events tagged with actor + role.
- Role checks happen in FastAPI dependencies, not in ad-hoc code.
- New roles require a doc update and PR review before rollout.
