# 17 — Granskningsberedskap

Vad vi visar upp, var det finns, och vem som ansvarar — när IMY,
SST, Skatteverket, eller en extern revisor knackar på dörren.

## TL;DR för styrelsen

Om ni får ett brev eller samtal från en myndighet som vill granska:

1. **Panika inte.** Vi har allt dokumenterat.
2. Öppna denna fil och följ checklistan nedan.
3. Allt som är markerat ✅ AUTO kan genereras direkt från plattformen.
4. Allt som är markerat 📄 DOC finns som fil i repot.
5. Allt som är markerat ✋ MANUAL kräver att en människa tar fram det.

---

## Checklista per granskande myndighet

### IMY (Integritetsskyddsmyndigheten) — GDPR-granskning

IMY granskar att ni behandlar personuppgifter lagligt. De frågar
efter dessa dokument:

| # | Dokument | Status | Var finns det |
|---|---|---|---|
| 1 | **Registerförteckning** (Art. 30) | 📄 DOC | `docs/governance/gdpr-register.md` |
| 2 | **Integritetspolicy** (Art. 13) | ✅ AUTO | `kyrka-portal.pages.dev/privacy.html` (sv + am) |
| 3 | **Samtyckes-hantering** (Art. 7) | ✅ AUTO | intake-formuläret: checkbox + `consent_timestamp` i Firestore |
| 4 | **Tekniska skyddsåtgärder** (Art. 32) | 📄 DOC | `docs/05-security-principles.md` + `docs/16-defense-in-depth.md` |
| 5 | **Krypteringsbeskrivning** | 📄 DOC | `services/membership-service/README.md` → "Least privilege (production IAM)" |
| 6 | **Radering-process** (Art. 17) | 📄 DOC | `docs/governance/policies.md` → "Deletion requests" |
| 7 | **Underbiträdesregister** (Art. 28) | 📄 DOC | `docs/governance/gdpr-register.md` → "Underbiträden" |
| 8 | **DPA med Google Cloud** | ✋ MANUAL | Signeras i GCP Console → Compliance → DPA |
| 9 | **DPA med PropelAuth** | ✋ MANUAL | Begärs via PropelAuth support |
| 10 | **DPIA** (Art. 35, om tillämpligt) | 📄 DOC | `docs/governance/gdpr-register.md` → "Konsekvensbedömning" |
| 11 | **Audit trail** — bevis på åtkomstkontroll | ✅ AUTO | Firestore `audit_events` collection |
| 12 | **Bevis att AI inte ser PII** | ✅ AUTO + 📄 DOC | `automation/openclaw/sanitizer/profiles.json` + `reporting-service/app/domain/pii_guard.py` + nightly CI-test |

**Hur ni genererar bevisen:**

```bash
# 1. Registerförteckning — redan en fil, skriv ut den
cat docs/governance/gdpr-register.md

# 2. Integritetspolicy — live på webben
open https://kyrka-portal.pages.dev/privacy.html

# 3. Samtyckes-bevis — visa intake-formuläret och Firestore
#    (kräver GCP-deploy för att visa riktig data)
curl -s https://api.kyrka.se/intake | python3 -m json.tool

# 4. Tekniska skyddsåtgärder — visa koden
#    IMY vill se: kryptering, åtkomstkontroll, zonindelning
cat services/membership-service/app/adapters/kms_encryption.py
cat infra/terraform/iam_bindings.tf

# 5. Audit trail — visa att åtkomst loggas
#    (kräver GCP-deploy)
gcloud firestore query --collection-group=audit_events --limit=10

# 6. PII-guard — visa att den avvisar personnummer
cd services/reporting-service
python3 -c "
from app.domain.pii_guard import assert_no_pii, PIIRejected
try:
    assert_no_pii({'first_name': 'Anna'})
except PIIRejected as e:
    print(f'BLOCKED: {e}')
print('Guard is active.')
"

# 7. Sanitizer — visa att den stoppar PII innan AI
python3 automation/openclaw/import/sanitize.py yellow-only \
  /tmp/test-payload-with-pii.json
# → REJECT: blocked pattern in key at $.first_name

# 8. Nightly CI — visa att PII-tester körs varje natt
cat .github/workflows/nightly.yml | grep -A5 "pii-sanitizer"
```

### SST (Myndigheten för stöd till trossamfund) — bidragsvillkor

SST granskar att ni uppfyller villkoren för organisationsstöd.

| # | Dokument | Status | Var |
|---|---|---|---|
| 1 | **Verksamhetsberättelse** | ✅ AUTO | admin-web `/kpi` → generera monthly/quarterly rapport |
| 2 | **Medlemsantal** | ✅ AUTO | `GET /members/stats/summary` → `total`, `active` |
| 3 | **Ekonomisk redovisning** | ✋ MANUAL | Fortnox (inte wired ännu) |
| 4 | **Stadgar** | ✋ MANUAL | Kyrkans stadgar (PDF, inte i plattformen) |
| 5 | **Demokratisk organisation** | ✋ MANUAL | Styrelseprotokoll |
| 6 | **Aktivitetsrapport** | ✅ AUTO | `GET /activities/export/period?start=...&end=...` |
| 7 | **Åldersfördelning** | ✅ AUTO | `age_band_counts` i varje aktivitet |

**Hur ni genererar SST-underlaget:**

```bash
# Verksamhetsberättelse (KPI-rapport med siffror)
# Admin-web → KPI → period: 2025 → Generera

# Medlemsantal
curl -H "Authorization: Bearer $TOKEN" \
  https://api.kyrka.se/members/stats/summary

# Aktivitetsrapport (alla aktiviteter senaste året)
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.kyrka.se/activities/export/period?start=2025-01-01&end=2025-12-31"
```

