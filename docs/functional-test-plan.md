# Funktionellt testunderlag (manuell genomgång)

Systematisk checklista för att gå igenom **hela** plattformens funktioner —
frontend, edge, backend, tvärgående krav, automation, och funktioner som ännu
inte är byggda. Syftet är att inget faller mellan stolarna vid en release- eller
acceptansgenomgång.

## Så här används underlaget
- Gå igenom rad för rad. Markera **status**: ✅ pass · ❌ fail · ⏭️ ej tillämplig · ⏳ ej byggd.
- Kolumnen **Täckning** visar om funktionen redan har **AUTO**(matiserat) test
  (kör `make test`) eller behöver **MANUELL** verifiering.
- Kör först regressionssviten: `make test` (Python + Node + guards). Allt nedan
  utöver det är funktionell/manuell acceptans.
- Roller som ska testas genomgående: **admin, pastor, editor, viewer** + oinloggad.

---

## 1. Frontend — publika portalen (`member-portal`)

### 1.1 Sidor & rendering
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| FE-01 | Alla 15 sidor laddar | Öppna index, intake, donate, live, funeral, about, contact, calendar, faq, baptism, tezkar, library, support, venue, privacy | 200, inget tomt innehåll, ingen JS-konsolfel | AUTO (`test_all_pages`, `test_critical_functions`) | |
| FE-02 | Pretty-URL/subsidor | Öppna `/contact/`, `/funeral/` direkt | Rätt sida, footer + meny renderas | AUTO (`test_navigation`) | |
| FE-03 | Tvåspråkigt innehåll finns | Varje textelement har `.sv` + `.am` | Inga saknade översättningar | AUTO (`test_all_pages`) | |

### 1.2 Språkväxling (sv/am)
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| FE-10 | Pill-växling på klientsidan | Klicka am → sv | DOM växlar direkt, ingen reload (lokalt) | AUTO (`test_app`) | |
| FE-11 | Edge-prefix-routing | Besök `/`, utan språk-cookie | Redirect till `/sv/` el. `/am/` enligt Accept-Language | MANUELL (kräver edge-deploy) | |
| FE-12 | Språk-cookie sätts | Växla språk | `selected_language` cookie persisterar val | MANUELL | |
| FE-13 | Amharisk font/rendering | Visa am | Noto Sans Ethiopic, korrekt typografi | MANUELL | |

### 1.3 Församlingsväljare
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| FE-20 | Lista & sök församlingar | Öppna väljaren, sök på namn/stad | Filtrerad lista (sv/am/stad) | MANUELL | |
| FE-21 | Välj församling | Välj en kyrka | `selectedChurch` i localStorage + `selected_church`-cookie, reload | MANUELL | |
| FE-22 | Innehåll byts per kyrka | Byt kyrka | Titel/footer/org.nr/telefon uppdateras från `churches.json` | AUTO (`test_app` data-load) | |
| FE-23 | Geolokalisering (närmaste) | Klicka "hitta närmaste" | Sorterar lista på avstånd (om tillåtet) | MANUELL | |
| FE-24 | Default utan val | Rensa localStorage | Faller tillbaka på `nacka` | AUTO (`test_app`) | |

### 1.4 Formulär & validering
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| FE-30 | Namn-validering | Tomt / med siffror / giltigt | Avvisar tomt + siffror, accepterar giltigt | AUTO (`test_app`) | |
| FE-31 | Telefon-validering | `+46…`, `07…`, skräp | Accepterar svenska format, avvisar skräp | AUTO (`test_app`) | |
| FE-32 | Personnummer (Luhn) | Giltigt / felaktigt / tomt | Luhn-kontroll, tomt tillåtet | AUTO (`test_app`) | |
| FE-33 | GDPR-samtycke (checkbox) | Skicka utan / med samtycke | Kan ej skicka utan; timestamp sätts | AUTO (`test_intake_form`, `test_critical_functions`) | |
| FE-34 | Swish deep-link (medlemsavgift) | Enskild 200 / familj 500 | `swish://` med rätt belopp/payee/meddelande | AUTO (`test_app`, `test_donate`) | |
| FE-35 | Swish donation | Donate-sida, valfritt belopp | Korrekt deep-link | AUTO (`test_donate`) | |
| FE-36 | Medlemstyp-val | Välj enskild/familj | Rätt belopp + fält | MANUELL | |

