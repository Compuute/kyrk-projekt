# 14 — Architecture Decision Records (ADRs)

Each decision below records **what** we chose, **why**, and
**when to revisit**. They're numbered by date, not by importance.

---

## ADR-001: Service-per-zone-boundary (originally six, now five)

**Date:** 2025-06
**Status:** amended by ADR-010 (activity+reporting merge)
**Context:** kyrk-projekt handles three sensitivity levels of data
(RED identity, YELLOW aggregates, GREEN content). A single monolith
would share a single service account, a single DB connection, and a
single deploy pipeline — making least-privilege impossible.
**Decision:** split into services along zone and trust boundaries.
The original prompt specified six; after 33 commits of empirical
data we consolidated to five by merging the two YELLOW services
(see ADR-010). The surviving boundaries are:
- membership-intake (RED, public)
- membership-service (RED, authenticated, KMS)
- certificate-service (RED, authenticated)
- reporting-service (YELLOW, authenticated, BigQuery)
- admin-web (UI, stateless)
**Consequence:** five services instead of six. Each service still has
its own SA, Firestore collections, IAM scope, Dockerfile, and test
suite. The operational overhead is reduced by one deploy job, one SA,
and ~350 lines of infrastructure code.
**When to revisit:** if a future requirement moves activity data into
RED (e.g., participant-level tracking with names), split them back.

---

## ADR-002: Plain HTML admin UI instead of React / SPA

**Date:** 2025-06
**Status:** accepted
**Context:** the admin UI needs to handle intake approval, certificate
issuance, and KPI viewing. These are form → submit → redirect flows
with no real-time interactivity.
**Decision:** server-rendered HTML via Jinja2 templates + plain CSS.
No JavaScript framework, no build pipeline, no CDN scripts. Same
design principle as the wifi-intake-portal.
**Consequence:** zero npm dependencies, zero build step, pages render
in <50 ms, auditable in a browser's "View Source". Downside: no inline
editing, no partial page updates without a full reload.
**When to revisit:** when a screen genuinely needs real-time feedback
(e.g. live participant counter during an event). At that point,
consider HTMX as progressive enhancement first, React only if HTMX
is insufficient.

---

## ADR-003: n8n for orchestration instead of a custom workflow engine

**Date:** 2025-06
**Status:** superseded by ADR-015
**Context:** the platform needs scheduled jobs (monthly KPI, quarterly
OpenClaw analysis, Fortnox sync, wifi portal content updates) and
webhook-triggered flows (new intake notification).
**Decision:** use self-hosted n8n on Cloud Run. Workflows are defined
as JSON and version-controlled in `automation/n8n/workflows/`.
**Consequence:** zero custom orchestration code, visual debugging in
the n8n UI, built-in retry logic. Downside: another Cloud Run service
to maintain (min 1 instance for cron reliability, ~€5-10/month).
**When to revisit:** if n8n's execution model becomes limiting (e.g.
complex fan-out with >100 parallel branches), evaluate Cloud Workflows
or Temporal.

---

## ADR-004: PropelAuth instead of custom auth

**Date:** 2025-06
**Status:** accepted
**Context:** building a secure multi-tenant RBAC system from scratch
takes weeks and introduces a large surface area for security bugs.
**Decision:** use PropelAuth for authentication + RBAC. Each church is
a PropelAuth organization; roles (admin/pastor/secretary/viewer) map to
PropelAuth org roles. Auth is a port — `FakeAuthAdapter` for tests,
`PropelAuthAdapter` for production.
**Consequence:** no session management code, no password hashing, no
token rotation logic. The free tier covers MVP. Downside: dependency
on a third-party SaaS for a critical path.
**When to revisit:** if PropelAuth pricing or availability becomes a
problem, swap the adapter for a self-hosted Keycloak or Auth0 — the
port interface stays the same.

---

## ADR-005: Adapter pattern with ADAPTER_MODE env var

**Date:** 2025-06
**Status:** accepted
**Context:** services need to run locally with no GCP credentials
(memory mode) AND in production with Firestore + KMS + PropelAuth
(production mode).
**Decision:** each service has a `factory.py` that reads `ADAPTER_MODE`
at startup and instantiates the right adapter set. Production adapters
lazy-import their GCP libraries so the test environment never needs
them installed.
**Consequence:** `make test` runs in <5 seconds with zero network
calls, every test uses in-memory adapters. Production swap is a single
env var.
**When to revisit:** if a third mode is needed (e.g. `staging` with
a different Firestore database), extend the factory. The pattern
itself is stable.

