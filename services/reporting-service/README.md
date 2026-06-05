# reporting-service

YELLOW-zone service. Handles both activity tracking (aggregate participant
counts) and KPI/ROI reporting from aggregated inputs only. Merged from the
former `activity-service` and `reporting-service` -- they protect the same
asset (aggregate data) at the same trust level.

## Zone

**YELLOW** -- strict. On every ingest path the service rejects any payload
containing a forbidden field (`personal_number`, `name`, `first_name`,
`last_name`, `email`, `phone`). Violations return **422**. This is a
defense-in-depth layer behind the n8n sanitizer.

## Defense layers (5 independent)

1. Cloud Run auth (service-to-service identity)
2. PropelAuth RBAC (user-level roles)
3. Pydantic validation (request shape)
4. pii_guard (recursive PII scan on report payloads)
5. Firestore collection separation (`activities` vs `reports`)

## Endpoints

### Activity tracking

| Method | Path | Role |
|---|---|---|
| POST | `/activities` | admin, pastor, secretary |
| GET | `/activities/{id}` | viewer+ |
| GET | `/activities/export/period?start=&end=` | viewer+ |

### KPI / ROI reporting

| Method | Path | Role |
|---|---|---|
| POST | `/reports/monthly` | admin |
| POST | `/reports/quarterly` | admin |
| POST | `/reports/board-export` | admin |
| GET | `/reports/{report_id}` | viewer+ |

All outputs are structured JSON with declared schemas so they can be fed
directly into OpenClaw prompts.

## Running

```bash
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## Schemas

- `schemas/openclaw-input.json` -- canonical JSON schema for the board-ready
  export. OpenClaw templates reference it via `expected_output_schema`.
- `schemas/activity-export.json` -- schema for the activity aggregate export.

## BigQuery

A `BigQueryExportPort` interface exists for push-to-BQ of report data.
The merged service account needs both `datastore.user` and
`bigquery.dataEditor`.

## Example outputs

See `examples/` for sample monthly, quarterly, and OpenClaw inputs.