### 1.5 PWA
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| FE-40 | Manifest giltigt | Ladda `manifest.json` | Namn, ikoner 192/512, standalone | AUTO (`test_pwa`, `test_cloudflare_ready`) | |
| FE-41 | Installerbar | Lägg till på hemskärm (mobil) | Ikon + standalone-läge | MANUELL (enhet) | |
| FE-42 | Offline-cache | Stäng nät, öppna cachade sidor | Sidor laddar offline (service worker) | MANUELL | |
| FE-43 | Uppdaterings-banner | Deploya ny version | "Ny version tillgänglig" + uppdatera-knapp | MANUELL | |
| FE-44 | SW pretty-URL-fallback | Offline, gå till `/contact/` | Visar cachad sida, inte blankt | AUTO (`test_pwa`) | |

### 1.6 Mätning (ska vara VILANDE)
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| FE-50 | Mätflagga av | Inspektera `app.js` / nätverk | `METRICS_ENABLED = false`; **inga** POST `/m`; inga `m_*`-localStorage | AUTO (`test_metrics`, `test_docs_freshness` tripwire) | |
| FE-51 | Policy matchar | Läs privacy-sidan | "inga analysverktyg" (sant medan vilande) | AUTO (tripwire) | |

### 1.7 Säkerhet / integritet (frontend)
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| FE-60 | Inga externa skript | Granska sidkälla | Inga tredjepartsskript, ingen tracker | AUTO (`test_privacy`) | |
| FE-61 | Säkerhetsheaders | Inspektera svar | CSP, HSTS, X-Frame-Options (`_headers`) | MANUELL (edge) | |
| FE-62 | Integritetspolicy komplett | Läs privacy (sv+am) | Art. 6/15/17, IMY, org.nr, KMS, EU-residens, kakor | AUTO (`test_privacy`) | |

---

## 2. Edge-funktioner (Cloudflare Pages Functions)
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| ED-01 | Språk-redirect | Begär `/` utan prefix | 302 → `/sv/` el `/am/` | MANUELL (deploy) | |
| ED-02 | KV-config-injektion | Ladda prefixad sida | `window.__KYRK_CONFIG__` injiceras från KV | MANUELL | |
| ED-03 | `content.json` från KV | GET `/content.json` med church-cookie | Rätt församlings config, 404 om saknas | MANUELL | |
| ED-04 | Länk-omskrivning | Inspektera interna länkar | Prefixas med `/sv` el `/am`; tel/mailto/swish lämnas | MANUELL | |
| ED-05 | Metrics-beacon vilande | POST `/m` (när odeployad/utan KV) | 204, lagrar inget; okända events tappas | AUTO (`test_metrics_privacy_guard`) | |

---

## 3. Backend per tjänst (API + domän + RBAC + zon)

> Generell mall per endpoint: (a) lyckat fall, (b) fel indata → 422,
> (c) obehörig roll → 403, (d) annan församling → 404 (existens-döljning),
> (e) audit-händelse skrevs, (f) ingen PII i loggar.

### 3.1 membership-intake (RED, publik write)
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| MI-01 | Skicka registrering | POST `/` med giltig payload | 202, pending-submission skapas | AUTO | |
| MI-02 | Validering | Ogiltigt personnummer/fält | 422 | AUTO | |
| MI-03 | Lista pending (admin) | GET `/submissions` som admin | Endast egen församlings | AUTO | |
| MI-04 | Godkänn → medlem | POST approve | Skapar member i membership-service, audit | AUTO | |
| MI-05 | Avslå | POST reject | Status uppdaterad, audit | AUTO | |
| MI-06 | RBAC | Som viewer | 403 på approve/reject | AUTO (`test_*`) | |

