# Impact Module Blueprint

A reusable skeleton for defining church activity modules in a way that is
directly compatible with `activity-service`, `reporting-service`, and grant
applications.

Every module spec in this folder (`youth-tech.md`, `coding-basics.md`,
`leadership-debate.md`, etc.) MUST use this skeleton. Fill every field.
If a field does not apply, write "N/A — rationale".

---

## 1. Purpose

One paragraph. Why does this module exist? What gap does it fill in the
community? Keep it plain and concrete.

## 2. Target group

- **Age band(s)** (match the activity-service enum): `0-6`, `7-12`,
  `13-17`, `18-25`, `26+`
- **Participant profile**: who is this for?
- **Barrier considerations**: language, cost, transportation, digital access.

## 3. Activity patterns

- **Frequency**: e.g. weekly, biweekly
- **Duration**: minutes per session
- **Format**: workshop, drop-in, cohort, one-off event
- **Facilitators required**: number + any specific skills
- **Equipment / space**: what is needed

## 4. KPI fields

Must match the `activity-service` entity exactly so reports are consistent:

| Field | Source |
|---|---|
| `activity_type` | enum value (e.g. `youth_tech`) |
| `date` | date of each session |
| `location` | address string |
| `funding_tag` | grant program tag (e.g. `arvsfonden`) |
| `participants_total` | headcount (aggregated) |
| `age_band_counts` | `{0-6, 7-12, 13-17, 18-25, 26+}` → int |

## 5. ROI drivers

- **Cost per participant**: target range
- **Grant leverage ratio**: target range
- **Continuity**: how many months per year this runs
- **Multiplier effects**: cross-module benefits (e.g. Youth Tech feeding
  leadership cohort)

## 6. Grant relevance

- **Primary grant programs**:
  - Arvsfonden — criteria matched
  - Allmänna Arvsfonden — criteria matched
  - Kommunala bidrag — criteria matched
- **Evidence required**: aggregate counts, age bands, funding_tag alignment

## 7. Yearly reusability plan

- **Annual cadence**: how the module evolves year to year
- **What to track**: new metrics as the module matures
- **Retirement criteria**: signals that tell you to sunset the module

---

## Filling in activity-service mapping

Every module binds to the `activity-service` enum and the fixed age bands.
If a new activity type is needed, it must be added to the enum in
`services/activity-service/app/domain/models.py` AND to the export schema
`services/activity-service/schemas/activity-export.json` before the module
is launched.
