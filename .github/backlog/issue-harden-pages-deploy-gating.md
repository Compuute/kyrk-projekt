# Issue: Härda deploy-gating för Pages när repot får betald GitHub-plan

> **Status (2026-06-11):** Backlog — medvetet uppskjutet under utvecklingsfasen.
> Aktiveras när projektet går mot betalversion/skarp drift.

## Kategori
- [x] Säkerhet / Process (deploy-styrning)
- [x] Infrastruktur / CI
- [ ] Felrättning (Bug)

## Beskrivning

Pages-projektet `kyrka-portal` återskapades 2026-06-11 med git-koppling till
`Compuute/kyrk-projekt` (det gamla projektet pekade på fel repo, `Compuute/.github`,
och Cloudflare tillåter inte repo-byte på befintliga projekt). Nuvarande läge:
**varje push till `main` bygger och deployar produktion automatiskt**, utan
manuellt godkännandesteg.

Det avviker från repo-regeln om manuellt ägargodkännande för produktionsdeploy.
Beslut 2026-06-11: accepterat under utvecklingsfasen; härdas vid betalversion.
GitHubs deployment protection rules (required reviewers m.m.) är inte
tillgängliga för privata repon på Free-planen, vilket även begränsar
alternativet att gå via GitHub Actions med miljö-gate (utreddes i PR #17,
stängd till förmån för git-integrationen).

## Arbetsmoment (vid betalversion/skarp drift)

1. **Branch protection på `main`** — required PR review innan merge gör att
   inget når produktion utan ägarens granskning (fungerar även på Free-planen
   för publika repon; kräver betald plan för privata).
2. Alternativt/kompletterande: stäng av automatiska produktionsdeploys i
   Pages-projektet (`production_deployments_enabled: false`) och deploya via
   GitHub Actions med `environment: prod` + required reviewers (kräver betald
   plan) — se stängda PR #17 för färdigt workflow-utkast.
3. **Branch-restriktion på GitHub-miljön `prod`** — endast `main`.
4. Överväg samma härdning för `deploy.yml` (GCP-tjänsterna), som är
   `workflow_dispatch`-only av samma skäl.

## Referenser
- PR #17 (stängd — Actions-deploy-utkast med miljö-gate)
- Cloudflare Pages-projektet `kyrka-portal` (git-kopplat till detta repo, produktionsbranch `main`)
