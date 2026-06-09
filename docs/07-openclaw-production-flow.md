# 07 — OpenClaw Production Flow

OpenClaw is the set of versioned prompt templates the platform uses to call the
Anthropic API. It is NOT a service — it is a folder of JSON templates orchestrated
by background tasks or scheduled scripts.

## End-to-end flow

```
┌────────────┐   ┌──────────────────┐   ┌───────────┐   ┌────────────────┐   ┌──────────────┐   ┌─────────────┐
│ Scheduler  │──▶│ reporting-service │──▶│ sanitizer │──▶│ Anthropic API  │──▶│ pending_review│──▶│ admin review │
│ (trigger)  │   │ (YELLOW aggregate)│   │ (profile) │   │ (JSON output)  │   │ storage (GCS) │   │ + apply      │
└────────────┘   └──────────────────┘   └───────────┘   └────────────────┘   └──────────────┘   └─────────────┘
```

## Steps

1. **Trigger.** Scheduler fires a cron or trigger (e.g. quarterly on the 1st).
2. **Fetch aggregates.** The orchestrator calls `reporting-service` for the declared period and report type.
3. **Validate.** The orchestrator applies the sanitizer profile declared on the OpenClaw template. Any field outside the whitelist aborts the run.
4. **Render prompt.** The template's `user_prompt_template` is rendered with `{{data}}` substitution.
5. **Call Anthropic.** The orchestrator calls the Anthropic API with `response_format: json`, the template's model, max_tokens, and system prompt.
6. **Parse + validate.** The response is validated against `expected_output_schema`. Invalid JSON aborts the run.
7. **Store as pending.** The result is written to `gs://<bucket>/openclaw-pending/<run_id>.json`.
8. **Notify.** An admin notification is posted (email or Slack webhook).
9. **Human review.** An admin opens the pending file, reviews, and either approves or rejects.
10. **Apply.** Approval triggers the downstream action (e.g. update Wi-Fi portal content, draft a board report). Rejection archives the run.

## Guarantees

- The Anthropic API never sees RED data — the sanitizer enforces this.
- No AI output modifies member data directly.
- Every run has a `run_id`, a sanitizer profile hash, a template version, and a reviewer.
- Prompts are versioned in git; rollbacks are a git revert.

## Folder layout

```
automation/
└── openclaw/
    ├── core/                   (reusable prompt templates)
    ├── church/                 (church-specific overrides)
    ├── sanitizer/              (profiles.json, rules.md)
    └── import/                 (data import helpers)
```

## Adding a new prompt

1. Copy an existing template from `automation/openclaw/core/`.
2. Bump `version` and update `description`.
3. Declare `sanitizer_profile`.
4. Declare `expected_output_schema`.
5. Commit. A PR review is required before the runner pipeline is wired up.
