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
**Status:** accepted — implementationen avviker just nu på dataresidens: den aktiva Zitadel-instansen ligger i **US-regionen** (gratisnivå), inte EU/Schweiz. Se **ADR-017**. Den EU/schweiziska datasuveräniteten som beskrivs nedan är ännu **INTE uppfylld** och får inte påstås vara det förrän EU-flytten är gjord.

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

## ADR-017: Tillfällig Zitadel-instans i US-region (gratisnivå) — avsteg från ADR-016:s dataresidens

**Date:** 2026-06
**Status:** accepted (tidsbegränsat, villkorat avsteg från [ADR-016](#adr-016-migration-från-propelauth-till-zitadel-cloud-saas-för-suveränitet-och-noll-drift))

**Context:**
ADR-016 beslutade migration till Zitadel Cloud uttryckligen för **EU/schweizisk dataresidens** (bort från amerikansk jurisdiktion: US Cloud Act / FISA). Zitadels EU/CH-region är dock en **betald** nivå. Under uppbyggnadsfasen vill vi verifiera att **all** auth-funktionalitet fungerar — OIDC authorization-code-flöde, multi-tenancy (Zitadel Organizations per församling), rollerna `admin`/`pastor`/`editor`/`viewer`, lokal JWKS-/RS256-verifiering i samtliga services, samt deploy-pipelinen — innan vi betalar för EU-regionen.

Den **gratisnivå** vi använder för detta ligger i Zitadels **US-region**. Faktiskt nuläge (verifierat mot Zitadel-konsolen, 2026-06-10):
- Instans: `kyrk-auth-oqvxjf.us1.zitadel.cloud` (`us1` = US-region)
- Organization: `EOTK Sverige`; projekt: `kyrk-portal`; app: `admin-web` (Web/OIDC, status Active)
- Client Id matchar `ZITADEL_CLIENT_ID` i `.github/workflows/deploy.yml`
- Inget är ännu deployat till produktion (`deploy.yml` har aldrig körts); ingen skarp persondata finns i instansen

**Decision:**
Bygg upp och verifiera all autentiserings- och RBAC-funktionalitet på Zitadels **gratisnivå i US-regionen** under uppbyggnadsfasen. Detta är ett **medvetet, kostnadsmotiverat och tidsbegränsat avsteg** från ADR-016:s krav på EU/schweizisk dataresidens.

**Hård grind (icke förhandlingsbar):**
Ingen **RED-zon / skarp persondata** (riktiga medlemmar, personnummer, namn, e-post, IP-loggar, riktiga admin-identiteter) får matas in i US-instansen. Endast **test-/syntetisk data** under denna fas. Identitetstjänsten **ska flyttas till Zitadels EU/CH-region innan** något av följande inträffar — vilket som kommer först:
1. Skarp/kritisk persondata matas in, eller
2. Systemet tas i publik produktion (första skarpa `deploy.yml`-körningen mot riktiga användare).

**Grindtolkning (förtydligat 2026-06-13):**
"Skarp persondata" i trigger 1 avser **registrerade som plattformen
behandlar** — församlingsmedlemmar, givare, och riktig personal vars
identiteter administreras i systemet. Den omfattar **inte** utvecklings-
teamets egna operatörskonton (t.ex. `daniel.abbay@compuute.net`) som
används för att bygga och verifiera systemet under denna fas — de är
operatörer, inte data subjects vars uppgifter tjänsten är till för att
hantera. Att logga in med ett eget teamkonto i US-instansen under
uppbyggnaden bryter alltså **inte** grinden. Hård regel ändå: håll
teamets operatörskonton minimerade (inga onödiga identiteter), och
trigger 2 (publik produktion) gäller oavsett — EU-flytten sker före
första riktiga medlem/givare, hanterad som del av go-live-grinden
(samma beslut som domän + prod-cutover, spårat i issue #118).

**Consequence:**
- Under uppbyggnadsfasen är dataresidensen **US, inte EU/CH**. ADR-016:s suveränitetsmål är därmed **inte uppfyllt i nuläget** och får inte påstås vara det i någon dokumentation (RULE 2 — dokument och verklighet ska säga samma sak). Berörda docs (`06-auth-strategy.md`, ADR-016, backlog-issuen) bär nu denna caveat.
- Eftersom endast test-/syntetisk data används medför US-residensen i denna fas **ingen behandling av riktiga personuppgifter** — GDPR-/FISA-risken materialiseras först om grinden ovan bryts.
- **Migrationsväg vid EU-flytt** (ren adapter-/config-ändring, ingen kodändring tack vare `AuthPort`/`SessionPort`): skapa ny instans i EU/CH-region → ny `ZITADEL_ISSUER_URL` + nytt client-id/secret → uppdatera `deploy.yml` och Secret Manager (`zitadel-client-secret`) → återskapa organizations/projekt/roller → verifiera mot full testsvit.
- Separat men relaterat: `JWTSessionAdapter` hämtar i nuläget JWKS med TLS-certverifiering avstängd (`ssl.CERT_NONE`) — ska åtgärdas före *varje* deploy, oberoende av region (egen issue/PR).

**When to revisit:**
Vid den punkt där grinden ovan triggar (all funktion verifierad och redo för produktion, eller innan skarp data). Då: utför EU-region-migrationen, uppdatera ADR-016:s status till uppfylld och sätt denna ADR-017 till **superseded/closed**.




## ADR-018: Pages git-integration som enda produktionsväg för portalen — via radera + återskapa

**Date:** 2026-06-11
**Status:** accepted (ersätter det interimistiska Actions-beslutet i doc 25:s första version)

**Context:**
Pages-projektet `kyrka-portal` var git-kopplat till fel GitHub-repo
(`Compuute/.github`, där projektet låg före flytten till `Compuute/kyrk-projekt`)
och hade ett trasigt byggkommando (`npx eleventy` — fel npm-paket). Effekten var
att sajten frös på sista lyckade deployen medan main gick vidare. Cloudflare
tillåter varken repo-byte eller git-tillkoppling på ett befintligt Pages-projekt,
och publika API:t ignorerar tyst ändringsförsök av `source`. Som akut workaround
byggdes `deploy-sites`-workflowen (wrangler direct upload från Actions) — vilket
fungerade men gav två parallella deploymekanismer när git-frågan väl löstes.

**Decision:**
Radera och återskapa Pages-projektet med **samma namn** (bevarar
`kyrka-portal.pages.dev`), git-kopplat till `Compuute/kyrk-projekt` med
produktionsbranch `main`. Detta är **den enda automatiska deployvägen**:
push till main → Cloudflare bygger (`make build-js && npx @11ty/eleventy`,
output `frontend/member-portal/dist`, root = repo-roten så `functions/`
bundlas) → produktion. Övriga branches får automatiska previews.
`deploy-sites` nedgraderas till **manuellt triggad reservväg** (workflow_dispatch)
för lägen när Pages byggpipeline är nere.

**Consequence:**
- En sanning: main. Portalen kan inte divergera från git, och inga
  API-tokens behövs i det normala flödet (reservvägen behåller sin
  Pages:Edit-token som repo-secret).
- Återskapandet kräver att projektspecifik konfig återställs manuellt:
  KV-bindningen `kyrka_content` (id `f40a72c8…`) måste finnas i **både**
  production och preview, annars ger Pages Functions fel 1101. Detta är
  dokumenterat i doc 25 och var dagens enda incident vid bytet.
- Radering av Pages-projekt blockeras tills gamla deployments rensats via
  API (»too many deployments«) — runbook-detalj värd att minnas.
- Push till main deployar produktion **utan godkännandesteg** — accepterat
  under utvecklingsfasen; härdning vid betalversion är backloggad
  (`.github/backlog/issue-harden-pages-deploy-gating.md`).

**When to revisit:**
Vid betalversion/skarp drift (godkännandegrind), eller om Cloudflare börjar
stödja repo-byte på befintliga projekt.

## ADR-019: Firestore-platspolicy per miljö och terraform-apply som ägaroperation

**Date:** 2026-06-11
**Status:** accepted

**Context:**
Firestore-platsen styrdes av tre osynkade källor: lokala gitignorade
tfvars-filer (dev saknade värdet helt och ärvde multi-region-defaulten
`eur3`; prod stod på regional `europe-north1` — spegelvänt mot rimlig
policy), CI-workflows som genererade `database_location = GCP_REGION` för
**båda** miljöerna, och modulens default. Dessutom visade sig CI:s
`terraform-apply` aldrig ha fungerat: deployer-SA:t har medvetet bara
app-deploy-roller (run.admin, artifactregistry.writer, m.fl.) och saknar
allt som full IaC-apply kräver (storage, datastore, KMS, IAM-administration).

**Decision:**
1. **Platspolicy:** dev = regional `europe-north1` (billig, ingen
   redundans behövs), prod = multi-region `eur3` (redundansen hör hemma i
   prod). Policyn kodas **i git**: explicit per miljö i
   `terraform-plan.yml`/`terraform-apply.yml` samt dokumenterad i
   `terraform.tfvars.example`.
2. **Apply-modell:** CI kör **plan-gate** på PR:ar (fungerar, kräver bara
   läsroller). Full `terraform apply` är en **ägaroperation lokalt** —
   deployer-SA:t utökas inte; att ge ett WIF-exponerat CI-konto nära nog
   owner-rättigheter är fel avvägning för ett security-by-design-projekt i
   denna fas.

**Consequence:**
- Platsbytet genomfördes 2026-06-11 med tomma databaser. Viktiga
  driftlärdomar, nu del av runbook-kunskapen: `google_firestore_database`
  har `deletion_policy = ABANDON` som default — terraform-"destroy" raderar
  **inte** databasen (bra skydd, behålls), så ett äkta platsbyte kräver
  manuell `gcloud firestore databases delete` + ~5 minuters cooldown innan
  databas-id:t kan återanvändas. Med data i databasen tillkommer
  export/import via backup-bucketen.
- Slutläge verifierat: dev = `europe-north1`, prod = `eur3`, noll drift i
  båda workspaces.
- `terraform-apply`-workflowen finns kvar men förblir trasig tills
  SA-frågan eventuellt omprövas — den fungerar som dokumentation av
  CI-flödets tänkta form. Omprövas vid betald GitHub-plan tillsammans med
  godkännandegrindarna (samma backlog-issue som ADR-018).

**When to revisit:**
När prod innehåller skarp medlemsdata (platsbyten blir då migreringsprojekt),
eller om teamet växer så att lokal ägar-apply blir flaskhals.

## ADR-020: Firestore-lagring för Bidrag (YELLOW) och Säkrad Proxy-lagring för Begravningar (RED) — Alternativ A

> *Omnumrerad från ADR-017 (2026-06-12): två ADR:er fick samma nummer. Zitadel-US-beslutet behåller 017 eftersom all extern dokumentation (auth-strategy, GDPR-register, backlog) refererar det numret. Denna ADR hade inga nummerreferenser.*

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

---

## ADR-021: Agent Operating Model — agentiska AI-grupper utvecklar och driftar plattformen

**Date:** 2026-06
**Status:** accepted

**Context:**
Teamet kommer att bestå av agentiska AI-grupper (Claude Code m.fl.) plus mänskliga ägare, som arbetar enligt Anthropics best practice för agenter. Vi hade redan delarna — CLAUDE.md (RULE 1–4), `ops-contract.yaml` (approval/forbidden/escalation för ops), KYA-access-policyn, flagg-governance och CI-gates — men ingen samlad modell för *hur ett agentiskt team opererar säkert*. Utan det riskerar agenter (som är snabba och kan vara självsäkert-fel) att bli en oövervakad väg runt kontrollerna.

**Decision:**
Anta en [Agent Operating Model](governance/agent-operating-model.md) som paraply över befintliga artefakter. Kärnval:
- **Deterministiska guardrails > omdöme** — agenter kan inte prata sig förbi en röd CI-check; enforcement ligger i kod, inte i prompts.
- **Människan äger det oåterkalleliga; agenter äger det reversibla-och-verifierade.** Explicita human-approval-grindar (merge/prod-deploy/schema/pengar/suveränitet/PII) generaliserar `ops-contract`:s `approval_required`.
- **Least privilege per roll** (Builder/Reviewer/Ops/Research) med scope:ad åtkomst (KYA), tillagd i lager.
- **Verifiering mot målet** (RULE 1) + gröna räcken före mänsklig review.
- **Attribution utan AI-committers:** committer = människan (RULE 4); spårbarhet *vilken agent gjorde vad* ligger i PR-beskrivning + sessionstranscripts, inte i git-author.

**Consequence:**
- Säkerheten skalar med antalet agenter — räckena är desamma oavsett hur många agenter eller hur snabbt de rör sig.
- Nya förmågor (ny MCP-server, ny agent-roll, write-behörighet) läggs till genom att ändra modellen i en PR granskad av en människa — aldrig ad hoc.
- KYA-access-policyn + `.mcp.json` blir access-komponenten under modellen (ersätter den fristående PR #18).

**When to revisit:**
När en ny agent-roll eller en write-/deploy-förmåga övervägs, eller när human-approval-grindarna behöver justeras (t.ex. vid produktionssättning av backend). Uppdatera modellen + berörda referensdokument i en PR.

---

## ADR-022: Kalendermotor — plattformens ICU som korrekthetsorakel, egen aritmetik som körtid

**Date:** 2026-06-12
**Status:** accepted

**Context:**
Den etiopiska kalendern med högtider (issue #35, f.d. gamla repots #39) byggdes
ursprungligen som en lös fil som aldrig committades och gick förlorad vid
repo-flytten. Inför återuppbyggnaden utvärderades arkitekturen datadrivet:
hur skulle en aktör som Google bygga tjänsten?

**Alternativ som utvärderades:**

| Ansats | Korrekthetsrisk | Payload | Beroenden | Kommentar |
|---|---|---|---|---|
| A. Egen JDN-aritmetik (ursprungsspecen) | Medel — handrullad kalendermatte är klassisk felkälla | ~12 kB | 0 | Fungerar överallt |
| B. Enbart `Intl` (ICU/CLDR) | Låg — Googles/Unicodes egen motor, samma som Chrome/Android | 0 kB (inbyggd) | 0 | Saknar invers (etiopisk→gregoriansk) och grid-logik |
| C. Kalenderbibliotek (npm) | Låg–medel | 30–200 kB | 1+ | Bryter mot portalens noll-beroende-linje (ADR-013) |
| D. Build-time-precompute (11ty-data) | Låg | 0 kB JS | 0 | Kräver deploy varje månad för att "innevarande månad" ska stämma — passar inte en sajt utan schemalagda byggen |

**Empiri (Node/V8 = Chromes motor, 2026-06-12):** `Intl.DateTimeFormat` med
`u-ca-ethiopic` ger korrekt Sene 5 2018 för dagens datum, Meskerem 1 2018 för
nyåret, Pagumen 6 2015 för skottdagen och Ter 11 2018 för Timkat, inklusive
amhariska månadsnamn. Svaret på "hur skulle Google byggt det": med exakt den
motorn — etiopisk kalender i Chrome/Android *är* ICU.

**Decision:**
Hybrid av A och B: egen minimal JDN-aritmetik som körtidsmotor (krävs ändå för
inversen och månadsgriden, fungerar oavsett webbläsarens ICU-data), men med
**ICU som korrekthetsorakel i testsviten** — motorn korsvalideras mot
`Intl`-konverteringen för 7 800+ datum 1950–2100 plus roundtrip för varje dag
2020–2030 och handverifierade golden-datum. Egen matte tillåts aldrig avvika
från ICU. Högtidsdata (24 fasta högtider, 11 månatliga helgondagar, svenska
röda dagar enligt lag 1989:253 med computus för rörliga) ligger som data i
motorn, GREEN-klassad, och ska innehållsgranskas av församlingen. Rörliga
etiopiska högtider (Fasika m.fl., Bahire Hasab-computus) är medvetet utanför
scope i v1.

**Consequence:**
- Korrektheten är bevisad mot referensimplementationen, inte antagen — testet
  går i CI vid varje ändring.
- Noll beroenden, ~12 kB, CSP-vänlig vanilla JS — i linje med ADR-002/013.
- Lärdomen från förlusten är kodifierad: motorn ligger i git med tester och
  deployas enbart via Pages git-bygget (ADR-018) — en lös fil på disk kan
  aldrig mer vara enda exemplaret.

**When to revisit:**
När rörliga högtider (Fasika/stora fastan) ska in — då behövs Bahire
Hasab-computus med egen golden-testsvit mot EOTC:s publicerade kalendrar.

## ADR-023: Dokumentation och felsökning som räcke, inte god vilja

**Date:** 2026-06-13
**Status:** accepted

**Context:**
Funktioner kunde mergas helt utan dokumentation — det fanns konventioner
(ADR:er, CONTRIBUTING-checklista) men inget som kontrollerade dem. Det var en
av orsakerna till att kalendern kunde "försvinna" obemärkt. Samtidigt växer
teamet mot agentiska supportflöden (ADR om Agent Operating Model) som behöver
maskinläsbara felsökningssteg, inte prosa, för att lösa ops-tasks säkert.

**Decision:**
1. **Docs-freshness-check i CI** (advisory) — en PR som rör funktions-/tjänstekod
   (`frontend/member-portal/src|app|calendar`, `services/`) utan att röra någon
   `docs/`, `ops/runbooks/` eller `.md` får en GitHub-warning + step-summary.
   Advisory, inte blockerande, för att inte stoppa rena refaktorer — men synlig
   i varje PR (deterministiskt räcke i linje med Agent Operating Model).
2. **PR-mall** med explicit doc-val: ADR / feature-doc / runbook / motiverat
   undantag. Tvingar ett aktivt beslut.
3. **Funktionsrunbooks** (`ops/runbooks/*.yaml`) i samma maskinläsbara format
   som drift-/incident-runbooksen, så supportagenter kan felsöka funktioner
   (inte bara infra). Första: `ops/runbooks/calendar.yaml`.

**Consequence:**
- Varje framtida funktion möter en synlig fråga "var dokumenteras detta?".
- Supportagenter får exakta steg per funktion, inkl. att skilja missläsning
  från äkta bugg (t.ex. "Sene 6 ≠ 6 juni") och att klassa högtidsdata som
  innehåll → församlingsgranskning, inte kodbugg.
- Advisory-valet kan skärpas till blockerande check vid betalversion, samma
  spår som övriga härdningsbeslut.

**When to revisit:**
Om warnings ignoreras systematiskt → gör checken blockerande. När fler
funktioner finns → en runbook per större funktionsområde.

---

## ADR-024: Publika sajtens backend-bindning — dev-som-MVP, prod-cutover vid go-live

**Date:** 2026-06-12
**Status:** accepted

**Context:**
Deploy-maskineriet är redan beslutat: backend deployas dev-först-sedan-prod
med approval-gate (`deploy.yml`, miljö via `inputs.environment`), och
Firestore-platspolicyn skiljer miljöerna (ADR-019). Men *vilken* backend den
publika sajten faktiskt anropar var aldrig ett medvetet beslut — det följde
av en hårdkodning. Verifierat 2026-06-12:

- `donate.njk`/`intake.njk` har dev-projektets Cloud Run-URL inbakad
  (`membership-intake-479770870521…`). Prod-projektnumret (`481734975638`)
  finns inte i någon konfig.
- Prod får deployer (13 st via GitHub-deployments) men prod-tjänsterna
  svarar 403 (ingen publik åtkomst) och dagens secrets (Brevo,
  org-mappning, KV-seed) sattes via dev-deployen.
- Slutsats: **dev är i praktiken produktion.** Riktiga besökare på
  kyrka-portal.pages.dev träffar dev-backenden.

Kostnad är inte ett argument åt något håll — Cloud Run skalar till noll, så
en oanvänd prod-miljö kostar nära inget. Beslutet står på risk och
trovärdighet.

**Decision:**
1. **Under MVP (2 testförsamlingar, före styrelsegodkännande): dev är den
   publika backenden, medvetet.** Att riva OIDC/secret-plumbingen till prod
   nu — samma redirect-URI/secret-arbete som dev krävde, gånger två — köper
   inget när enda användarna är teamet självt.
2. **Prod-cutover är en grind före kyrka #3**, paketerad med
   styrelsemötet som ändå beslutar domän + Swish Handel. Vid skala och
   riktiga gåvor/personnummer blir dev-som-prod ohållbart — både för att
   det saknas en säker testmiljö och för att "dev" framför pengar/PII
   underminerar spårbarhets-pitchen.
3. **De-hårdkoda backend-URL:en nu, oavsett cutover-timing.** Flytta den ur
   `.njk`-sidorna till en custom-domän (`api.<domän>`, peka per miljö i
   Cloudflare DNS) eller injicerad konfig. Då blir "byt dev→prod" en
   konfigändring, inte en kodändring — och det är samma domänarbete
   styrelsemötet auktoriserar. Detta är det enda som driftar åt fel håll
   medan vi väntar (varje ny secret sätts bara i dev), så vägen till prod
   ska vara skriptad, inte manuellt återupptäckt.

**Consequence:**
- Tills cutovern: behandla dev som produktion i drift (rollback, övervakning,
  incidenthantering gäller dev-miljön för publika flöden).
- Cutover-checklistan (öppna prod-endpoints, prod-secrets via ägare-lokal
  apply enligt ADR-019, custom-domän, peka frontend) spåras som issue med DoD.
- Prod-deployerna fortsätter (de håller prod-imagen färsk och testar
  pipelinen) men prod är inte live-trafikmål förrän grinden passeras.

**When to revisit:**
Vid styrelsegodkännandet / före onboarding av kyrka #3 — då genomförs
cutovern och denna ADR uppdateras till att prod är den publika backenden.
