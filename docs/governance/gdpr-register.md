# GDPR Registerförteckning (Art. 30)

Personuppgiftsansvarig: Abune Tekle Haymanot Etiopiska Ortodoxa Tewahedo Kyrkan
Org.nr: 802492-9237
Adress: Saltsjö-Boo, Nacka kommun

## Behandlingsregister

### 1. Medlemsregistrering (membership-intake + membership-service)

| Fält | Värde |
|---|---|
| **Ändamål** | Registrera nya medlemmar i församlingen |
| **Kategorier av registrerade** | Vuxna medlemmar, barn (med föräldrasamtycke) |
| **Kategorier av personuppgifter** | Förnamn, efternamn, telefon, e-post, personnummer, kyrkotillhörighet |
| **Rättslig grund** | Samtycke (Art. 6.1.a) med explicit checkbox och tidsstämpel |
| **Känsliga uppgifter** | Religiös tillhörighet (Art. 9.2.d — behandling av ideell förening med religiöst syfte) |
| **Mottagare** | Kyrkans admin (pastor, sekreterare, styrelse) via PropelAuth RBAC |
| **Tredjelandsöverföring** | Nej — all data i GCP europe-north1 (Finland) |
| **Lagringstid** | Aktiva medlemmar: tills radering begärs. Pending (ej godkänd): 30 dagar. |
| **Tekniska skyddsåtgärder** | KMS-kryptering av personnummer, TLS i transit, per-service IAM, audit trail |
| **System** | membership-intake (RED), membership-service (RED) |

### 2. Dopcertifikat och kyrkliga handlingar (certificate-service)

| Fält | Värde |
|---|---|
| **Ändamål** | Utfärda och verifiera digitala certifikat (dop, vigsel, söndagsskola) |
| **Kategorier av registrerade** | Medlemmar som tar emot kyrkliga handlingar |
| **Kategorier av personuppgifter** | Certifikat-ID (UUID), member_id (referens), certifikattyp, utfärdandedatum, kyrkans namn |
| **Rättslig grund** | Berättigat intresse (Art. 6.1.f) — kyrkans uppgift att dokumentera handlingar |
| **Mottagare** | Utfärdaren (admin/pastor). Publik verifiering visar BARA typ/datum/kyrka/status — aldrig identitet. |
| **Tredjelandsöverföring** | Nej |
| **Lagringstid** | Permanent (certifikat återkallas, inte raderas — historisk integritet) |
| **Tekniska skyddsåtgärder** | UUID-baserade ID:n (ej sekventiella), verifiering utan identitetsläckage |
| **System** | certificate-service (RED) |

### 3. Aktivitetsspårning (reporting-service)

| Fält | Värde |
|---|---|
| **Ändamål** | Aggregerad statistik för KPI, bidragsrapporter, styrelserapporter |
| **Kategorier av registrerade** | Inga — enbart anonyma aggregat |
| **Kategorier av personuppgifter** | INGA personuppgifter. Bara: deltagarantal, åldersband, aktivitetstyp, datum, plats. |
| **Rättslig grund** | Berättigat intresse (Art. 6.1.f) |
| **PII-skydd** | pii_guard avvisar varje payload med personnummer, namn, e-post eller telefon (HTTP 422) |
| **Tredjelandsöverföring** | Nej |
| **System** | reporting-service (YELLOW) |

### 4. AI-assisterad analys (OpenClaw via n8n)

| Fält | Värde |
|---|---|
| **Ändamål** | Generera kvartalsanalyser, bidragsunderlag, innehållsförslag |
| **Kategorier av personuppgifter** | INGA — sanitizer validerar att enbart aggregerad data når API:et |
| **Mottagare** | Anthropic API (Claude) — zero-retention konfigurerat |
| **Tredjelandsöverföring** | Data skickas till Anthropic API (US-baserat). ENBART anonyma aggregat. Inga personuppgifter. |
| **Skyddsåtgärder** | Sanitizer profiler (whitelist), pii_guard, system-prompt instruktion, human-in-the-loop |
| **System** | automation/openclaw (GREEN), n8n |

### 5. Webbplats och Wi-Fi-portal (member-portal, wifi-intake-portal)

| Fält | Värde |
|---|---|
| **Ändamål** | Informera om aktiviteter, möjliggöra medlemsregistrering |
| **Kategorier av personuppgifter** | Inga — webbsidorna samlar INTE in data (inga kakor, ingen spårning, inga analysverktyg) |
| **Rättslig grund** | Ej tillämpligt — ingen personuppgiftsbehandling |
| **Tredjelandsöverföring** | Cloudflare CDN (EU edge). Ingen persondata cachas. |
| **System** | frontend/member-portal (GREEN), frontend/wifi-intake-portal (GREEN) |

### 6. Donationshantering (donate.html)

| Fält | Värde |
|---|---|
| **Ändamål** | Ta emot gåvor via Swish |
| **Kategorier av personuppgifter** | Inga — Swish-betalningen hanteras av Swish/banken, inte av vår plattform |
| **Rättslig grund** | Ej tillämpligt — vi lagrar inga betalningsuppgifter |
| **System** | frontend/member-portal/donate.html (GREEN) |

## Underbiträden (databehandlare)

| Underbiträde | Syfte | DPA | Plats |
|---|---|---|---|
| Google Cloud Platform | Hosting, Firestore, KMS, BigQuery | Googles standard-DPA (behöver signeras) | EU (europe-north1) |
| PropelAuth | RBAC / autentisering | PropelAuth DPA (behöver signeras) | EU/US (enbart admin-email) |
| Cloudflare | CDN, DDoS-skydd | Cloudflare DPA (automatisk vid konto) | Global edge (ingen persondata) |
| Anthropic | AI-analys via API | Anthropic DPA (zero-retention) | US (enbart anonyma aggregat) |

## Konsekvensbedömning (DPIA)

En fullständig DPIA (Art. 35) rekommenderas för:
- Behandling av personnummer (känslig uppgift i svensk kontext)
- Barndata i söndagsskolemodulen

Vår bedömning: risken är låg tack vare:
- KMS-kryptering av personnummer
- Minimal datalagring (6 fält)
- Redaction efter godkännande
- Zonindelning som förhindrar PII-läckage
- Audit trail på varje skrivning

## Vad vi visar vid en IMY-granskning

1. **Denna registerförteckning** (Art. 30)
2. **Integritetspolicyn** på hemsidan (Art. 13) — privacy.html på sv + am
3. **Samtyckes-hanteringen** — intake-formuläret med checkbox + timestamp (Art. 7)
4. **Tekniska skyddsåtgärder** — KMS, CMEK, pii_guard, sanitizer, per-service IAM (Art. 32)
5. **Audit trail** — Firestore audit_events collection med actor/action/timestamp (Art. 5.2)
6. **Retention policy** — docs/governance/policies.md (Art. 5.1.e)
7. **Defense-in-depth policy** — docs/16-defense-in-depth.md (Art. 25 — data protection by design)
8. **Radering-process** — membership-service deactivate + 30-dagars retention (Art. 17)
9. **Underbiträdesregister** — tabellen ovan (Art. 28)
10. **Kodbasen** — open source, granskningsbar, TDD-testad (Art. 25 — transparency)
