# activity-service

YELLOW-zone service. Tracks church activities with **aggregated counts only** —
no participant-level data. Outputs feed `reporting-service` and grant reports.

## Zone

**YELLOW** — aggregates only. This service intentionally cannot store names,
personnummers, emails, or any identifier that links an activity to a person.

## Activity types

`youth_tech`, `coding`, `sunday_school`, `leadership`, `debate`,
`community_hub`, `other`.

## Stored fields

| Field | Type |
|---|---|
| `activity_id` | UUID |
| `church_id` | string |
| `activity_type` | enum |
| `date` | date |
| `location` | string |
| `funding_tag` | string |
| `participants_total` | int |
| `age_band_counts` | `{"0-6", "7-12", "13-17", "18-25", "26+"}` → int |

Age-band counts must sum to `participants_total` (validated).

## Auth

PropelAuth RBAC on write endpoints. Reads are open to `viewer` and above.

## Running

```bash
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## Export shape for reporting-service

See `schemas/activity-export.json` for the JSON schema that `reporting-service`
ingests.
