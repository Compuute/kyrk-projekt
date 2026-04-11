# reporting-service

YELLOW-zone service. Generates monthly / quarterly / board-ready KPI and ROI
reports from aggregated inputs only.

## Zone

**YELLOW** — strict. On every ingest path the service rejects any payload
containing a forbidden field (`personal_number`, `name`, `first_name`,
`last_name`, `email`, `phone`). Violations return **422**. This is a
defense-in-depth layer behind the n8n sanitizer.

## Endpoints

| Method | Path | Role |
|---|---|---|
| POST | `/reports/monthly` | service account or admin |
| POST | `/reports/quarterly` | service account or admin |
| POST | `/reports/board-export` | service account or admin |
| GET | `/reports/{report_id}` | viewer+ |

All outputs are structured JSON with declared schemas so they can be fed
directly into OpenClaw prompts.

## Running

```bash
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## OpenClaw input schema

`schemas/openclaw-input.json` is the canonical JSON schema for the
board-ready export. OpenClaw templates reference it via `expected_output_schema`.

## BigQuery

A `BigQueryExportPort` interface exists for future push-to-BQ — not wired up
in MVP.

## Example outputs

See `examples/` for sample monthly, quarterly, and OpenClaw inputs.