---

## ADR-006: Static wifi-intake-portal instead of React

**Date:** 2025-06
**Status:** accepted
**Context:** the Wi-Fi landing portal is shown to guests for ~2 seconds
on a captive portal. It must load instantly, use no cookies, no
tracking, no external scripts.
**Decision:** plain HTML + CSS + 80 lines of vanilla JS. Content
is loaded from a JSON file pushed to Cloud Storage by n8n.
**Consequence:** 7 KB total, renders on any device, passes any
privacy audit. Downside: adding a dynamic feature (e.g. a captive
portal registration form) would need more JS.
**When to revisit:** if the portal needs user-specific content
(e.g. personalized welcome after Wi-Fi login), evaluate whether a
simple form POST is sufficient before reaching for a framework.

---

## ADR-007: Structured JSON output for OpenClaw (no free-form prose)

**Date:** 2025-06
**Status:** accepted
**Context:** OpenClaw prompts call Anthropic API via n8n. Free-form
prose output is hard to validate, harder to audit, and risks leaking
data into unexpected fields.
**Decision:** every prompt template uses `response_format: json` and
declares an `expected_output_schema`. The n8n sanitizer validates the
response against the schema; invalid JSON aborts the run.
**Consequence:** AI outputs are machine-checkable, parseable, and
auditable. Human reviewers see structured data, not walls of text.
Downside: the AI cannot produce narrative reports directly — an admin
must compose narrative from the structured JSON if needed.
**When to revisit:** when the board requests a "narrative quarterly
report" format. At that point, add a second template with free-form
output but keep the structured template as the primary data source.

---

## ADR-008: CMEK for Firestore

**Date:** 2025-06
**Status:** accepted
**Context:** Google encrypts Firestore at rest by default, but with
Google-managed keys the data owner cannot revoke access at the
cryptographic level. In a worst-case scenario (compromised service
account, legal hold, or exit from GCP), the ability to revoke the key
and render all data unreadable is a meaningful addition to the security
posture.
**Decision:** provision a customer-managed Cloud KMS key and configure
Firestore to use it via CMEK. The Firestore service agent gets
`cloudkms.cryptoKeyEncrypterDecrypter` on that key.
**Consequence:** revoking the key makes all collections unreadable
within minutes — a nuclear option for incident response. Day-to-day
access control stays in IAM + security rules. Cost: negligible
(~€0.06/month for one active key version).
**When to revisit:** never — CMEK is strictly additive. The only
downside is a ~5 ms latency increase per operation, which is invisible
at church-scale traffic.

---

## ADR-009: No A/B testing in MVP — phased introduction

**Date:** 2025-06
**Status:** accepted
**Context:** A/B testing frameworks add routing complexity,
observability requirements, and statistical interpretation overhead.
The MVP has <5 churches and no product metrics pipeline.
**Decision:** defer A/B testing entirely until Phase 3. See
[`docs/15-ab-testing-strategy.md`](15-ab-testing-strategy.md) for the
phased introduction plan and the criteria that trigger it.
**Consequence:** simpler deploy, simpler routing, simpler debugging.
Downside: we can't measure the impact of feature changes on user
behavior until the pipeline is in place.
**When to revisit:** see the trigger criteria in `15-ab-testing-strategy.md`.

---

## ADR-010: Merge activity-service into reporting-service

**Date:** 2025-06
**Status:** accepted
**Supersedes:** the implicit 5-service split in the original prompt (B)

**Context:** after building all six services with production adapters,
CI/CD, and operational docs (33 commits of empirical data), we
measured the actual overhead and security properties of each service
boundary. Data showed:

- `activity-service` had 30% infrastructure overhead (243 lines of
  boilerplate out of 798 total) — the highest ratio of any service.
- `propelauth_auth.py` was copy-pasted identically across 5 services
  (261 lines of pure duplication).
