# n8n deployment notes

## Hosting

- Cloud Run service `n8n-automation` in `europe-north1`.
- Min instances: 1 (cron reliability); max: 2.
- Dedicated service account `n8n-automation@<project>.iam.gserviceaccount.com`.
- Backing store: Cloud SQL Postgres (smallest tier) or Firestore via custom adapter.

## Environment variables

```
N8N_HOST=<cloud-run-url>
N8N_PROTOCOL=https
N8N_ENCRYPTION_KEY=<from secret manager>
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=<cloud-sql-host>
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=<secret>
```

## Secrets (Secret Manager)

Each secret is exposed to the Cloud Run service as an env var via
`--set-secrets`. Grant the n8n service account `roles/secretmanager.secretAccessor`
scoped to the specific secret — nothing wider.

```
PROPELAUTH_API_KEY=projects/<p>/secrets/propelauth-api-key:latest
ANTHROPIC_API_KEY=projects/<p>/secrets/anthropic-api-key:latest
FORTNOX_CLIENT_ID=projects/<p>/secrets/fortnox-client-id:latest
FORTNOX_CLIENT_SECRET=projects/<p>/secrets/fortnox-client-secret:latest
REPORTING_SERVICE_TOKEN=projects/<p>/secrets/reporting-service-token:latest
ADMIN_NOTIFY_WEBHOOK=projects/<p>/secrets/admin-notify-webhook:latest
```

## Importing workflows

Each JSON file in `workflows/` can be imported via the n8n UI or API.
Workflow versions are tracked in git — the n8n instance is treated as
a deploy target, not the source of truth.

## Security

- n8n UI access is restricted to admin emails via PropelAuth in front of
  Cloud Run (IAP or PropelAuth-protected reverse proxy).
- The sanitizer Function node is included at the top of every OpenClaw-
  adjacent workflow. Do not bypass it.
- No workflow stores secrets in node parameters. All secrets come from
  environment variables.
