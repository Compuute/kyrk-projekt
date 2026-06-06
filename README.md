# kyrk-projekt

AI-native kyrkplattform för Etiopisk-Ortodoxa Tewahedo-kyrkan i Sverige.
Byggd med security-by-design, flerspråksstöd (svenska + amharic),
och en Telegram-bot som admin-gränssnitt.

**Live:** [kyrka-portal.pages.dev](https://kyrka-portal.pages.dev)

## TL;DR

```bash
git clone https://github.com/Compuute/.github.git
cd .github/kyrk-projekt

make install   # pip install all service requirements
make test      # 350+ tests across all services + frontends
```

## Tech stack

| Lager | Teknik | Varför |
|---|---|---|
| **Backend** | Python + FastAPI + Pydantic | TDD-first, clean architecture, type-safe |
| **Frontend (publik)** | Static HTML + vanilla JS + Cloudflare Pages | 15 KB total, <100ms laddtid, gratis |
| **Frontend (admin)** | FastAPI + Jinja2 (server-rendered) | Ingen build-pipeline, ingen npm |
| **Database** | Firestore (EU, CMEK) | Schemaless, EU multi-region, customer-managed encryption |
| **Encryption** | Cloud KMS | Field-level encryption av personnummer |
| **Auth** | PropelAuth (RBAC) | Multi-tenant, free tier, no custom auth code |
| **AI** | Claude (Anthropic API) via n8n + OpenClaw | Bidragsansökningar, översättning sv↔am, KPI-analys |
| **Automation** | n8n (self-hosted on Cloud Run) | Visuella workflows, inbyggd retry, free |
| **CDN/WAF** | Cloudflare (free tier) | DDoS, WAF, global edge, auto-SSL |
| **Infra** | Terraform | Ett `apply` skapar hela GCP-miljön |
| **CI/CD** | GitHub Actions (4 workflows) | Tests, deploy, e2e healthz, nightly drift check |
| **Hosting** | GCP Cloud Run (backend) + Cloudflare Pages (frontend) | Scale-to-zero, ~€20/mån |
| **Notifications** | Telegram Bot API | Gratis, amharic-stöd, bot som admin-gränssnitt |
| **Donations** | Swish deep link | 0 kr/transaktion, öppnar appen direkt |
| **App** | PWA (Progressive Web App) | Installerbar på Android + iOS utan app store |

## Funktioner — vad som finns

### Publik hemsida (LIVE på Cloudflare Pages)

| Sida | URL | Funktion |
|---|---|---|
| Startsida | [kyrka-portal.pages.dev](https://kyrka-portal.pages.dev) | Kyrkans info, aktiviteter, meddelanden (sv + am) |
| Bli medlem | [/intake.html](https://kyrka-portal.pages.dev/intake.html) | Registreringsformulär med GDPR-consent + source-tracking |
| Ge en gåva | [/donate.html](https://kyrka-portal.pages.dev/donate.html) | Swish med beloppsväljare + bankgiro + org.nr |
| Livestream | [/live.html](https://kyrka-portal.pages.dev/live.html) | YouTube-embed (modulärt per kyrka via content.json) |
| Integritetspolicy | [/privacy.html](https://kyrka-portal.pages.dev/privacy.html) | GDPR-policy på svenska + amharic |

| Begravningstjänster | [/funeral.html](https://kyrka-portal.pages.dev/funeral.html) | Paket, priser, hemtransport, jämförelse vs Fonus |

Alla sidor: tvåspråkiga (🇸🇪/🇪🇹), PWA-installerbara, offline-stöd, inga kakor.

### Admin-system (Cloud Run — kräver GCP-deploy)

| Funktion | Sida | Beskrivning |
|---|---|---|
| Dashboard | `/` | Pending intake, KPI, bidrag med deadline, certifikat |
| Intake-hantering | `/submissions` | Godkänn/avslå nya medlemmar med redaction av PII |
| Certifikat | `/certificates/new` | Utfärda dop/vigsel/söndagsskola (sv/am/en, 10 typer) |
| KPI-dashboard | `/kpi` | Deltagarantal, kostnad/deltagare, grant leverage |
| Bidragstracker | `/grants` | 12 bidragskällor med deadline, eligibility, AI-genererade ansökningar |
| Content-editor | `/content-editor` | Redigera hemsidans text sv+am, Claude-översättning |
| GDPR-rapport | `/audit` | En-klicks GDPR/SST/kommun-underlag för granskning |
| Granskningsberedskap | `/audit/generate/gdpr` | 14 compliance-items auto-verifierade |
| Begravningsärenden | `/funerals` | Lista, skapa, checklista, hemtransport-tracker |
| Nytt begravningsärende | `/funerals/new` | Registrera med paketval + hemtransport-option |
| Ärendedetalj | `/funerals/{id}` | 29-punkts checklista, status, minnessida, sorg-kalender |

### Backend-services (4 st + admin-web)

| Service | Zon | Endpoints | Tester |
|---|---|---|---|
| `membership-intake` | RED | POST /intake, GET/POST /submissions/*/approve|reject | 37 |
| `membership-service` | RED | CRUD /members, GET /members/stats/summary | 31 |
| `certificate-service` | RED | POST /certificates, GET /verify, GET /download (10 cert-typer) | 39 |
| `reporting-service` | YELLOW | POST /reports/*, GET /activities/export, pii_guard | 36 |
| `admin-web` | mixed | Alla admin-sidor ovan | 102 |

### Certifikattyper (trilingual: am/sv/en)

| Typ | Ikon | Ålder |
|---|---|---|
| Dop / ጥምቀት / Baptism | — | — |
| Konfirmation / ክርስትና / Confirmation | — | — |
| Vigsel / ጋብቻ / Marriage | — | — |
| Begravning / ቀብር / Funeral | — | — |
| Söndagsskola — Fröet / ዘር / Seed | 🌱 | 5-7 |
| Söndagsskola — Plantan / ተክል / Plant | 🌿 | 7-9 |
| Söndagsskola — Trädet / ዛፍ / Tree | 🌳 | 9-11 |
| Söndagsskola — Lärjungen / ደቀ መዝሙር / Disciple | 📖 | 11-13 |
| Söndagsskola — Tjänaren / አገልጋይ / Servant | 🕯 | 13-15 |
| Söndagsskola — Ambassadören / አምባሳደር / Ambassador | 👑 | 15-18 |

Certifikattyper i koden: `sunday_school_seed`, `sunday_school_plant`,
`sunday_school_tree`, `sunday_school_disciple`, `sunday_school_servant`,
`sunday_school_ambassador` — se `certificate-types.json` för trilingual metadata.

### AI-automation

| Funktion | Teknik | Status |
|---|---|---|
| Bidragsansökan (sv/en) | OpenClaw grant-narrative-sv/en + Claude | ✅ Byggt |
| Översättning sv↔am | Claude via TranslationPort | ✅ Byggt |
| KPI-analys (kvartalsvis) | OpenClaw + sanitizer + n8n | ✅ Workflow definierad |
| Telegram admin-bot | Whisper (röst→text) + Claude (intent) | ✅ Workflow definierad |
| Proaktiv bidragsbevakning | n8n cron + grant tracker | ✅ Workflow definierad |
| Auto-genererat veckoinnehåll | n8n + Claude + content.json | ✅ Workflow definierad |

### n8n workflows (9 st)

| Workflow | Trigger | Vad |
|---|---|---|
| `new_pending_membership_notification` | Webhook | Notifierar admin vid ny intake |
| `monthly_kpi_export` | Cron | Genererar monthly rapport |
| `quarterly_openclaw_analysis` | Cron | Sanitizer → Anthropic → review |
| `fortnox_aggregate_reporting` | Cron | Hämtar finance-aggregat |
| `wifi_portal_content_update` | Cron | Uppdaterar wifi-portal JSON |
| `telegram_activity_broadcast` | Webhook | Tvåspråkig broadcast till Telegram |
| `content_update_notification` | Webhook | Generell content-uppdatering |
| `telegram_admin_bot` | Webhook | AI admin-bot (amharic röst + text) |
| `grief_calendar_reminders` | Cron (daglig) | ተዝካር memorial-påminnelser dag 3/7/12/40/6m/1å |
| `funeral_case_notification` | Webhook | Notifierar vid nytt begravningsärende |

### OpenClaw prompt-templates (8 st)

| Template | Språk | Syfte |
|---|---|---|
| `quarterly-variance` | sv | Kvartalsanalys |
| `annual-planning` | sv | Årsplanering |
| `roi-prioritization` | sv | ROI-ranking |
| `content-planning` | sv | Portal-content |
| `grant-narrative-sv` | sv | Bidragsansökan (SST/MUCF etc) |
| `grant-narrative-en` | en | Bidragsansökan (Erasmus+/ESF+ etc) |

### Publika HTML-sidor

Alla sidor i `frontend/member-portal/`: `index.html`, `intake.html`,
`donate.html`, `live.html`, `privacy.html`. Alla tvåspråkiga (sv+am),
alla med back-link till index.html, alla cachade av service worker.

### Säkerhet (10 defense-in-depth lager)

```
Layer 1:  Cloudflare DDoS + WAF + bot detection         [EDGE]
Layer 2:  Cloud Run --no-allow-unauthenticated           [NETWORK]
Layer 3:  PropelAuth RBAC middleware                      [APPLICATION]
Layer 4:  Pydantic input validation                      [APPLICATION]
Layer 5:  pii_guard recursive PII rejection (422)        [DATA]
Layer 6:  Firestore collection + doc-id scoping          [DATA]
Layer 7:  KMS field-level encryption (personnummer)      [CRYPTO]
Layer 8:  CMEK for entire Firestore database             [CRYPTO]
Layer 9:  Per-service IAM (least privilege)              [IAM]
Layer 10: Audit trail on every RED write                 [AUDIT]
```

### Bidragstracker (12 bidragskällor)

| Källa | Belopp | Land |
|---|---|---|
| SST Organisationsstöd | 50k–2M SEK | 🇸🇪 |
| SST Projektbidrag | 50k–500k SEK | 🇸🇪 |
| MUCF Organisationsbidrag | 50k–500k SEK | 🇸🇪 |
| MUCF Projektbidrag | 100k–500k SEK | 🇸🇪 |
| Arvsfonden Projektbidrag | 200k–5M SEK | 🇸🇪 |
| Arvsfonden Lokalstöd | 500k–10M SEK | 🇸🇪 |
| Kommunala bidrag | 20k–200k SEK | 🇸🇪 |
| Erasmus+ KA2 | 10k–150k EUR | 🇪🇺 |
| ESF+ | 50k–500k EUR | 🇪🇺 |
| Nordiska ministerrådet | 50k–500k DKK | Nordic |
| Fritt Ord | 50k–300k NOK | 🇳🇴 |
| Crafoordska | 25k–200k SEK | 🇸🇪 |

### Multi-church (10 kyrkor)

Alla kyrkor under ärkestiftet kan ha en egen sida. Samma kodbas,
varje kyrka har sin egen `content.json` med:
- Kyrkans namn (sv + am)
- YouTube-kanal-ID
- Swish-nummer
- Adress
- Aktiviteter

En ny kyrka = kopiera content.json + byt 5 värden + deploy. 5 minuter.

## Docs index

| Doc | Syfte |
|---|---|
| [`00-vision.md`](docs/00-vision.md) | Mission, produkt-pelare |
| [`01-architecture-red-yellow-green.md`](docs/01-architecture-red-yellow-green.md) | Zonmodellen |
| [`02-sovereignty.md`](docs/02-sovereignty.md) | EU data residency |
| [`03-mvp-scope.md`](docs/03-mvp-scope.md) | Scope (in/out) |
| [`04-ai-boundaries.md`](docs/04-ai-boundaries.md) | Vad AI får/inte får se |
| [`05-security-principles.md`](docs/05-security-principles.md) | Säkerhetsregler |
| [`06-auth-strategy.md`](docs/06-auth-strategy.md) | PropelAuth + BankID roadmap |
| [`07-openclaw-production-flow.md`](docs/07-openclaw-production-flow.md) | n8n → sanitizer → Anthropic → review |
| [`10-getting-started.md`](docs/10-getting-started.md) | **15 min onboarding** |
| [`11-development-guide.md`](docs/11-development-guide.md) | **Adapter-mönster, TDD, lägga till features** |
| [`12-operations.md`](docs/12-operations.md) | **Deploy, rollback, monitoring** |
| [`13-runbook.md`](docs/13-runbook.md) | 5 incident-playbooks |
| [`14-architecture-decisions.md`](docs/14-architecture-decisions.md) | **12 ADRs** |
| [`15-ab-testing-strategy.md`](docs/15-ab-testing-strategy.md) | Phase 3 |
| [`16-defense-in-depth.md`](docs/16-defense-in-depth.md) | **Service merge/split policy** |
| [`17-audit-readiness.md`](docs/17-audit-readiness.md) | **Granskningsberedskap (IMY/SST/kommun)** |
| [`18-ai-admin-bot.md`](docs/18-ai-admin-bot.md) | **Telegram-bot för pastor (amharic röst)** |
| [`19-funeral-bureau-investment-analysis.md`](docs/19-funeral-bureau-investment-analysis.md) | **Begravningsbyrå: investering, konkurrens, P&L** |
| [`20-funeral-strategic-investments.md`](docs/20-funeral-strategic-investments.md) | **Strategiska investeringar: 8 områden, beslutskarta** |
| [`21-funeral-global-benchmark.md`](docs/21-funeral-global-benchmark.md) | **Benchmark: kyrko-drivna begravningstjänster globalt** |
| [`22-repatriation-requirements-checklist.md`](docs/22-repatriation-requirements-checklist.md) | **Hemtransport: ambassad, airline, IATA-krav (verifierat)** |
| [`23-funeral-service-agreement.md`](docs/23-funeral-service-agreement.md) | **Uppdragsavtal: ansvarsfördelning, SLA, KPI, kundkommunikation** |
| [`architecture/cloudflare-edge.md`](docs/architecture/cloudflare-edge.md) | Sekvensdiagram, DNS, felsökning |
| [`architecture/threat-model.md`](docs/architecture/threat-model.md) | STRIDE |
| [`governance/gdpr-register.md`](docs/governance/gdpr-register.md) | **Art. 30 registerförteckning** |
| [`governance/rbac.md`](docs/governance/rbac.md) | Rollmatris |
| [`governance/policies.md`](docs/governance/policies.md) | Retention, radering |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | PR-flöde, review-krav |

## Siffror

| Mätvärde | Antal |
|---|---|
| Commits | 52 |
| Filer | 530+ |
| Python-tester | 245 |
| Frontend-tester (Node) | 100+ |
| **Totalt tester** | **350+** |
| Backend-services | 4 + admin-web |
| Publika HTML-sidor | 6 (live på Cloudflare) |
| OpenClaw-templates | 8 |
| n8n-workflows | 11 |
| ADRs | 12 |
| Docs | 30+ |
| Bidragskällor | 12 |
| Certifikattyper | 10 |
| Språk | 3 (sv, am, en) |

## Common commands

```bash
make test                    # full suite (350+ tests)
make test-admin-web          # one service
make lint                    # syntax + terraform fmt
make local-ci                # mirrors CI locally
make docs-serve              # live docs on :8090
make onboarding              # build onboarding HTML
make bootstrap ENV=dev       # first-time GCP setup
make deploy ENV=dev          # deploy backend to Cloud Run
make deploy-sites            # deploy frontends to Cloudflare Pages
make deploy-all              # both
make smoke ENV=dev            # curl /healthz on all services
make clean                   # remove caches
```
