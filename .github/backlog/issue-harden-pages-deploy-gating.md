# Issue: Härda deploy-gating för Pages när repot får betald GitHub-plan

> **Status (2026-06-11):** Backlog — medvetet uppskjutet under utvecklingsfasen.
> Aktiveras när projektet går mot betalversion/skarp drift.

## Kategori
- [x] Säkerhet / Process (deploy-styrning)
- [x] Infrastruktur / CI
- [ ] Felrättning (Bug)

## Beskrivning

Produktionsdeploy av medlemsportalen sker via `.github/workflows/pages-deploy.yml`
(manuell `workflow_dispatch`, infört i PR #17 efter att Pages git-integration
kopplades bort — den pekade på fel repo och kunde inte pekas om). Det manuella
"Run workflow"-klicket är idag ägarens godkännande, kompletterat med en guard i
workflowet som vägrar köra från andra refs än `main`.

GitHubs **deployment protection rules** (required reviewers, wait timer) är inte
tillgängliga för privata repon på Free-planen, så miljön `prod` saknar
plattformsnivå-gating. Beslut 2026-06-11: vi kör utan detta under utveckling och
hårdnar när projektet får betald plan.

## Arbetsmoment (när betald plan finns)

1. **Required reviewers på `prod`-miljön** — Settings → Environments → prod →
   Deployment protection rules → Required reviewers → lägg till ägaren.
   Då kan workflow-triggern bytas till `push: branches: [main]` med bibehållet
   manuellt godkännande (deployjobbet pausar tills reviewern godkänner).
2. **Branch-restriktion på miljön** — Deployment branches and tags: endast `main`
   (ersätter/kompletterar guard-steget i workflowet).
3. Överväg samma härdning för `deploy.yml` (GCP-tjänsterna), som är
   `workflow_dispatch`-only av samma skäl.

## Referenser
- PR #17 (workflow + bakgrund till bortkopplad git-integration)
- `.github/workflows/pages-deploy.yml`
