# 28 — Agentisk driftmodell: teknisk skuld, agentkatalog och färdplan

Datadriven inventering (2026-06-12) av teknisk skuld plus en realistisk plan
för att låta AI-agenter ta över det tunga dagliga arbetet — medlemshantering,
söndagsskoleadministration, fondansökningar och drift — så att föräldrar och
medlemmar kan fokusera på församlingen. Allt inom ramarna i
[AI-RULES.md](../AI-RULES.md), [ops-contract.yaml](../ops/ops-contract.yaml)
och zonmodellen i [01-architecture-red-yellow-green.md](01-architecture-red-yellow-green.md).

---

## 1. Teknisk skuld — inventering med belägg

Basdata: 5 tjänster, 442 testfunktioner, repo-vakter gröna. Rankat efter
hävstång; "blockerar agenter" markerar poster som måste lösas innan
agentdrift är säker.

| # | Skuld | Belägg | Allvar | Blockerar agenter |
|---|---|---|---|---|
| 1 | Zitadel-auth vendorerad i 4 tjänster utan drift-vakt; skör fallback som gräver church_id ur roles-claimet | `services/*/app/adapters/zitadel_auth.py` — 3 byte-identiska + 1 avvikande kopia; intake-scopingbuggen uppstod i just den avvikande | Hög | Ja — agent-identiteter går genom samma auth |
| 2 | Multi-tenancy: en delad Zitadel-org (`376713621675248694`) för alla admins; kvittoregistret har 1 av 9 kyrkor | `membership-intake/app/domain/churches.py` vs `frontend/member-portal/churches.json` | Hög | Ja — agenters behörighet kan inte avgränsas per kyrka |
| 3 | **Identifierarinkonsekvens**: intake/donationer nycklar data på portal-slug, men membership/certificate/reporting nycklar på `actor.church_id` = org-id i produktion | `membership_service.py:68,144`, `certificate_service.py:55,128`, `activity_service.py:40` | Hög | Ja — agenter som korsar tjänstegränser möter två id-världar |
| 4 | In-memory rate limiter i produktion — kringgås när Cloud Run skalar ut | `membership-intake/app/adapters/factory.py` (kommentaren medger det) | Hög | Delvis |
| 5 | Ingen kö/schemaläggare: inga Cloud Tasks/PubSub/Scheduler i Terraform; endast FastAPI BackgroundTasks utan retries | grep över `infra/` + `services/` | Hög | **Ja — största blockeraren** |
| 6 | 60 %-täckningsregeln mäter filexistens, inte radtäckning; ingen pytest-cov i CI | `tests/test_coverage_threshold.py` | Medel | Ja — agentändrad kod kräver ärlig täckning |
| 7 | `routes_combined.py` i admin-web: 1 626 rader, 42 endpoints, 4 st `except Exception: pass` | `services/admin-web/app/api/routes_combined.py:217-269` | Medel | Nej |
| 8 | HTTP-adaptrar har timeout men inga retries — notiser kan tappas vid nätverksblipp | `http_notifier.py`, `httpx_clients.py` | Medel | Ja — agentflöden kräver leveransgaranti |
| 9 | Genererad `app.js` i git; hårdkodad `nacka`-default; `_ADMIN_ROLES` duplicerad; docs-vakt täcker bara indexering | diverse | Låg | Nej |

Posterna 1–3 hänger ihop: roten är att **kanoniskt kyrk-id är odefinierat**.
Beslut (ska bekräftas som ADR): *portal-slugen är kanoniskt id i all
domändata; org-id → slug löses vid auth-gränsen.* Donations-/intake-fixarna
(2026-06-11/12) implementerar detta lokalt via `resolve_church_id`; samma
mappning ska in i övriga tjänster innan data i produktion hinner nyckas
på org-id i större skala.

---

## 2. Vad som redan finns att bygga på

Detta är inte ett grönfältsprojekt. Befintliga byggstenar:

- **OpenClaw** (`automation/openclaw/`): sanitizer (whitelist) → mall →
  Claude → schemavalidering → pending → mänsklig granskning. Detta ÄR
  agentmönstret, i drift för bidragsnarrativ och kvartalsanalys.
- **RBAC-kapaciteten "Approve AI output"** (endast `admin`) — godkännande-
  modellen är redan designad ([governance/rbac.md](governance/rbac.md)).
- **ops-cli.py** med PII-filter + [ops-contract.yaml](../ops/ops-contract.yaml)
  som definierar vad en agent får göra själv (health, loggar, driftcheck,
  backup-verify) och aldrig får göra (prod-deploy, IAM, radera data,
  RED-data externt).
- **Anthropic-översättaradaptern** (sv/amhariska) i admin-web.
- **Pending→approve-mönstret** i intake- och donationsflödena.

## 3. Tjänstekarta: klassisk kyrkoservice → vår digitala motsvarighet

