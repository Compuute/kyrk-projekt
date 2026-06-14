# 32 — Driftöverlämning och portabilitet: bort från persondependens

> Hur hela plattformen flyttas till **kyrkans egna konton och egna API-nycklar**
> så att driften inte hänger på någon enskild person (idag: Daniels GCP-projekt,
> Anthropic-konto, Cloudflare och Zitadel). Skrivet så att stegen kan
> **automatiseras av AI-agenter** där det är möjligt — det som måste göras av en
> människa är uttryckligen utmärkt. Komplement till
> [29-identitets-och-iam-principer.md](29-identitets-och-iam-principer.md),
> [12-operations.md](12-operations.md) och
> [28-agentisk-driftmodell.md](28-agentisk-driftmodell.md).

## 1. Princip

1. **Ingen persondependens.** Inget får kräva ett *personligt* konto. All drift
   sker via tjänstekonton, pipelines och hemligheter i Secret Manager — aldrig en
   namngiven persons nyckel.
2. **Allt som kod.** Infrastruktur (Terraform), deploy (GitHub Actions) och konfig
   (env/Secret Manager, Cloudflare KV) är versionerat. En ny miljö reproduceras
   genom att köra koden mot nya konton — inte genom manuella klick.
3. **Agent-körbart där det går.** Steg som bara flyttar konfiguration/hemligheter
   eller kör Terraform/deploy kan en agent göra. Steg som kräver att *äga ett
   konto, acceptera villkor eller koppla betalning* är irreducibelt mänskliga.
4. **Två driftmodeller stöds** (se §5): (A) vi driftar åt kyrkan, eller (B) kyrkan
   driftar själv i sina egna konton. Skillnaden är *vem som äger kontona* — koden
   är identisk.

## 2. Ägarskapsmatris — vad som måste bytas

Allt nedan pekar idag mot operatörens (Daniels) konton. Vid överlämning byts
ägaren till kyrkans egna. "Agent?" = kan en AI-agent utföra bytet givet att en
människa redan skapat mål-kontot.

| Resurs | Var den bor idag | Hur den byts | Agent? |
|---|---|---|---|
| **GCP-projekt** `kyrk-projekt` (+ billing) | Operatörens GCP-org | Skapa nytt projekt i kyrkans org, koppla billing | 🧑 Människa (billing/ToS) |
| **Terraform state-bucket** `kyrk-projekt-tfstate` | GCS i projektet | Skapas out-of-band i nya projektet (se 12-operations) | 🤖 Agent (gcloud/script) |
| **WIF-provider + sa-deployer/sa-terraform** | GCP IAM | `terraform apply` skapar dem; WIF-poolen kopplas till GitHub-repot | 🤖 Agent |
| **Runtime-tjänstekonton** (`sa-admin-web`, `sa-membership-*` …) | GCP IAM | Skapas av Terraform | 🤖 Agent |
| **Secret Manager-hemligheter** | GCP Secret Manager | Skapas av Terraform; **värden** läggs in separat (se §3) | delvis 🤖 |
| `anthropic-api-key` | Operatörens Anthropic-org (`dd.memo@gmail.com`) | Kyrkans egen Anthropic-org + nyckel → ny secret-version | 🧑 skapa nyckel, 🤖 lägg in |
| `zitadel-client-secret` | Zitadel `kyrk-auth-oqvxjf` | Kyrkans egen Zitadel-tenant + client | 🧑 tenant, 🤖 lägg in |
| `admin-notify-webhook` | Operatörens webhook (Telegram/n8n) | Kyrkans egen webhook-URL | delvis 🤖 |
| `fortnox-client-id` / `fortnox-client-secret` | Fortnox-app (bokföring) | Kyrkans Fortnox-integration | 🧑 |
| **GitHub Actions secrets** (`GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA`, `CLOUDFLARE_API_TOKEN`, `BREVO_API_KEY`, `RECEIPT_FROM_EMAIL`, `ADMIN_NOTIFY_WEBHOOK`, `AGENT_CLIENT_ID`, `AGENT_CLIENT_SECRET`) | GitHub repo settings | Sätts om till nya miljöns värden | 🤖 (via `gh secret set`) |
| **Cloudflare** (Pages-projekt `kyrka-portal`, KV `kyrka_content`, API-token) | Operatörens Cloudflare-konto | Kyrkans Cloudflare-konto; ny API-token med Workers KV: Edit | 🧑 konto, 🤖 token/secret |
| **Zitadel** (org, projekt-roller, OIDC-clients) | `kyrk-auth-oqvxjf.us1.zitadel.cloud` | Kyrkans egen Zitadel-tenant | 🧑 tenant, 🤖 client-konfig via API |
| **Anthropic** (org + billing) | Operatörens org | Kyrkans egen org + betalning + spend-limit | 🧑 |
| **Brevo** (kvittomail), **Swish**, **Telegram-bot** | Operatörens/kyrkans konton | Kyrkans egna konton/nummer | 🧑 |
| **Domän / DNS** | Cloudflare DNS | Kyrkans domän pekas om | 🧑 |