### Skatteverket — gåvokvitto och ekonomi

| # | Dokument | Status | Var |
|---|---|---|---|
| 1 | **Organisationsnummer** | ✅ AUTO | 802492-9237 visas på donate.html och privacy.html |
| 2 | **Gåvokvitto-underlag** | ⚠️ Manuellt i MVP | Swish-transaktioner hanteras av banken |
| 3 | **Bokföring** | ✋ MANUAL | Fortnox |

### Kommun — verksamhetsbidrag

| # | Dokument | Status | Var |
|---|---|---|---|
| 1 | **Aktivitetsrapport** | ✅ AUTO | reporting-service export |
| 2 | **Deltagarantal per aktivitetstyp** | ✅ AUTO | `participants_by_type` i monthly rapport |
| 3 | **Åldersfördelning** | ✅ AUTO | `participants_by_age_band` |
| 4 | **Lokalbeskrivning** | ✋ MANUAL | |

---

## Vid en dataintrångsincident (Art. 33/34)

Om ni misstänker att personuppgifter läckt:

### Tidslinje (72-timmarsregeln)

| Tid | Åtgärd | Vem |
|---|---|---|
| T+0 | Upptäckt — stoppa pågående läckage | On-call (se `docs/13-runbook.md`) |
| T+1h | Bedöm omfattning — vilka data, hur många drabbade | Admin + on-call |
| T+4h | Dokumentera i `incidents/YYYY-MM-DD-*.md` | Admin |
| T+24h | Beslut: behöver IMY meddelas? (Art. 33: ja om risk) | Styrelsen |
| T+48h | Formulera anmälan till IMY om nödvändigt | Styrelsen + DPO |
| T+72h | **Deadline:** anmälan till IMY om det bedöms som en risk | Styrelsen |
| T+1v | Informera drabbade om hög risk (Art. 34) | Styrelsen |
| T+2v | Postmortem + åtgärdsplan | Teamet |

### Vad anmälan till IMY ska innehålla

1. Typ av intrång (obehörig åtkomst, dataförlust, oavsiktlig publicering)
2. Kategorier av drabbade (medlemmar, barn, besökare)
3. Ungefärligt antal drabbade
4. Beskrivning av möjliga konsekvenser
5. Åtgärder som vidtagits eller planeras
6. Kontaktuppgifter till er kontaktperson

### Vad plattformen ger er automatiskt vid incident

```bash
# 1. Audit trail — vem gjorde vad, när
gcloud firestore query --collection-group=audit_events \
  --filter='at>="2025-06-01"' --limit=100

# 2. PII-guard-loggar — avvisade payloads (hash, inte klartext)
gcloud logging read 'textPayload:"PIIRejected"' --limit=20

# 3. Sanitizer-larm — misslyckade n8n-körningar
# (n8n UI → Executions → filter: failed)

# 4. Service-loggar — felsökning
gcloud run services logs read membership-service --limit=100

# 5. Terraform state — vilka IAM-bindings som fanns vid tidpunkten
terraform state show google_project_iam_member.membership_service_firestore
```

---

## Transparensrapport — vad vi proaktivt kan publicera

Följande kan publiceras årligen (på hemsidan eller i verksamhetsberättelsen)
för att visa transparens utan att vänta på en granskning:

| Uppgift | Källa | Frekvens |
|---|---|---|
| Antal aktiva medlemmar per kyrka | `/members/stats/summary` | Kvartalsvis |
| Antal aktiviteter + deltagare | reporting-service monthly | Månatligt |
| Antal söndagsskole-certifikat utfärdade | certificate-service | Kvartalsvis |
| Antal bidrag sökta / beviljade / avslagna | grant tracker | Kvartalsvis |
| Tekniska skyddsåtgärder (övergripande) | docs/security + defense-in-depth | Årligen |
| Inga dataintrång rapporterade (eller: N st) | incidents/ | Årligen |
| PII-guard: antal avvisade payloads senaste kvartalet | nightly CI log | Kvartalsvis |
| AI-användning: vilken data som sänds, vad som blockeras | prompt-redlines.md | Årligen |

---

## Checklista: årsvis GDPR-underhåll

Gör dessa en gång per år (lämpligen i januari):

- [ ] Uppdatera registerförteckningen (`docs/governance/gdpr-register.md`)
- [ ] Granska integritetspolicyn (`privacy.html`) — stämmer texten fortfarande?
- [ ] Granska underbiträdesregistret — har vi lagt till nya tjänster?
- [ ] Kör åtkomstgranskning — har alla admins/pastorer fortfarande rätt roller?
- [ ] Verifiera att DPA:er med GCP och PropelAuth är aktiva
- [ ] Kör `./scripts/local-ci.sh` → verifiera att pii_guard + sanitizer fortfarande avvisar PII
- [ ] Granska `incidents/` — finns det olösta follow-ups?
- [ ] Uppdatera DPIA om nya behandlingar tillkommit
- [ ] Verifiera att retention policy (30d pending, 2y audit) efterlevs
- [ ] Publicera transparensrapport på hemsidan

---

## Sammanfattning: vad vi visar vid granskning

```
IMY ringer → öppna docs/17-audit-readiness.md → följ checklistan
SST ringer → admin-web → KPI + /members/stats/summary + grant tracker
Skatteverket ringer → Fortnox + donate.html org.nr
Kommun ringer → reporting-service export + deltagarantal

Dataintrång → docs/13-runbook.md → 72h-processen ovan
```

Allt som går att automatisera ÄR automatiserat. Allt som kräver
en människa ÄR dokumenterat med exakt vem som gör vad.