| Klassisk tjänst | Vår motsvarighet | Status |
|---|---|---|
| Dop-/vigsel-/medlemsintyg ur arkiv | certificate-service med publik verifiering utan identitetsläcka | Byggt |
| Kollekt och gåvor | Donationsflöde med verifierat e-kvitto | Byggt, aktivering pågår (issue #27) |
| Begravningsstöd | Funeral-tracker: paket, program, repatriering | Byggt |
| Katekes/söndagsskola | Endast aggregatrapportering; roster, närvaro, föräldranotiser saknas | Grönfält |
| Flerspråkig församlingskommunikation | Translator-adapter + content.json (sv/am) | Delvis |
| Själavård/bokning | — | Grönfält |

## 4. Agentkatalogen

I riskordning (lägst först). Genomgående principer:

1. **RED-data når aldrig en LLM** — sanitizer-profiler är obligatoriska.
2. **Agenter beslutar aldrig i RED-zonen** — de förbereder; människan
   godkänner ("Approve AI output").
3. **Varje agentaktion auditloggas** (aktör = agentens servicekonto).
4. **Vendor-SDK:er endast i `app/adapters/`** — även agentkod följer
   hexagonregeln.

| Agent | Gör | Zon | Kräver |
|---|---|---|---|
| Rapportagenten | Schemalagda månads-/kvartals-/styrelserapporter (`POST /reports/*` finns) | YELLOW | Cloud Scheduler |
| Kassörs-assistenten | Påminner om donationer overifierade > 3 dagar; månadsavstämning. Verifierar aldrig själv | YELLOW | Scheduler + notifier-retries |
| Bidragsagenten | Bevakar utlysningar (GREEN), matchar aktivitets-KPI:er mot fondkriterier, skriver utkast via OpenClaw; styrelsen godkänner före inskick | GREEN + YELLOW | Granskningsvy i admin-web (grant-tracker finns) |
| Intake-sekreteraren | Dedupe, validering, påminnelser om liggande ansökningar. Auto-approve är förbjudet (RED) | RED-metadata | Scheduler |
| Söndagsskole-koordinatorn | Föräldrapåminnelser, auto-utfärdade kursintyg via certificate-service, terminsrapporter | RED (roster) + YELLOW | Rostermodul (grönfält), notiskanal |
| Ops-agenten | Daglig health/backup-verify/driftcheck; incident skapas vid larm — allt inom ops-contract | GREEN | Scheduler (ops-cli finns) |

Bidragsagenten har störst hävstång mot målet att förvärva kyrkobyggnaden
(se [20-funeral-strategic-investments.md](20-funeral-strategic-investments.md)).

## 5. Ramverksval: pipelines före multi-agent-ramverk

Beslut: **inget tungt agentramverk (CrewAI/LangGraph) i steg 1.** Skäl:

- Våra flöden är deterministiska pipelines med ett LLM-steg och ett
  mänskligt godkännande — exakt det OpenClaw redan gör, med sanitizern
  som PII-garanti. Ett ramverk skulle ersätta den garantin med
  abstraktioner vi inte kontrollerar.
- AI-RULES förbjuder vendor-SDK:er utanför adapters — varje ramverk måste
  ändå kapslas där, vilket äter upp dess bekvämlighetsvinst.
- Det som saknas är rörläggning, inte agentintelligens:
  **Cloud Scheduler → Pub/Sub → små Python-workers (hexagonala) →
  Anthropic API bakom en LLMPort → pending-kö i admin-web → godkännande.**

Omprövningspunkt: > 3 agentflöden i drift och dokumenterat behov av
orkestrering mellan dem. För kodunderhåll används Claude Code i GitHub
Actions (befintligt).

## 6. Färdplan — skulden och agenterna i samma drag

- **Fas 0 (dagar):** Merga intake-scopingfixen. Kanonisk auth-källa i
  `libs/shared-auth/` + drift-vakt (`tests/test_shared_auth_sync.py`) +
  synkskript. ADR för kanoniskt kyrk-id. Rate limiter → Firestore-baserad.
  → löser skuld 1, 3 (beslut), 4.
- **Fas 1 (veckor):** Cloud Scheduler + Pub/Sub i Terraform,
  `audit_events`-kollektion, eget servicekonto/RBAC-identitet för agenter,
  retries i notifier-adaptrar. Första agenterna: rapport + ops (YELLOW/GREEN,
  ofarliga). pytest-cov-gate i CI. → löser skuld 5, 6, 8.
- **Fas 2:** Bidragsagenten end-to-end med styrelsegranskning i admin-web.
- **Fas 3:** Söndagsskolemodul (roster, närvaro, intyg) + koordinatoragenten.
  Dela upp `routes_combined.py` i samma veva. → löser skuld 7.
- **Fas 4:** Egna Zitadel-orgs per kyrka — *före* nästa kyrka onboardas.
  → löser skuld 2.

## 7. Stoppvillkor

Agentdrift pausas omedelbart om något av följande inträffar:

- PII upptäcks i en LLM-payload eller agentlogg (kritisk eskalering enligt
  ops-contract).
- En agent agerar utanför sin RBAC-roll eller utan auditpost.
- Godkännandekön kringgås (en AI-genererad artefakt publiceras/skickas
  utan "Approve AI output").