- `activity-service` and `reporting-service` are both YELLOW-zone,
  both `--no-allow-unauthenticated`, both PropelAuth-protected, and
  share domain concepts (`activity_type`, `age_band_counts`,
  `participants_total`). Reporting's `GenerateReportInput` takes
  `activities: list[dict]` — it already knows what an activity is.
- The only IAM difference was BigQuery access (reporting had
  `bigquery.dataEditor`, activity did not). This prevented a
  theoretical activity→BigQuery write — but that threat requires a
  code change which would be caught by code review + CI.

We evaluated against the Israeli defense-in-depth principle:
"multiple independent barriers, each sufficient alone." The SA
isolation between two YELLOW services was a barrier that protected
the same asset (aggregate data) against the same threats at the same
trust level. Removing it leaves five independent layers intact. See
[`docs/16-defense-in-depth.md`](16-defense-in-depth.md) for the full
analysis.

**Decision:** merge `activity-service` into `reporting-service`.
The combined service handles activity tracking (create, get, export)
AND report generation (monthly, quarterly, board export). It runs
under one Cloud Run service, one SA, one Dockerfile.

**Consequence:**
- ~350 lines of infrastructure code removed
- 1 fewer deploy job, SA, IAM binding, healthz target
- HTTP hop in admin-web KPI dashboard eliminated (export_period is
  now an internal function call)
- Duplicated PropelAuth + FakeAuth adapters eliminated
- 3 of 8 defense layers changed; 5 of 5 independent layers preserved
- Combined SA has `datastore.user` + `bigquery.dataEditor`
- Activity endpoints still cannot reach BigQuery — no code path
  exists; adding one requires review + CI

**What we kept:**
- Firestore collections remain separate (`activities` vs `reports`)
- `pii_guard` runs on every reporting ingest path
- Activity endpoints validate age-band sums via Pydantic
- PropelAuth RBAC on every endpoint

**When to revisit:** if a future requirement places activity data in
a different zone (e.g., participant-level tracking that becomes RED),
split them back. The port pattern makes this a one-day operation.

---

## ADR-011: Defense-in-depth policy as a permanent document

**Date:** 2025-06
**Status:** accepted
**Context:** the activity+reporting merge decision required a
structured evaluation of which service boundaries earn their keep.
That evaluation should be repeatable for any future merge or split.
**Decision:** create [`docs/16-defense-in-depth.md`](16-defense-in-depth.md)
as the permanent reference for how kyrk-projekt applies defense-in-
depth. It defines the decision matrix (5 yes/no questions), the
non-negotiable RED-zone boundaries, and the evaluation process for
future changes.
**Consequence:** any future service merge or split must reference this
document and answer the five evaluation questions in writing (PR
description or new ADR). No merge across zone boundaries without a
full security review + DPIA update.
**When to revisit:** when new zones or trust levels are introduced
(e.g., a BLUE zone for financial transactions).

---

## ADR-012: Cloudflare Pages + proxy for public-facing sites

**Date:** 2025-06
**Status:** accepted
**Context:** the platform has two static sites (member-portal,
wifi-intake-portal) and four dynamic services. Hosting static sites
on GCS requires 5 GCP resources (bucket + IAM + Cloud CDN + SSL cert
+ load balancer) per site. Each resource needs Terraform, costs money,
and adds an ops surface. Meanwhile, the public intake endpoint needs
DDoS protection, which Cloud Armor charges $5/policy/month for.
**Decision:** host static sites on Cloudflare Pages (free tier, global
edge, auto-SSL, auto-CDN, free DDoS). Route dynamic traffic through
Cloudflare proxy to Cloud Run (free WAF, bot detection, DDoS). All
data stays in GCP (Firestore, KMS, BigQuery in EU regions).
**Consequence:**
- Static deploys: one command (`wrangler pages deploy`) instead of 5
  GCP resources. No Terraform needed for Pages.
- DDoS + WAF: free, automatic, no Cloud Armor cost.
- Resilience: static sites survive a GCP outage (edge-served).
- Ops: one more vendor (Cloudflare) but fewer things to configure.
- Sovereignty: Cloudflare edge caches are EU-restricted on free plan
  for .se domains. All persistent data (Firestore, KMS) stays in GCP
  `europe-north1`. Cloudflare sees only the HTTP request/response, not
  the database contents.
