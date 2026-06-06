# Utvecklare — Onboarding

Välkommen till kyrk-projekt. Här är allt du behöver för att komma igång.

## Repo

- **GitHub:** https://github.com/Compuute/.github
- **Branch:** `claude/kyrk-projekt-mvp-foundation-ofWAZ`
- **Live site:** https://kyrka-portal.pages.dev
- **Issues (backlog):** https://github.com/Compuute/.github/issues

## Snabbstart (5 minuter)

```bash
git clone https://github.com/Compuute/.github.git
cd .github/kyrk-projekt

# Installera beroenden
pip install -r services/admin-web/requirements.txt

# Kör alla tester (224 st)
python -m pytest tests/ services/admin-web/tests/ --tb=short

# Kör frontend-tester
cd frontend/member-portal && node tests/test_all_pages.js
```

Om allt är grönt är du redo.

## Vad som finns — MVP

### Publik hemsida (8 sidor, LIVE)

| Sida | URL | Funktion |
|---|---|---|
| Startsida | [kyrka-portal.pages.dev](https://kyrka-portal.pages.dev) | Aktiviteter, meddelanden, snabblänkar |
| Bli medlem | /intake | Registrering med GDPR-consent |
| Ge en gåva | /donate | Swish + bankgiro |
| Gudstjänst live | /live | YouTube-embed |
| Begravning | /funeral | 6 paket, hemtransport, Fonus-jämförelse |
| Om oss | /about | Kyrkans historia, Tewahedo-tron |
| Kontakt | /contact | Adress, telefon, tider, Telegram |
| Integritetspolicy | /privacy | GDPR sv + am |

Alla sidor: tvåspråkiga (svenska + amhariska), PWA, offline-stöd, inga kakor.

### Backend-services (5 st, byggda, ej deployade)

| Service | Vad den gör | Tester |
|---|---|---|
| membership-intake | Publik registrering + admin-godkännande | 37 |
| membership-service | Medlem-CRUD + KMS-kryptering + audit | 31 |
| certificate-service | 10 certifikattyper (dop, vigsel, söndagsskola) | 39 |
| reporting-service | KPI, ROI, PII-guard | 36 |
| admin-web | Allt admin: intake, certifikat, KPI, bidrag, begravning | 161 |

### Admin-funktioner (admin-web)

| Funktion | URL |
|---|---|
| Dashboard | `/` |
| Godkänn medlemmar | `/submissions` |
| Utfärda certifikat | `/certificates/new` |
| KPI-dashboard | `/kpi` |
| Bidragstracker (12 bidrag) | `/grants` |
| Begravningsärenden | `/funerals` |
| Hemtransport-tracker | `/funerals/{id}` |
| Content-editor (sv+am) | `/content-editor` |
| GDPR-rapport | `/audit` |

### Säkerhet

- 224 automatiska tester
- 75 guard-tester (vendor lock-in, PII, auth, arkitektur)
- OWASP LLM Top 10 checklista
- Zone-modell: RED (PII) / YELLOW (aggregat) / GREEN (publik)
- Alla POST-routes kräver autentisering
- Inga vendor-imports i routes/ports (CI-enforced)

## Arkitektur

```
frontend/member-portal/     ← 8 HTML-sidor (Cloudflare Pages)
services/
  admin-web/                ← Admin UI (FastAPI + Jinja2)
  membership-intake/        ← Publik intake (FastAPI)
  membership-service/       ← Medlems-CRUD + KMS (FastAPI)
  certificate-service/      ← Certifikat (FastAPI)
  reporting-service/        ← KPI + PII-guard (FastAPI)
automation/
  n8n/workflows/            ← 10 workflow-definitioner
  openclaw/                 ← 6 AI-promptmallar
  grants/database.json      ← 12 bidragskällor
infra/terraform/            ← GCP-infrastruktur
docs/                       ← 30+ docs
tests/                      ← Projekt-övergripande tester
```

### Ports/Adapters-mönster (VIKTIGT)

Varje service följer hexagonal arkitektur:

```
app/api/routes.py       ← HTTP (importerar BARA ports)
app/ports/*.py          ← Protocol-interfaces (INGA vendor-imports)
app/adapters/fake_*.py  ← In-memory för tester
app/adapters/*.py       ← Produktion (vendor-imports OK här)
app/adapters/factory.py ← ADAPTER_MODE=memory|production
```

**Regeln:** routes och ports importerar ALDRIG httpx, anthropic, google etc direkt. CI failar om du bryter detta.

## Docs att läsa

| Prio | Dokument | Tid |
|---|---|---|
| 1 | `AI-RULES.md` | 10 min — regler för AI-assisterad utveckling |
| 2 | `CONTRIBUTING.md` | 10 min — PR-flöde, TDD, review-krav |
| 3 | `docs/10-getting-started.md` | 15 min — setup |
| 4 | `docs/11-development-guide.md` | 20 min — adapter-mönster, ny feature |
| 5 | `docs/01-architecture-red-yellow-green.md` | 10 min — zonmodellen |

## Hur du bidrar

1. Kolla [issues](https://github.com/Compuute/.github/issues) — välj en
2. Skapa branch: `git checkout -b feat/kort-beskrivning`
3. Skriv test FÖRST (TDD)
4. Implementera
5. Kör `python -m pytest tests/ services/admin-web/tests/` — allt grönt
6. Push + PR

## Vad som INTE ska göras

- Pusha direkt till main
- Importera vendor-bibliotek i routes/ports
- Skicka PII till webhooks/Telegram
- Skapa route utan auth
- Lägga till dependency utan att fråga
- Committa secrets

Se `AI-RULES.md` för alla 10 regler.

## Kontakt

Frågor? Öppna en [Discussion](https://github.com/Compuute/.github/discussions) eller kontakta Daniel.
