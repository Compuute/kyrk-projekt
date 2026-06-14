# 33 — Prod-bootstrap: få `plan/apply (prod)` grön

> Prod-miljön är inte bootstrappad, så `terraform-plan`/`terraform-apply` för
> `prod` misslyckas (dev fungerar). Detta är runbooken för att rätta det.
> Komplement till [12-operations.md](12-operations.md) (dev-bootstrap),
> [29-identitets-och-iam-principer.md](29-identitets-och-iam-principer.md) och
> [32-driftoverlamning-och-portabilitet.md](32-driftoverlamning-och-portabilitet.md).

## 1. Symptom & orsak

`plan (prod)` / `apply (prod)` faller med:

```
Failed to get existing workspaces: querying Cloud Storage failed: ... 404:
  "Not found; Gaia id not found for email sa-terraform@<prod>.iam.gserviceaccount.com"
```

Orsak: workflowen autentiserar via WIF som
`sa-terraform@${{ secrets.GCP_PROJECT_ID }}` där `GCP_PROJECT_ID` kommer från
GitHub-**environmentet** `prod`. Det kontot (och sannolikt hela prod-projektets
bootstrap: WIF, state-åtkomst, workspace, env-secrets) finns ännu inte. Dev är
opåverkad — den har sin egen bootstrappade identitet.

> Detta är ett **rent prod-uppsättningsgap**, inte ett fel i någon kodändring.
> Dev-pipelinen (plan + apply) är grön.

## 2. Miljömodellen (så att stegen blir begripliga)

- **En delad state-bucket** `gs://kyrk-projekt-tfstate`, isolerad per
  **terraform-workspace** (`dev`/`prod`), prefix `terraform`
  (`backend.tf`). Prod-state hamnar i workspace `prod`.
- **Per-miljö GitHub-environments** (`dev`, `prod`) håller var sina secrets:
  `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA`.
- **Auth:** `sa-terraform@<GCP_PROJECT_ID>` via WIF. Varje projekt har sitt eget
  `sa-terraform` (chicken-and-egg: kan inte skapa sig självt — skapas för hand,
  adopteras sedan i state via `imports.tf`).
- **Prod-grind:** `apply (prod)` körs bara via manuell `workflow_dispatch` med
  required reviewer på `prod`-environmentet (ops-contract).

Prod-projektets nummer är `481734975638` (se
[14-architecture-decisions.md](14-architecture-decisions.md)); projekt-**id:t**
ligger i GitHub-secreten `GCP_PROJECT_ID` (prod-environmentet).

## 3. Bootstrap-runbook

Markering: 🧑 = människa (äga konto/billing/grind), 🤖 = agent kan köra.
Kör i ordning. `<PROD>` = prod-projektets id, `<PROD_NUMBER>` = `481734975638`,
`<OWNER/REPO>` = `Compuute/kyrk-projekt`.

### 3.1 Prod-projekt + billing 🧑
Skapa (eller bekräfta) prod-projektet och koppla billing. Notera projekt-id och
projektnummer.

### 3.2 Aktivera API:er 🤖
```bash
gcloud services enable run.googleapis.com firestore.googleapis.com \
  cloudkms.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  cloudscheduler.googleapis.com pubsub.googleapis.com bigquery.googleapis.com \
  --project=<PROD>
```

### 3.3 Skapa `sa-terraform` + roller + WIF-binding 🧑 (engångs, chicken-and-egg)
Samma mönster som dev-bootstrap (12-operations §bootstrap), mot prod-projektet:
```bash
gcloud iam service-accounts create sa-terraform \
  --project=<PROD> --display-name="Terraform infra deployer (CI)"

for role in roles/editor roles/resourcemanager.projectIamAdmin \
  roles/iam.serviceAccountAdmin roles/iam.workloadIdentityPoolAdmin \
  roles/secretmanager.admin roles/cloudkms.admin roles/storage.admin; do
  gcloud projects add-iam-policy-binding <PROD> \
    --member="serviceAccount:sa-terraform@<PROD>.iam.gserviceaccount.com" \
    --role="$role" --quiet
done

# WIF-poolen `github` skapas av terraform-apply; men för den FÖRSTA apply:n
# måste poolen finnas så WIF-bindningen kan sättas. På ett nytt projekt:
#   1) skapa pool+provider för hand (se 12-operations), eller
#   2) kör en lokal `terraform apply` som projektägare som skapar dem,
#      och låt sedan CI ta över.
gcloud iam service-accounts add-iam-policy-binding \
  sa-terraform@<PROD>.iam.gserviceaccount.com --project=<PROD> \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<PROD_NUMBER>/locations/global/workloadIdentityPools/github/attribute.repository/<OWNER/REPO>"
```

