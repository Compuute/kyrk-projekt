# 29 — Identitets- och IAM-principer: en identitet per pipeline

> Kodifierar besluten från terraform-apply-incidenten 2026-06-12, då
> GitOps-applyn kördes från CI för första gången och hela bootstrap-kedjan
> blottlades. Gäller alla utvecklare och alla AI-agenter som rör miljön.
> Maskinläsbara räcken finns i [ops-contract.yaml](../ops/ops-contract.yaml);
> agenternas operativa modell i
> [Agent Operating Model (master)](governance/agent-operating-model.md).

---

## 1. Principen

**En identitet per pipeline/agent — aldrig delade konton, aldrig nycklar.**

Säkerheten ligger inte i korta rollistor utan i tre egenskaper som varje
identitet måste ha:

1. **Separation.** Den mest körda pipelinen (app-deploy) får aldrig
   infra-makt på köpet. En kompromettering av ett flöde ger inte nästa.
2. **Spårbarhet.** Varje identitet har eget audit-spår i Cloud Logging —
   man ska kunna svara på "vem gjorde detta?" med pipeline-precision.
3. **Ingen nyckel.** All CI-åtkomst går via Workload Identity Federation,
   begränsad till detta GitHub-repo (`attribute.repository`-villkoret i
   [wif.tf](../infra/terraform/wif.tf)). Inga exporterade SA-nycklar, någonsin.

En IaC-identitet *måste* kunna administrera det IaC:n äger (IAM, KMS,
secrets, WIF, buckets). "Least privilege" för den betyder alltså: separat
identitet + repo-låst WIF + eget audit-spår — inte en kort rollista.

## 2. Identitetskartan

| Identitet | Används av | Makt | Får aldrig |
|---|---|---|---|
| `sa-deployer` | `deploy.yml` (app-deploy) | Bygga/pusha images, deploya Cloud Run, läsa secrets (4 roller) | Röra IAM, KMS, infra |
| `sa-terraform` | `terraform-apply.yml` + `terraform-plan.yml` | `editor` + IAM/SA/WIF/secret/KMS/storage-admin | Användas utanför Terraform-pipelinen |
| `sa-<tjänst>` (runtime, 5 st) | Respektive Cloud Run-tjänst | Exakt det tjänsten kräver ([iam_bindings.tf](../infra/terraform/iam_bindings.tf) är kanoniska ytan) | Läsa andra tjänsters data |
| `sa-agent-worker` | Agent-jobb (rapportagent m.fl.) | Firestore `audit_events` + invoker på reporting-service | RED-zonens kollektioner, KMS, secrets utöver egen env |
| `sa-agent-jobs-pusher` | Pub/Sub push | Exakt en sak: invoka agent-worker | Allt annat |
| Projektägaren (människa) | Bootstrap + grindar | Allt | Användas för rutindrift |

## 3. Hur ändringar i miljön får ske

- **All infra ändras via Terraform-PR.** IAM-bindningar bor i
  `iam_bindings.tf` — finns bindningen inte där får tjänsten inte bero på
  förmågan. Aldrig `gcloud`/`terraform` för hand mot dev/prod (undantag:
  bootstrap, §4).
- **Dev auto-applyar vid merge till main**; mergen är godkännandet.
  **Prod är gated** bakom manuell dispatch med environment-reviewer.
  Apply körs alltid från main — aldrig från brancher (skyddar mot att en
  branch destroyar en annans resurser ur state).
- **Service-till-service mot privata tjänster**: anroparens Google-identitet
  i `X-Serverless-Authorization` (Cloud Run IAM validerar och strippar) +
  användarens/agentens Zitadel-token i `Authorization` (appens RBAC).
  Mönstret implementeras i admin-webs `app/adapters/gcp_identity.py`.

## 4. Bootstrap — det enda människan gör för hand

Hönan-och-ägget: `sa-terraform` kan inte skapa sig själv, och API:er kan
inte aktiveras av ett konto som inte finns. På ett nytt projekt gör
projektägaren, en gång, i ordning:

1. **Aktivera API:er** (annars faller apply med 403):
   `cloudresourcemanager`, `cloudscheduler`, `iam`, `run`, `secretmanager`,
   `cloudkms`, `firestore`, `bigquery`, `pubsub`, `monitoring`.
   TODO: kodifiera som `google_project_service` i en `apis.tf` så listan
   inte driftar (uppföljning till fas 1).
2. **Skapa `sa-terraform`** + roller + WIF-bindning — exakta kommandon i
   [12-operations.md](12-operations.md). OBS: vänta några sekunder mellan
   `create` och rollbindningarna — IAM-propagering är inte momentan och
   "service account does not exist" betyder oftast bara "för snabbt".
3. Därefter adopterar import-blocket i
   [imports.tf](../infra/terraform/imports.tf) kontot in i state vid
   första CI-applyn. Allt efter den punkten sker via PR.

## 5. Regler för AI-agenter som driftar miljön

Agenter (rapportagenten, ops-agenten och kommande) ärver allt ovan, plus:

- **Läs [ops-contract.yaml](../ops/ops-contract.yaml) före varje
  driftoperation.** Endast `allowed_operations` får ske autonomt; allt
  under `gated_operations` kräver människa. Kontraktet valideras i CI.
- **Aldrig råa `gcloud`/`gsutil`/`terraform`** — drift går via
  `ops/ops-cli.py` (som PII-filtrerar loggar), infra-ändringar via
  Terraform-PR som människa mergar.
- **Agenter föreslår, pipelines verkställer.** En agent som vill ändra
  miljön skriver en PR med Terraform-diff och motivering — den applyar
  aldrig själv. Mergen (dev) respektive environment-gaten (prod) är
  människans beslut.
- **Egen identitet, alltid.** Agentaktioner körs som `sa-agent-worker`
  (eller framtida agent-SA:n), aldrig som `sa-deployer`/`sa-terraform`,
  så audit-spåret skiljer agent från pipeline från människa.
- **Zonmodellen gäller agenter fullt ut**: RED-data lämnar aldrig
  RED-tjänsterna; agenter konsumerar YELLOW-aggregat och skriver sina
  spår till `audit_events`.

## 6. Varför det blev så här (incidentlogg, kort)

Första CI-applyn (2026-06-12) avslöjade i tur och ordning: CRM-API:t
oaktiverat → deployern saknade IAM-läsrätt → deployern saknade läsrätt på
allt övrigt rotmodulen äger. Grundorsak: staten bootstrappades en gång med
ägarkontot, och GitOps-flödet hade aldrig körts på riktigt. Beslutet blev
att inte bredda `sa-deployer` utan införa `sa-terraform` (PR #48) — det är
principen i §1 tillämpad i stället för kompromissad.
