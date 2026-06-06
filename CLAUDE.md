# CLAUDE.md — regler för AI-assistenter

Detta dokument läses av Claude Code, Antigravity, ChatGPT, Cursor,
Copilot och alla andra AI-verktyg som genererar kod i detta repo.

**Om du är en AI-assistent: följ dessa regler utan undantag.**

## Arkitekturregler (BRYT ALDRIG)

### 1. Ports/Adapters — ingen vendor lock-in

```
TILLÅTET:
  app/api/routes.py  → importerar från app/ports/
  app/ports/*.py     → definierar Protocol-klasser (inga vendor-imports)
  app/adapters/*.py  → importerar vendor-bibliotek (httpx, anthropic, google, etc.)

FÖRBJUDET:
  app/api/routes.py  → import httpx          ❌
  app/api/routes.py  → import anthropic      ❌
  app/api/routes.py  → from google.cloud ... ❌
  app/ports/*.py     → import httpx          ❌
```

Om du behöver en extern tjänst:
1. Skapa ett Protocol i `app/ports/`
2. Skapa en fake-adapter i `app/adapters/fake_*.py`
3. Skapa en produktionsadapter i `app/adapters/`
4. Registrera i `app/adapters/factory.py`
5. Lägg till i `app/api/deps.py`
6. Lägg till i `tests/conftest.py`

**CI-test `test_no_vendor_lockin.py` failar om du bryter detta.**

### 2. Zonmodellen (RED / YELLOW / GREEN)

```
RED:    Personnummer, namn, e-post, telefon, adress
        → BARA i membership-intake, membership-service, certificate-service
        → ALDRIG i reporting-service, admin-web templates, n8n, Telegram

YELLOW: Aggregerade siffror, KPI, anonymiserad statistik
        → reporting-service, admin-web dashboards
        → Får gå till Anthropic API via sanitizer

GREEN:  Publik information, content, bidragsdatabas
        → frontend, openclaw, n8n workflows
        → Fritt att skicka till LLM
```

**Fråga dig: "Kan denna data identifiera en person?"**
- Ja → RED. Bakom auth + KMS.
- Nej → YELLOW eller GREEN.

### 3. PII-regler

```
FÖRBJUDET i Telegram/n8n/webhooks/externa API:er:
  contact_person, contact_phone, contact_email,
  personal_number, name, email, phone, member_id,
  date_of_birth, address

TILLÅTET:
  deceased_name (behövs för memorial/program),
  church_id, case_id, status, package, date_of_death,
  ceremony_date, activity counts, KPI-aggregat
```

Om du skapar en webhook eller API-endpoint: **filtrera PII explicit**.
Se `_FUNERAL_API_PII_BLOCKED` i routes.py som exempel.

### 4. TDD — testet först

Skriv testet innan implementationen. Varje ny:
- Route → test i `tests/test_*.py`
- Port → test i `tests/test_*.py`
- Domänmodell → test av affärslogik
- Template → test av server-side data (inte HTML)

### 5. Autentisering

Alla admin-routes MÅSTE anropa `_require_session(request)`.
Alla API-endpoints MÅSTE verifiera token (session-cookie eller X-API-Token).
**Ingen route utan auth.**

### 6. Input-validering

- Alla POST-routes: `Form(...)` med typer
- Alla API-endpoints: Pydantic-modeller eller explicit validering
- Aldrig lita på klientdata

### 7. Ingen vendor-specifik konfiguration i kod

```
TILLÅTET:
  os.environ.get("FUNERAL_API_TOKEN")          # generiskt
  settings.funeral_api_token                     # via config-objekt

FÖRBJUDET:
  from google.cloud import secretmanager        # i routes/ports
  import boto3                                    # i routes/ports
```

## Namnkonventioner

- Paketnamn: **Svenska, beskrivande** (Enkel/Ceremoni/Komplett)
- Religiösa termer (ንጽሕና, ሐዘን, ተዝካር): BARA i ritualsammanhang, ALDRIG som produktnamn
- Filer: `snake_case.py`
- Klasser: `PascalCase`
- Portar: `*Port` (Protocol)
- Fakes: `Fake*` i `app/adapters/fake_*.py`

## Filstruktur per service

```
services/<service>/
├── app/
│   ├── api/
│   │   ├── routes.py      ← HTTP-routes (importerar BARA från ports)
│   │   └── deps.py        ← Dependency injection
│   ├── ports/
│   │   ├── *.py           ← Protocol-klasser (INGA vendor-imports)
│   ├── adapters/
│   │   ├── factory.py     ← ADAPTER_MODE → memory | production
│   │   ├── fake_*.py      ← In-memory för tester
│   │   └── *.py           ← Produktionsadaptrar (vendor-imports OK här)
│   ├── domain/
│   │   └── models.py      ← Dataklasser, affärslogik
│   ├── services/
│   │   └── *.py           ← Orchestrering (importerar BARA ports)
│   └── templates/
│       └── *.html         ← Jinja2 (auto-escaping aktivt)
└── tests/
    ├── conftest.py        ← Fixtures med alla fakes
    └── test_*.py          ← TDD-tester
```

## Vanliga fel som AI-verktyg gör

