# Sanitizer rules

## Goal

Make it impossible, in the normal n8n flow, for identity data to reach the
Anthropic API or any GREEN destination.

## How a profile is applied

1. The n8n workflow declares `sanitizerProfile: <name>` in its workflow JSON.
2. A Function node loads `profiles.json`, picks the profile, and runs it
   against the payload.
3. The sanitizer walks the payload recursively. Each key and string value is
   checked:
   - The key must be in `allowed_fields` OR the sanitizer is configured in
     "whitelist" mode (strict — default).
   - No key may match any `blocked_patterns` regex.
   - No string value may contain a personnummer-like pattern
     (`\d{6,8}[-\s]?\d{4}`).
   - Total payload size must be under `max_payload_size_bytes`.
4. On any violation: the profile's `rejection_action` is applied. `fail`
   aborts the workflow and raises an alert.

## Why whitelist over blacklist

Blacklists drift. If a new field is added upstream with PII, a blacklist
silently lets it through. A whitelist fails closed — new fields must be
explicitly allowed.

## Testing a profile

Run the local helper `../import/sanitize.py` against an example payload:

```bash
python3 ../import/sanitize.py yellow-only ../../services/reporting-service/examples/board-export-example.json
```

The helper exits non-zero if the payload would be rejected.

## Defense in depth

The n8n sanitizer is the first line. `reporting-service` also rejects any
PII at ingress (`app/domain/pii_guard.py`), so even if a workflow mis-points
at a raw source, the service itself will refuse to return the data.