> **Tumregel:** allt som är "skapa ett konto / koppla pengar / acceptera villkor"
> är människans 5–10 minuters jobb per leverantör. Allt däremellan — Terraform,
> service accounts, secret-versioner, deploy, Cloudflare-konfig — kan en agent
> köra mot de nya kontona utan att någon person sitter i loopen.

## 3. Migreringsrunbook (per domän)

Ordning: GCP-grund → hemligheter → auth → edge → integrationer → verifiering.

### 3.1 GCP-grund 🧑+🤖
1. 🧑 Skapa kyrkans GCP-projekt + koppla billing.
2. 🤖 Skapa state-bucket out-of-band (`gsutil mb`/script enligt
   [12-operations.md](12-operations.md)) och aktivera object versioning.
3. 🧑 Skapa `sa-terraform` + WIF-koppling till GitHub-repot (engångs-bootstrap,
   se 12-operations §bootstrap) — eller låt en agent göra det med ett tillfälligt
   admin-token.
4. 🤖 Sätt GitHub-secrets `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`,
   `GCP_DEPLOYER_SA` till nya värden.
5. 🤖 Kör **terraform-apply** — skapar service accounts, IAM, Firestore, KMS,
   Secret Manager-containrar, Pub/Sub m.m.

### 3.2 Hemlighetsvärden 🧑(skapa)+🤖(lägg in)
För varje secret skapar Terraform *containern*; **värdet** läggs in separat:
```bash
printf '%s' '<värde>' | gcloud secrets versions add <namn> \
  --data-file=- --project=<NYTT_PROJEKT>
```
Gäller: `anthropic-api-key`, `zitadel-client-secret`, `admin-notify-webhook`,
`fortnox-client-id`, `fortnox-client-secret`. (Människan tar fram nyckeln hos
respektive leverantör; agenten lägger in den.)

### 3.3 Auth (Zitadel) 🧑+🤖
1. 🧑 Skapa kyrkans Zitadel-tenant, projekt och roller (`admin`/`pastor`/
   `editor`/`viewer`), samt en org per kyrka.
2. 🤖 Uppdatera `ZITADEL_ISSUER_URL` och `ZITADEL_CLIENT_ID` (env i `deploy.yml`)
   samt org-id→slug-mappningen i
   `services/membership-intake/app/domain/churches.py`.
3. 🤖 Lägg `zitadel-client-secret`-värdet i Secret Manager.

### 3.4 Edge (Cloudflare) 🧑+🤖
1. 🧑 Skapa kyrkans Cloudflare-konto; skapa Pages-projekt + KV-namespace.
2. 🧑 Skapa API-token med **Workers KV: Edit** (och Pages om CI deployar).
3. 🤖 Sätt `CLOUDFLARE_API_TOKEN` som GitHub-secret; uppdatera `wrangler.toml`
   (KV-namespace-id) och peka om domänen.

### 3.5 Integrationer 🧑
Anthropic-org (+ spend-limit), Brevo (kvittomail), Swish-nummer, Telegram-bot,
Fortnox — skapas/ägs av kyrkan; värden in via §3.2/§3.4-mönstret.

### 3.6 Verifiering 🤖
`make deploy ENV=dev` → `make smoke ENV=dev` (healthz) → testa intake, `/grants`
(AI-utkast), översättning, gåvokvitto. Allt grönt = överlämnad miljö lever.

## 4. Vad en agent kan ta över löpande (best practice)

Efter överlämning ska driften kunna skötas **utan en namngiven person**:

- **Rotation** av API-nycklar/secrets: agent skapar ny version i Secret Manager
  och triggar deploy — `:latest` plockas upp. Ingen kodändring, ingen person.
- **Infra-ändringar**: PR → `plan` → merge → auto-`apply`. Agenten kan föreslå,
  granska och driva igenom.
- **Innehåll/konfig**: Cloudflare KV via admin-web eller sync-pipeline.
- **Övervakning/incident**: enligt [28](28-agentisk-driftmodell.md) +
  ops-cli — agenten läser (PII-maskade) loggar, öppnar incident, föreslår fix.

**Irreducibelt mänskligt** (kan inte och bör inte automatiseras bort):
att *äga* kontona, *betala* (billing/betalkort), *acceptera villkor*, och
*godkänna* känsliga ändringar (prod-apply, IAM, RED-data) — de senare ska kräva
mänsklig review enligt ops-contract även när en agent föreslår dem.

## 5. Två driftmodeller

| | A. Vi driftar (managed) | B. Kyrkan driftar själv |
|---|---|---|
| Kontoägare | Operatören | Kyrkan |
| Kod/pipelines | Samma repo | Samma repo (forkas/överförs) |
| Hemligheter | Operatörens Secret Manager | Kyrkans Secret Manager |
| Övergång A→B | Kör §3 mot kyrkans konton | — |
| Persondependens | Mitigeras av denna runbook | Eliminerad |

Plattformen är medvetet byggd så att **A och B är samma kod** — bara kontona
skiljer. Det är portabiliteten som gör att ingen, inklusive operatören, blir
oumbärlig.

## 6. Nästa steg när överlämning blir aktuell

1. Bestäm modell (A eller B, §5).
2. Människa skapar kontona i §2 som är 🧑.
3. Agent kör §3-runbooken mot de nya kontona.
4. Verifiera (§3.6), rotera in kyrkans nycklar, avveckla operatörens.