1. **Importerar httpx/requests direkt i routes** → Skapa en port istället
2. **Skickar PII till webhook** → Filtrera med blocked_fields
3. **Glömmer auth på ny route** → Lägg till `_require_session`
4. **Skapar ny fil utan test** → Skriv test först (TDD)
5. **Använder religiösa termer som produktnamn** → Svenska beskrivande namn
6. **Lägger vendor-specifik config i kod** → Använd env vars via settings
7. **Skippar att uppdatera conftest.py** → Alla nya ports behöver fake + DI-override
8. **Modifierar befintliga tester för att "fixa" sin implementation** → Fråga varför testet finns först

### 8. API-kontrakt — bryt aldrig befintliga fält

Om du ändrar en dataclass (FuneralCase, PendingSubmission, etc.):
- **Lägg till** fält fritt (med default-värde)
- **Ta ALDRIG bort** fält som andra services använder
- **Byt ALDRIG namn** på befintliga fält

CI-test `test_api_contracts.py` failar om ett kontraktsfält försvinner.

### 9. Beroenden — lägg inte till paket utan att tänka

- Lägg till i `requirements.txt` med `==` (exakt version)
- Använd ALDRIG: pycrypto, django, flask (banned)
- Fråga: "Behövs verkligen ett nytt paket, eller finns funktionen redan?"

### 10. Testtäckning — skriv alltid test

Varje ny modul i `app/` måste ha minst ett test.
CI-test `test_coverage_threshold.py` failar om täckningen < 60%.

## OWASP LLM Top 10 — checklista (2025)

Projektet använder Claude API i produktion (översättning, bidragsansökningar).
Dessa risker ska bevakas:

| # | Risk | Vår mitigation | Status |
|---|---|---|---|
| LLM01 | **Prompt Injection** | System-prompt i n8n, ej user-kontrollerbar | ✅ |
| LLM02 | **Insecure Output Handling** | Jinja2 auto-escaping, aldrig `safe`-filter | ✅ |
| LLM03 | **Training Data Poisoning** | Ej relevant (vi tränar ej egna modeller) | N/A |
| LLM04 | **Model Denial of Service** | Rate limiting på n8n workflows | ⚠️ |
| LLM05 | **Supply Chain** | test_dependency_safety.py, banned packages | ✅ |
| LLM06 | **Sensitive Info Disclosure** | Sanitizer profiles, pii_guard, blocked_fields | ✅ |
| LLM07 | **Insecure Plugin Design** | Inga plugins — direkt API-anrop via portar | ✅ |
| LLM08 | **Excessive Agency** | Human-in-the-loop (Telegram bot bekräftar alltid) | ✅ |
| LLM09 | **Overreliance** | AI-genererat granskas av människa innan publicering | ✅ |
| LLM10 | **Model Theft** | API-nyckel i Secret Manager, ej i kod | ✅ |

### Regler för AI-anrop i produktion

```
1. ALDRIG skicka RED-data till Claude API
   → Sanitizer profiles filtrerar INNAN anrop
   → pii_guard avvisar förbjudna fält med 422

2. ALLTID human-in-the-loop för AI-genererat innehåll
   → Bidragsansökningar: styrelsen granskar innan inskick
   → Översättningar: begravningsprogram godkänns av familj
   → Telegram-bot: bekräftelse innan publicering

3. ALDRIG lita på AI-output som fakta
   → AI-genererade siffror verifieras mot KPI-dashboard
   → Ambassad-dokumentation verifieras mot checklista

4. API-nycklar ENBART i Secret Manager
   → Aldrig i kod, .env-filer, Docker-images eller CLAUDE.md
```

### Slopsquatting-skydd (OWASP Supply Chain)

AI-verktyg kan hallucinera paketnamn. Innan du lägger till
ett pip-paket som en AI föreslagit:
1. Verifiera att det finns på pypi.org
2. Kontrollera nedladdningsantal (>10 000/mån)
3. Kontrollera GitHub-repo (stjärnor, senaste commit)
4. test_dependency_safety.py fångar banned packages

## Claude Code hooks (.claude/settings.json)

Hooks körs deterministiskt — till skillnad från CLAUDE.md
som är rådgivande. Tre hooks konfigurerade:

| Hook | Trigger | Vad den gör |
|---|---|---|
| PreToolUse | Före Write/Edit | Blockerar skrivning till .env, secrets, migrations |
| PostToolUse | Efter Write/Edit | Skannar efter vendor lock-in |
| Stop | Innan task rapporteras klar | Kör alla guard-tester |

## Hur du verifierar att din kod är OK

```bash
# Från kyrk-projekt/
python -m pytest tests/ --tb=short                              # projektguards (63 tester)
python -m pytest services/admin-web/tests/ --tb=short           # admin-web (161 tester)
cd frontend/member-portal && node tests/test_all_pages.js       # frontend

# Eller allt på en gång:
python -m pytest tests/ services/admin-web/tests/ --tb=short    # 224 tester
```

Alla måste vara gröna innan du committar.

## CI-tester som skyddar projektet

| Test | Vad den fångar | Antal |
|---|---|---|
| `test_no_vendor_lockin.py` | Vendor-imports i routes/ports | 2 |
| `test_architecture_guard.py` | Auth, ports, fakes, DI, PII | 5 |
| `test_project_security_guard.py` | Samma sak × alla 5 services + frontend | 33 |
| `test_api_contracts.py` | Borttagna/omdöpta API-fält | 12 |
| `test_dependency_safety.py` | Banned/osäkra paket | 11 |
| `test_coverage_threshold.py` | Kod utan tester | 5 |
| `test_docs_freshness.py` | Odokumenterade features | 7 |
| **Total** | | **75 guard-tester** |
