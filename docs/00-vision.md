# 00 — Vision

## Mission

Give Swedish churches a modern, secure, mobile-first digital foundation that
respects members' integrity, reduces admin workload, and produces credible
impact evidence for grants and boards.

## Target users

- Pastors, secretaries, board members
- New and existing members
- Youth and community participants
- Grant bodies and auditors (indirect, via reports)

## Product pillars

1. **Intake that respects people.** Mobile-first, QR-friendly, minimal data.
2. **Certificates that prove without leaking.** Digital, verifiable, privacy-preserving.
3. **Evidence that funds itself.** Aggregated KPI/ROI reporting aligned with Swedish grants.
4. **AI that serves, not surveils.** OpenClaw templates reviewed by humans before use.
5. **Sovereignty by design.** GCP in EU, no third-country data flows, no dark patterns.

## What we are NOT building

- A replacement for Kyrkans Bokföring or Fortnox
- A public member search
- Any AI that touches identity data
- A custom auth system (we use PropelAuth)
- A custom workflow engine (we use n8n)

## Success criteria for MVP

- A new member can register in under 60 seconds on a phone
- A pastor can issue a baptism certificate in under 2 minutes
- A board can generate a quarterly KPI report without manual spreadsheets
- No personal data ever reaches the LLM
- All AI outputs are reviewed by an admin before use
