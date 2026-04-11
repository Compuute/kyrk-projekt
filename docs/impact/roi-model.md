# ROI model

## Inputs (YELLOW zone only)

- Activity count per month per type
- Participants total per activity
- Age-band breakdown per activity
- Grant funding received per funding_tag
- Operating cost per funding_tag

## Metrics

| Metric | Formula |
|---|---|
| Cost per participant | cost / sum(participants_total) |
| Grant leverage ratio | grant_amount / own_contribution |
| Participant reach per krona | sum(participants_total) / operating_cost |
| Youth reach share | participants in 0-17 bands / total participants |
| Activity continuity | months_with_activity / period_months |

## Reporting cadence

- Monthly: activity counts, participants, cost per participant
- Quarterly: variance vs plan, grant leverage, ROI commentary (OpenClaw)
- Annual: full impact narrative + next-year plan (OpenClaw)

## Grant alignment

- Arvsfonden — youth, community, innovation projects
- Allmänna Arvsfonden — vulnerable groups, development projects
- Kommunala bidrag — local civic integration

Each activity declares a `funding_tag` that maps to its grant program.
Reports aggregate per `funding_tag` for board and grant-body exports.
