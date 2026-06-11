# Issue: Migrera autentisering från PropelAuth till Zitadel Cloud (SaaS)

> **Status (2026-06-11):** Kod-migreringen är **genomförd** — `ZitadelAuthAdapter` + `JWTSessionAdapter` wire:as i production via `factory.py` i samtliga services; ingen levande PropelAuth-kod kvar (endast inaktuella docstrings). **MEN** den aktiva instansen ligger i Zitadels **US-region på gratisnivå** (`kyrk-auth-oqvxjf.us1.zitadel.cloud`), inte EU/Schweiz. Det är ett medvetet, kostnadsmotiverat avsteg under uppbyggnadsfasen — se **[ADR-017](../../docs/14-architecture-decisions.md)**. **Kvarstår innan stängning:** (1) flytta till EU/CH-region före skarp persondata/produktion, (2) fixa `ssl.CERT_NONE` i `JWTSessionAdapter` före deploy, (3) rensa inaktuella PropelAuth-docstrings.

## Kategori
- [x] Säkerhet / Datasuveränitet (Security / Sovereignty)
- [x] Refaktorering / Arkitektur (Refactoring / Architecture)
- [ ] Felrättning (Bug)

## Beskrivning
Då PropelAuth är ett amerikanskt SaaS-bolag medför det potentiella GDPR- och FISA-relaterade suveränitetsrisker (US Cloud Act) för medlemmars inloggningsuppgifter och administratörsaktivitet. Eftersom vi vill ha en molntjänst utan operationell driftsbörda (vilket utesluter självvärdad Keycloak), har vi beslutat att migrera autentisering och multi-tenant RBAC till **Zitadel Cloud** (SaaS baserat i Schweiz/EU).

Zitadel Cloud erbjuder:
- 100 % EU- och schweizisk datalagring (GDPR-kompatibel och fri från amerikansk jurisdiktionsrisk).
- Inbyggt stöd för multi-tenancy (Zitadel "Organizations") som matchar vår kyrko-modell.
- Generös gratisnivå (25 000 förfrågningar per månad).
- Ingen driftbörda eller databashantering för vårt team.

Tack vare vår hexagonala arkitektur (`AuthPort`) kan vi genomföra denna migration helt inom adapterlagret.

## Arbetsmoment

### 1. Konfigurera Zitadel Cloud
- Skapa ett Zitadel Cloud-konto (instans).
- Definiera roller (`admin`, `pastor`, `secretary`, `viewer`) som matchar vår nuvarande RBAC-modell.
- Konfigurera scopes och claims för att exponera organisationer och roller i JWT-tokens.
- Skapa API-klienter (Client ID) för våra mikrotjänster.

### 2. Implementera Zitadel-adapter i Backend
- Skapa en ny `ZitadelAuthAdapter` som implementerar `AuthPort` i följande tjänster:
  - `services/membership-service/app/adapters/zitadel_auth.py`
  - `services/membership-intake/app/adapters/zitadel_auth.py`
  - `services/reporting-service/app/adapters/zitadel_auth.py`
- Adaptern ska hämta Zitadels JWKS (JSON Web Key Set) från `https://<instance>.zitadel.cloud/oauth/v2/keys` och verifiera samt avkoda inkommande JWT-tokens (Bearer token i `Authorization`-headern).
- Använd ett standardsäkerhetsbibliotek (t.ex. `pyjwt` eller `authlib`) istället för ett proprietärt SDK för att undvika vendor lock-in.
- Extrahera `user_id`, `church_id` (motsvarande Zitadels organization ID) och `role` från token-claims.

### 3. Uppdatera Factory & Miljövariabler
- Uppdatera `app/adapters/factory.py` i alla tjänster för att instansiera `ZitadelAuthAdapter` vid produktion (eller baserat på `ADAPTER_MODE` / nya miljövariabler).
- Byt ut miljövariablerna i Kubernetes/Cloud Run-miljön:
  - Ta bort: `PROPELAUTH_URL`, `PROPELAUTH_API_KEY`
  - Lägg till: `ZITADEL_ISSUER_URL`, `ZITADEL_CLIENT_ID`
- Uppdatera GCP Secret Manager så att nödvändiga Zitadel-hemligheter lagras och hämtas på samma sätt.

### 4. Ta bort PropelAuth-beroenden
- Ta bort `propelauth-fastapi` från `requirements.txt` i alla berörda mikrotjänster.
- Radera de gamla filerna `propelauth_auth.py` från adaptrarna.
- Uppdatera `FakeAuthAdapter` om det behövs för att simulera Zitadel-tokens under lokala tester (eller behåll befintlig då den är oberoende av specifik SaaS-leverantör).

### 5. Dokumentationsuppdateringar
- Uppdatera operationsmanualen (`docs/12-operations.md`) och arkitekturöversikten.
- Uppdatera instruktionerna för incidenthantering (användarblockering och token-rotation).

## Verifieringsplan
- **Automatiska tester**: Kör `make test` för att säkerställa att `FakeAuthAdapter` fortfarande fungerar utan att krascha och att alla 244 Python-tester passerar lokalt.
- **Integrationstester**: Skapa en testinstans i Zitadel Cloud och verifiera framgångsrik inloggning och token-verifiering via en test-klient.
- **Rollefterlevnad**: Verifiera att obehöriga anrop till RED-zonen blockeras och att behöriga släpps igenom med rätt roll-scope.