### 3.2 membership-service (RED, autentiserad, KMS)
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| MS-01 | Skapa medlem | POST `/` admin | 201, personnummer KMS-krypterat | AUTO (`test_api_members`) | |
| MS-02 | Hämta medlem | GET `/{id}` | Egen församling; annan → 404 | AUTO | |
| MS-03 | Uppdatera | PATCH `/{id}` | Fält uppdateras, audit | AUTO | |
| MS-04 | Avaktivera | POST deactivate | Status inaktiv, 30-dagars retention | AUTO | |
| MS-05 | Statistik | GET `/stats/summary` | Aggregat, ingen PII | AUTO (`test_member_stats`) | |
| MS-06 | Betalning | autogiro/Swish/tezkar-portar | Korrekt hantering | AUTO (`test_payment`, `test_billecta_adapter`) | |
| MS-07 | Begravningsfall | CRUD `/funerals` | Skapa/hämta/lista/radera, spårning | AUTO (`test_api_funerals`, `test_firestore_funeral_tracker`) | |
| MS-08 | Auth (Zitadel/OIDC) | Ogiltig/utgången token | 401 | AUTO (`test_zitadel_auth`) | |

### 3.3 certificate-service (RED, autentiserad)
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| CS-01 | Utfärda certifikat | POST `/` | 201, UUID-id (ej sekventiellt) | AUTO (`test_api_certificates`) | |
| CS-02 | Återkalla | POST revoke | Status revoked (raderas ej) | AUTO | |
| CS-03 | Frys | POST freeze | Status frozen | AUTO | |
| CS-04 | Ladda ner (admin) | GET download | Endast behörig | AUTO | |
| CS-05 | **Publik verifiering** | GET `/verify/{id}` | Visar BARA typ/datum/kyrka/status — **aldrig identitet** | AUTO | |

### 3.4 reporting-service (YELLOW, aggregat)
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| RS-01 | Skapa aktivitet | POST `/activities` | 201, åldersband validerade mot total | AUTO (`test_api_reports`) | |
| RS-02 | Åldersband-validering | Summa ≠ total | 422 | AUTO | |
| RS-03 | Månadsrapport | POST `/reports/monthly` | KPI-aggregat | AUTO | |
| RS-04 | Kvartalsrapport | POST `/reports/quarterly` | Variansaggregat | AUTO | |
| RS-05 | Styrelse-/bankexport | POST `/board-export` | PaymentSummary, inga personnamn | AUTO | |
| RS-06 | Period-export | GET `/activities/export/period` | Aggregat för intervall | AUTO | |
| RS-07 | Ingen PII på ingress | Skicka payload med namn | Avvisas/saneras (zon-regel) | AUTO | |

### 3.5 admin-web (UI-flöden)
| ID | Funktion | Steg | Förväntat | Täckning | Status |
|----|----------|------|-----------|----------|--------|
| AW-01 | Login/OIDC + callback | Logga in via Zitadel | Session-cookie `kyrk_session` (HTTP-only) | AUTO (`test_auth_and_login`, `test_zitadel_session`) | |
| AW-02 | Logout | POST `/logout` | Session rensad | AUTO | |
| AW-03 | Dashboard | GET `/` | Översikt, rollanpassad | MANUELL | |
| AW-04 | Intake-godkännande | `/submissions` → approve/reject | Statusändring + audit | AUTO | |
| AW-05 | Utfärda certifikat | `/certificates/new` | Skapar via service | MANUELL | |
| AW-06 | KPI-vy | `/kpi` | Rapporter renderas | MANUELL | |
| AW-07 | Bidrag (grants) | lista/visa/ansök/generera/status | Flöde + AI-narrativ via sanitizer | MANUELL | |
| AW-08 | Innehållseditor | save/translate/add-activity | Skriver KV-config, översättning | MANUELL | |
| AW-09 | Audit-vy + rapporter | `/audit` + generate | Granskningsrapporter | MANUELL | |
| AW-10 | Begravningar | lista/ny/status/checklista/noter/minnessida | Fullt fallflöde | MANUELL | |
| AW-11 | Skattesamtycke (tezkar) | `/tax-consent` | Samtyckeshantering | MANUELL | |
| AW-12 | Datakvalitet | `/data-quality` | Kvalitetsvy | MANUELL | |
| AW-13 | Healthz | GET `/healthz` | 200 | AUTO | |
| AW-14 | RBAC genomgående | Varje vy som viewer/editor/pastor | Rätt behörighet/spärr | AUTO (`test_factory`, `test_no_vendor_lockin`) + MANUELL | |

---

