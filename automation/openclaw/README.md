# OpenClaw

Versioned prompt templates for calling the Anthropic API. **Not a
service** — this folder contains JSON templates, sanitizer rules, and
church-specific overrides. A background worker or local script orchestrates everything.

## Structure

```
openclaw/
├── core/           reusable prompt templates (JSON)
├── church/         church-specific overrides (JSON)
├── sanitizer/      sanitizer profiles + rules
├── import/         data import helpers (loaders, validators)
└── prompt-redlines.md
```

## Production flow

See `../../docs/07-openclaw-production-flow.md`.

1. The orchestrator fetches aggregates from `reporting-service`.
2. The orchestrator runs the sanitizer profile declared by the template.
3. The orchestrator renders the template with `{{data}}` substitution.
4. The orchestrator calls `https://api.anthropic.com/v1/messages` with the template's
   system prompt, user prompt, `response_format: json`, model, and max_tokens.
5. The orchestrator validates the response against `expected_output_schema`.
6. The orchestrator stores the result as pending review in Cloud Storage.
7. An admin reviews and applies or rejects.

## Adding a new prompt

1. Copy an existing template from `core/`.
2. Bump `version` and edit `description`.
3. Declare `sanitizer_profile` from `sanitizer/profiles.json`.
4. Declare `expected_output_schema`.
5. Open a PR. A reviewer verifies the redlines in `prompt-redlines.md`.

## Testing prompts locally

A tiny helper in `import/render.py` substitutes `{{data}}` for a local JSON
file so you can eyeball the rendered prompt without calling the API.