### 3.4 Ge prod-`sa-terraform` åtkomst till den delade state-bucketen 🤖 (lätt att missa)
State-bucketen `kyrk-projekt-tfstate` är **delad** men ligger i seed-/dev-projektet.
Prods `sa-terraform` (ett annat projekts SA) måste få läsa/skriva den:
```bash
gcloud storage buckets add-iam-policy-binding gs://kyrk-projekt-tfstate \
  --member="serviceAccount:sa-terraform@<PROD>.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```
> **Alternativ (renare, valfritt):** ge prod en **egen** state-bucket
> (`<PROD>-tfstate`) och välj den via `terraform init -backend-config=...` per
> miljö i workflowen, i stället för en delad bucket. Då kopplas inte dev och
> prod via samma bucket. Kräver en liten workflow-ändring.

### 3.5 Skapa prod-workspace 🤖
Vid första körningen finns inte workspace `prod`. Workflowen kör
`terraform workspace select prod` (som faller om den saknas). Skapa den en gång:
```bash
cd infra/terraform
terraform init -input=false
terraform workspace new prod   # därefter använder CI `select prod`
```
> Bör härdas i workflowen: byt `workspace select prod` mot
> `workspace select prod || workspace new prod` så bootstrap blir självläkande.

### 3.6 Sätt prod-environmentets GitHub-secrets + grind 🧑/🤖
I GitHub → Settings → Environments → **prod**:
- Secrets: `GCP_PROJECT_ID=<PROD>`, `GCP_REGION=europe-north1`,
  `GCP_WIF_PROVIDER=<full provider-resurssträng>`,
  `GCP_DEPLOYER_SA=sa-deployer@<PROD>.iam.gserviceaccount.com`.
- **Required reviewers** på `prod` (ops-contract: prod-apply kräver mänskligt
  godkännande).
```bash
gh secret set GCP_PROJECT_ID --env prod --body "<PROD>"
gh secret set GCP_REGION     --env prod --body "europe-north1"
gh secret set GCP_WIF_PROVIDER --env prod --body "<provider>"
gh secret set GCP_DEPLOYER_SA  --env prod --body "sa-deployer@<PROD>.iam.gserviceaccount.com"
```

### 3.7 Första apply 🧑 (godkänns via grinden)
Kör **terraform-apply** (workflow_dispatch, environment=prod). Den grindas av
required reviewer. `imports.tf` adopterar det handskapade `sa-terraform` in i
state. Apply skapar resten (Artifact Registry, KMS, runtime-SA:er, Firestore
`eur3`, buckets, Secret Manager-containrar, Pub/Sub, scheduler i `europe-west1`).

### 3.8 Lägg in prod-hemlighetsvärden 🧑(skapa)+🤖(lägg in)
Som i [32 §3.2](32-driftoverlamning-och-portabilitet.md): för varje secret
(`anthropic-api-key`, `zitadel-client-secret`, `admin-notify-webhook`,
`fortnox-*`) lägg in värdet med `gcloud secrets versions add … --project=<PROD>`.

## 4. Gotchas (verifierade i koden)

- **Firestore-location är oåterkalleligt.** Prod sätts till `eur3` (multi-region,
  ADR-019) i workflowen. Att ändra efter skapande ger destroy+recreate — exportera
  data först.
- **Cloud Scheduler-region:** redan åtgärdat (`scheduler_region=europe-west1`,
  doc 30-eran) — Scheduler finns inte i `europe-north1`.
- **Delad state-bucket** (§3.4) — utan bucket-IAM för prods SA faller redan
  `terraform init`/workspace-listningen (det är just det felet i §1 efter att SA
  finns).
- **Prod-grinden** får inte tas bort — `apply (prod)` ska kräva mänsklig review.

## 5. Verifiering

1. `plan (prod)` på en infra-PR blir grön (inget Gaia-/bucket-fel).
2. `terraform-apply` (prod) körs igenom efter godkännande.
3. `make smoke ENV=prod` (healthz på alla tjänster) grön.

## 6. Vad en agent kan ta över

Allt utom det irreducibelt mänskliga (§3.1 billing, §3.3 första SA/WIF om poolen
inte finns, §3.6 reviewer-grinden, §3.8 att skaffa nycklar) kan en agent köra —
inklusive att härda workflowen (§3.5) så att nästa miljö-bootstrap blir
självläkande. Princip och gränser: [32](32-driftoverlamning-och-portabilitet.md).