## 4. Tvärgående krav (cross-cutting)
| ID | Krav | Verifiering | Täckning | Status |
|----|------|-------------|----------|--------|
| X-01 | RBAC-matris | admin/pastor/editor/viewer mot varje skyddad åtgärd (se `governance/rbac.md`) | AUTO + MANUELL | |
| X-02 | 404-regel (cross-church) | Åtkomst till annan församlings resurs ger 404, inte 403 | AUTO | |
| X-03 | Audit trail | Varje RED-skrivning loggar actor/action/timestamp | AUTO | |
| X-04 | Zonmodell RED→YELLOW | Ingen PII i aggregat/loggar/webhooks/LLM | AUTO (`test_project_security_guard`, `pii_guard`) | |
| X-05 | Sanitizer före Anthropic | YELLOW→LLM passerar sanitizer | AUTO (`profiles.json` + nightly) | |
| X-06 | Hexagonal arkitektur | Inga vendor-SDK i api/ports/services | AUTO (`test_architecture_guard`) | |
| X-07 | Felhantering downstream | Firestore/KMS/Zitadel nere → tydligt fel, ingen krasch | MANUELL | |
| X-08 | i18n överallt | sv + am på alla användartexter | AUTO (frontend) + MANUELL (admin) | |
| X-09 | Dataresidens | Data i `europe-north1`; auth migreras EU före live (gate 1) | MANUELL/ops | |

---

## 5. Automation
| ID | Funktion | Verifiering | Täckning | Status |
|----|----------|-------------|----------|--------|
| AUT-01 | OpenClaw-mallar (6 st) | Varje mall: giltig JSON + `expected_output_schema` | AUTO (`test_ops_guardrails`, `test_docs_freshness`) | |
| AUT-02 | Sanitizer-profiler | YELLOW-only / GREEN-only filtrerar PII | AUTO | |
| AUT-03 | Grants-databas | Antal/format konsekvent med docs | AUTO (`test_docs_freshness`) | |
| AUT-04 | Ops-CLI | `health/status/logs/backup/drift/incident` | AUTO (`test_ops_guardrails`) + MANUELL | |

---

## 6. Tilltänkta / ej byggda funktioner (testas när de byggs) ⏳
| ID | Funktion | Status idag | Vad som ska testas när byggd |
|----|----------|-------------|------------------------------|
| FUT-01 | **Telegram admin-bot** (doc 18) | Specad, ej i kod | Amharisk röst-kommando → admin-åtgärd; ingen PII i botloggar |
| FUT-02 | **Push-notiser** | `sw.js` har handler; ingen subscribe-flow | Opt-in-knapp, VAPID-subscribe, leverans iOS/Android, ingen PII i payload |
| FUT-03 | **Inloggad medlemsportal** (`mobile-web`) | Placeholder | OIDC/PKCE-login, RED-data kräver session, mobil-först |
| FUT-04 | **PWA-mätning (aktivering)** | Vilande (`METRICS_ENABLED=false`) | Vid `true`: räknare ökar, opt-out/DNT, policy+GDPR §5 uppdaterad (tripwire) |
| FUT-05 | **Hemtransport-tracker** (funeral) | Delvis fält | Ambassad/airline/IATA-steg, statusflöde |
| FUT-06 | **BankID / Bankgirot e-medgivande** | Stub | Signeringsflöde autogiro |
| FUT-07 | **Mobilapp-wrapper (A→B)** | Ej aktuellt | Om aktiverad: butiksinstall, native push, deep links |

---

## 7. Täckningskarta (snabböversikt)
- **Stark AUTO-täckning idag:** validering, Swish, PWA-struktur, integritetspolicy,
  alla service-API:er (CRUD/RBAC/404/audit), zon-/arkitektur-guards, mät-vilande.
- **Behöver MANUELL acceptans:** edge-routing/headers (kräver deploy),
  PWA-install/offline på riktig enhet, admin-web UI-flöden (grants, content-editor,
  begravningar, skattesamtycke), i18n i admin, downstream-felscenarier.
- **Ej testbart än (⏳):** allt i §6 — lägg till testfall när funktionen byggs.

> Kör `make test` för AUTO-raderna; gå igenom MANUELL-raderna i en
> staging-/preview-miljö före varje skarp release.
