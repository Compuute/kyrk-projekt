# n8n automation

Self-hosted n8n (on Cloud Run) orchestrates all cross-service workflows:
notifications, monthly KPI exports, quarterly OpenClaw analyses, Fortnox
aggregate pulls, Wi-Fi portal content updates.

## Workflow catalogue

| File | Trigger | Source zone | Destination zone |
|---|---|---|---|
| `workflows/new_pending_membership_notification.json` | webhook (from membership-intake) | RED | RED admin |
| `workflows/monthly_kpi_export.json` | cron (1st of month) | YELLOW | YELLOW storage |
| `workflows/quarterly_openclaw_analysis.json` | cron (quarterly) | YELLOW | GREEN (sanitized) |
| `workflows/fortnox_aggregate_reporting.json` | cron (monthly) | YELLOW (external) | YELLOW |
| `workflows/wifi_portal_content_update.json` | cron (weekly) or manual | GREEN | GREEN (Cloud Storage) |

## Sanitizer

Every workflow that touches data declares a `sanitizerProfile` in its
workflow JSON. The sanitizer rules live at `../openclaw/sanitizer/`. The
sanitizer runs as a Function node before any HTTP call to the Anthropic
API. See `../openclaw/sanitizer/rules.md` for details.

## Deployment

See [`DEPLOY.md`](DEPLOY.md).

## Secrets

All secrets are referenced by name only (never inlined). The real values
live in GCP Secret Manager and are injected into n8n as environment
variables at Cloud Run start.

Required secret names:
- `PROPELAUTH_API_KEY`
- `ANTHROPIC_API_KEY`
- `FORTNOX_CLIENT_ID`, `FORTNOX_CLIENT_SECRET`
- `REPORTING_SERVICE_TOKEN` (service-account token)
- `ADMIN_NOTIFY_WEBHOOK` (Slack/email relay URL)