- New failure mode: if Cloudflare goes down, flip DNS to direct Cloud
  Run URLs (5 min manual rollback). Documented in
  [`architecture/cloudflare-edge.md`](architecture/cloudflare-edge.md).
**What we do NOT move to Cloudflare:**
- Backend services (need Python + Firestore + KMS — Cloudflare Workers
  can't run our stack)
- Secrets (stay in GCP Secret Manager with per-secret IAM)
- Encryption keys (stay in GCP KMS with CMEK)
- Database (stays in GCP Firestore with EU multi-region)
**When to revisit:** if Cloudflare changes their free-tier terms, or if
we need to serve dynamic content from edge (evaluate Cloudflare Workers
at that point, but it would require a JS rewrite).

---

## ADR-013: Eleventy (11ty) for member-portal — not React, Astro, or Next.js

**Date:** 2026-06
**Status:** accepted

**Context:**
The public member portal serves church members across ~10 congregations.
The site needs to:
- Load instantly on older Android phones on slow 4G connections
- Work fully offline as a PWA (Progressive Web App) once installed
- Serve static pages from Cloudflare edge in ~10 ms globally
- Support two languages (Swedish + Amharic) without a page reload
- Operate with zero tracking, zero cookies, and zero external scripts
- Be deployable by a single developer with `wrangler pages deploy`
- Remain maintainable by a small team for 5+ years without framework churn

We evaluated the following alternatives before deciding on Eleventy:

**React / Next.js:**
- Adds a JS runtime bundle of 70–200 KB to every page load
- Requires Node.js server or edge functions for SSR, adding ops surface
- Component model is powerful but overkill for mostly-static content pages
- `node_modules` dependency tree is a long-term maintenance liability
- Hydration adds complexity: the HTML shell and client runtime must agree
- Decision: **rejected** — operational and performance cost not justified by the content model

**Astro:**
- Excellent static output, minimal JS by default — closer to what we need
- Ships a full build pipeline (Vite, rollup) with a significant learning curve
- Plugin ecosystem introduces dependency churn risk
- Islands architecture is elegant but adds conceptual overhead for a small team
- Decision: **rejected** — Astro is technically sound but was not yet stable enough at project start (2025-06), and its abstraction layer is unnecessary when our pages are already simple Nunjucks templates

**Vue / SvelteKit:**
- Same class of trade-offs as React/Next.js
- Even smaller teams = higher truck factor risk with niche framework knowledge
- Decision: **rejected** — same reasoning as React

**Plain HTML files (no SSG):**
- Zero build step, zero dependencies — maximally simple
- Immediately ruled out because 15 pages × shared nav/footer/PWA code
  = 1050+ lines of copy-pasted HTML that must be kept in sync manually
- A single layout change (e.g. adding a new nav link) requires editing 15 files
- Decision: **rejected** — violates DRY, maintenance burden unacceptable at scale

**Eleventy (11ty) — chosen:**
- Zero-JS output by default: the framework itself ships no runtime JS to the browser
- Nunjucks templates are readable by any developer who knows HTML
- Shared layout in `src/_includes/base.njk` eliminates all copy-paste: one change propagates to all 15 pages
- Build is a single command (`npx @11ty/eleventy`), outputs pure HTML to `dist/`
- No bundler, no transpiler, no dependency tree — `node_modules` contains only Eleventy itself
- Output is 100% auditable with `View Source` in any browser
- PWA, service worker, and bilingual logic live in vanilla `app.js` — not tied to any framework lifecycle

**Decision:**
Use Eleventy to compile `.njk` templates into static HTML. All dynamic
behaviour (church selection, language toggle, Swish payment link, YouTube
embed, offline caching) is implemented in a single vanilla `app.js` file
that runs in the browser with no framework dependency.

**Consequence:**
- Bundle size: 0 KB of framework JS shipped to the browser
- Build time: ~80 ms for 15 pages (vs. 15–60 s for a Next.js cold build)
- Lighthouse score: 100 Performance on all pages (Cloudflare edge + no JS blocking)
- Developer onboarding: any developer who knows HTML and basic JS can read and change every file
- Long-term risk: Eleventy is stable and slow-moving by design; v3 is backward-compatible with v2

**What we explicitly do NOT do with Eleventy:**
- No client-side routing (page navigations are standard `<a href>` links)
- No state management library (church ID lives in `localStorage`, language in `data-lang`)
- No CSS-in-JS or component CSS (one shared `styles.css`)

**When to revisit:**
If a future screen genuinely requires real-time two-way interactivity (e.g.
a live chat during a service, a ticket booking flow with seat selection),
evaluate HTMX as a progressive enhancement first. Reach for React or SvelteKit
only if HTMX is provably insufficient — and only for that screen, not the
entire portal.

---

## ADR-014: TypeScript för app.js — inte hela frontend

**Date:** 2026-06
**Status:** accepted

**Context:**
`frontend/member-portal/app.js` är den enda filen med komplex runtime-logik:
church-val, språkväxling, content-fetch, PWA-registrering, Swish-länkbygge,
personnummer-validering och formulärhantering. Filen är 553 rader och växer
med varje ny kyrka eller funktion.

De två övriga runtime JS-filerna är:
- `sw.js` (94 rader) — Service Worker, ändras sällan, ingen komplex logik
- `wifi-intake-portal/content.js` (95 rader) — isolerad wifi-portal, stabil

Testerna (`tests/*.js`) är avsiktligt beroende-fria Node.js-assertions och
ska aldrig ha ett build-steg (se ADR-013: noll externa testberoenden).

**Problem som TypeScript löser i app.js:**
1. **Stavfel på content.json-nycklar** — `youtube_chanel_id` istället för
   `youtube_channel_id` är en tyst bug i vanilla JS, en kompileringsfel i TS.
2. **Null-dereference** — `content.upcoming[0].title.sv` kraschar om
   `upcoming` är tom. TypeScript tvingar fram null-checks.
3. **Fel funktionssignatur** — `applyLanguage('svenska')` i stället för
   `applyLanguage('sv' | 'am')` fångas vid kompilering, inte i produktion.
4. **Kontraktbrott mot content.json** — TypeScript-interface `ContentConfig`
   och `Church` dokumenterar och enforcar JSON-schemat maskinellt.

**Varför INTE migrera sw.js, content.js eller testerna:**
- `sw.js` och `content.js` är trivialt korta och stabila — TypeScript ger
  noll värde relativt kostnaden av ett nytt build-steg per fil.
- Testerna är avsiktligt dependency-fria. TypeScript kräver `tsc` eller
  `ts-node`, vilket bryter principen om noll-beroende-testning (ADR-013).

**Decision:**
Migrera enbart `app.js` → `app.ts`. Kompilera med `esbuild` (inte `tsc`)
eftersom `esbuild` är 100× snabbare (~20 ms vs ~2 s), inte kräver en
tsconfig-driven bundle-pipeline, och producerar identisk output.

Typcheck körs separat med `tsc --noEmit` (ingen output, bara fel).
Detta ger fullständig typsäkerhet utan att röra den befintliga 11ty-pipelinen.

**Build-pipeline:**
```
app.ts  →[tsc --noEmit]→  (typcheck, inga filer)
app.ts  →[esbuild]→  app.js  →[11ty]→  dist/
```

`sw.js`, `content.js` och alla `tests/*.js` är oförändrade.

**Consequence:**
- `app.ts` är den auktoritativa källkoden. `app.js` är genererad output.
- `app.js` läggs till i `.gitignore` för member-portal (genererad fil).
- `make test` kör `tsc --noEmit` + `esbuild` + `11ty` + Node-tester
  i sekvens. Allt annat är identiskt med förut.
- Befintliga test-filer importerar fortfarande `../app.js` — de
  importerar esbuild-outputen, inte TypeScript-källan. Testerna kräver
  noll ändringar.
- `node_modules` i member-portal växer med `typescript` + `esbuild`
  (~8 MB dev-dependencies, aldrig deployade till Cloudflare Pages).

**When to revisit:**
Om `sw.js` eller `content.js` växer förbi ~300 rader med komplex
kontrollflöde — migrera dem individuellt med samma mönster.


---

## ADR-015: Avveckling av n8n till förmån för FastAPI BackgroundTasks

**Date:** 2026-06
**Status:** accepted
**Context:** n8n användes ursprungligen för orkestrering och asynkrona jobb (t.ex. webhooks för nya medlemsansökningar, funeral-notifikationer, etc.). Men drift av n8n på Cloud Run medförde en fast kostnad (~5-10 €/månad eftersom minst 1 instans krävdes för cron-tillförlitlighet) samt ytterligare infrastrukturkomponenter (PostgreSQL-databas, Secret Manager-kopplingar, etc.) att underhålla. Dessutom stred det mot principen att minimera komplexitet i infrastrukturen för ett litet MVP-system.
**Decision:** Avveckla n8n-automationstjänsten helt och hållet från GCP-infrastrukturen. Ersätt asynkrona integrationer (som Telegram-notiser och externa webhooks) med FastAPIs inbyggda `BackgroundTasks` och `httpx` direkt i respektive backend-tjänst (såsom `admin-web`).
**Consequence:**
- Enklare infrastruktur med färre rörliga delar och lägre driftskostnad (~0 €/månad för orkestrering då allt körs inom befintliga Cloud Run-tjänster).
- Ingen n8n Cloud Run-instans eller dedikerad PostgreSQL-databas behövs längre i Terraform.
- Webhook-integrationer körs nu som icke-blockerande bakgrundsuppgifter (`BackgroundTasks.add_task(...)`) direkt efter framgångsrika databastransaktioner.
- Nackdel: Vi förlorar n8n:s visuella gränssnitt för att felsöka misslyckade workflows, men fel loggas nu direkt i GCP Cloud Logging för `admin-web` och `membership-intake`, vilket är mer enhetligt.
- Historiska n8n-workflows raderas från katalogen `automation/n8n/`.
**When to revisit:** Om kraven på orkestrering ökar (t.ex. vid behov av komplexa transaktioner över flera dagar, komplicerade retry-policies eller behov av att icke-teknisk personal ska bygga flöden), utvärdera GCP Cloud Workflows eller Temporal.

---

## ADR-016: Migration från PropelAuth till Zitadel Cloud (SaaS) för suveränitet och noll-drift

**Date:** 2026-06
**Status:** accepted

**Context:**
PropelAuth (som används för multi-tenant RBAC i MVP) är en amerikansk SaaS-tjänst. Eftersom den hanterar inloggningar, e-postadresser, IP-adresser och aktivitetsloggar för kyrkomedlemmar och administratörer (vilka kan innehålla RED-zon personuppgifter och därmed medför GDPR- och FISA-relaterade suveränitetsrisker under amerikansk lagstiftning), måste vi migrera till en fullständigt EU/schweizisk datasuverän lösning.

Vi utvärderade följande alternativ för att lösa detta:
1. **Självvärdad Keycloak på Cloud Run/GKE:**
   - **Fördel:** Fullständig kontroll över data och infrastruktur.
   - **Nackdel:** Extremt hög operationell driftsbörda. Keycloak kräver databashantering (PostgreSQL), skalning, patchning, certifikat och kontinuerliga säkerhetsuppdateringar. Detta strider mot vårt mål om noll operationell driftsbörda ("no-ops").
2. **Zitadel Cloud (SaaS):**
   - **Fördel:** Schweiziskt värdskap och schweiziskt bolag (100 % EU/schweizisk datasuveränitet, ingen risk för amerikanska FISA-husrannsakningsorder), fullt stöd för OIDC multi-tenancy (Zitadel "Organizations"), generös gratisnivå (25 000 förfrågningar/månad) och noll operationell driftsbörda då det är en fullt hanterad molntjänst.
   - **Nackdel:** Fortfarande ett beroende av en extern SaaS-leverantör, men suveränitets- och GDPR-risken är helt eliminerad till skillnad från PropelAuth.

**Decision:**
Migrera autentisering och multi-tenant RBAC från PropelAuth till Zitadel Cloud. Vi drar nytta av vår befintliga hexagonala arkitektur (`AuthPort`) för att byta ut `PropelAuthAdapter` mot en standard-baserad `ZitadelAuthAdapter`.

**Consequence:**
- Ingen operationell driftsbörda för att underhålla identitetshantering (identitetsdatabas, uppdateringar, infrastruktur).
- Fullständig efterlevnad av GDPR och suveränitetsprinciper genom att använda ett schweiziskt SaaS-alternativ med dataresidens inom EU/Schweiz.
- Kodmässigt isoleras ändringen helt till adapter-lagret (`ZitadelAuthAdapter` ersätter `PropelAuthAdapter`).
- Vi byter ut det proprietära `propelauth-fastapi`-biblioteket mot standardiserad OIDC-tokenverifiering (t.ex. med hjälp av `pyjwt` eller `authlib` för att läsa JWKS från Zitadel).
- Nya miljövariabler (`ZITADEL_ISSUER_URL`, `ZITADEL_CLIENT_ID` etc.) läggs till och motsvarande `PROPELAUTH_`-miljövariabler avvecklas.

**When to revisit:**
Om Zitadel ändrar sin prismodell så att det blir kostsamt, eller om suveränitetskraven kräver fullständig lokal kontroll, utvärdera Keycloak eller en motsvarande självvärdad IDP igen.

---

## ADR-017: Firestore-lagring för Bidrag (YELLOW) och Säkrad Proxy-lagring för Begravningar (RED) — Alternativ A

**Date:** 2026-06
**Status:** accepted

**Context:**
Systemet behöver stödja persistent lagring för begravningsärenden (`FuneralCase`) och bidragsansökningar (`GrantApplication`).
* **Bidragsansökningar** innehåller endast projektbeskrivningar, budgetar och målgrupper utan några personuppgifter. Detta klassificeras som **YELLOW-zon** (aggregat/finansiellt/strategiskt).
* **Begravningsärenden** innehåller namn, dödsdatum, födelsedatum samt kontaktpersons namn och telefonnummer för avlidna och anhöriga. Detta klassificeras som **RED-zon** (känsliga personuppgifter / PII).

Enligt systemets arkitekturella principer ([`docs/01-architecture-red-yellow-green.md`](01-architecture-red-yellow-green.md)) ska den publikt exponerade frontenden `admin-web` vara ett **tillståndslöst UI-lager** med lägsta möjliga behörighet. Att låta `admin-web` ha direkta databasnycklar eller läs-/skrivrättigheter till RED-zon-data i Firestore bryter mot principen om minsta behörighet (*least privilege*) och ökar attackytan vid en eventuell kompromiss av webbservern.

**Decision:**
Vi implementerar **Alternativ A (Strikt Säkerhet)**:
1. **Bidrag (YELLOW):** `admin-web` sparar och läser bidragsdata direkt mot en Firestore-samling (`grants`) via en lokal `FirestoreGrantTracker`.
2. **Begravningar (RED):** Databaslagringen flyttas helt till `membership-service` (vår säkrade, autentiserade RED-zon-backend) via en `FirestoreFuneralTracker` som hanterar samlingen `funerals`.
3. **API-Proxy:** Vi exponerar säkra och rollbaserade API-endpoints `/api/funerals` i `membership-service`. I `admin-web` implementeras en HTTP-klient (`HttpxFuneralTracker`) som skickar vidare förfrågningar till backend med användarens autentiserings-token bifogad.

**Consequence:**
* **Säkerhet:** RED-zon-uppgifter är säkert isolerade bakom en autentiserings- och auktoriseringsbarriär. Webbservern `admin-web` har inget direkt databaskonto med access till begravningsdatan.
* **Behörighetsstyrning:** Kyrko-isolering och rollbaserad åtkomst (t.ex. att endast `admin` och `pastor` kan se begravningsärenden) hanteras centralt och enhetligt i backend-tjänsten istället för att dupliceras i frontenden.
* **Nätverksprestanda:** Ett extra nätverkshopp (~10–30 ms) tillkommer mellan `admin-web` och `membership-service` vid hantering av begravningsärenden, vilket är försumbart för ett administrativt gränssnitt.
* **Underhåll och testning:** Testsviterna förblir fristående. Lokala tester använder in-memory-mockar och adaptertester mockar Firestore-klienten direkt, vilket eliminerar beroenden på externa resurser eller live GCP-anslutningar vid lokala byggen.

**When to revisit:**
Om vi i framtiden behöver utföra tunga analytiska beräkningar eller rapportering på begravningsdata i YELLOW-zonen (t.ex. i `reporting-service`), måste vi se till att datan anonymiseras eller pseudonymiseras i backend innan den skickas vidare.




