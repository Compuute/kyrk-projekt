# GCP Well-Architected & FinOps Guidelines

Detta dokument definierar de strikta arkitektur-, säkerhets- och kostnadsprinciper (FinOps) som **all utveckling och infrastruktur** i `kyrk-projekt` måste följa. Både mänskliga utvecklare och framtida AI-assistenter ska följa dessa riktlinjer slaviskt.

---

## 1. GCP Well-Architected & Serverless-först

Vi tillämpar en **serverless-first-policy** för att minimera underhåll och maximera elasticitet.

* **Skala till noll (Scale-to-Zero)**:
  - Alla Cloud Run-tjänster ska konfigureras med `min_instances = 0`. Inga resurser får kosta pengar när systemet är inaktivt.
* **Serverless Databaser & Lagring**:
  - Vi använder **Firestore Native Mode** för dokumentlagring och **BigQuery** för analytisk data. Inga provisionerade servrar (t.ex. Cloud SQL eller virtuella maskiner) får introduceras utan explicit arkitekturbeslut.
* **Händelsestyrd bakgrundskörning**:
  - Bakgrundsjobb körs via asynkrona FastAPI `BackgroundTasks` inom de befintliga serverless-containrarna, alternativt Cloud Tasks/Cloud PubSub. Vi undviker alltid-på-system som n8n.

---

## 2. FinOps Best Practices (Kostnadsoptimering)

FinOps handlar om att maximera värdet av varje moln-krona. Vår målsättning är **€0/månad i baslinje-kostnad** för utveckling och minimala kostnader för produktion.

* **Resursval**:
  - Välj SaaS-tjänster med generösa gratistiers (t.ex. Zitadel Cloud som tillåter upp till 25 000 aktiva användare/månad gratis) framför att självhosta tjänster som kräver fasta VM-kostnader (t.ex. Keycloak på en VM eller Cloud SQL).
* **Livscykelhantering**:
  - Alla GCS-lagringshinkar ska ha definierade livscykelregler (t.ex. att temporära filer i `openclaw-pending` raderas automatiskt efter 90 dagar) för att undvika onödig lagringskostnad.
* **Täta instanser (Min/Max)**:
  - Max-gränser för Cloud Run-instanser sätts lågt (t.ex. max 3 eller 5 instanser) för att förhindra skenande kostnader vid eventuella överbelastningsattacker (DDoS) eller buggar med oändliga loopar.

### 2.1 Proaktiva Budgetlarm

* **GCP Billing Budget**: Varje GCP-projekt (dev och prod) ska ha en programmatisk budgetalarm definierad i Terraform.
  - Standardbudget: **€20/månad** (prod), **€10/månad** (dev).
  - Trösklar: Notifiering vid **50%**, **80%**, och **100%** av budgeten.
  - Kanal: Notifieringar skickas till en dedikerad Pub/Sub-topic (`budget-alerts`) som kan kopplas till e-post eller webhook.
* **Granskning**: Budgetar och faktiska kostnader granskas månadsvis av projektansvarig.

---

## 3. Security Best Practices (Säkerhet)

Säkerheten bygger på principen om **Defense in Depth** (djupförsvar) och strikt uppdelning av känsliga uppgifter.

* **Zonmodellen (RED / YELLOW / GREEN)**:
  - **RED**: Personuppgifter (personnummer, namn, e-post, telefon). Krypteras i databasen på fältnivå med Cloud KMS. Endast behöriga tjänster (`membership-service`, `membership-intake`, `certificate-service`) får access till RED-data.
  - **YELLOW**: Aggregerad anonym statistik och KPI:er. Får läsas av analysverktyg och skickas till LLM via sanitizers.
  - **GREEN**: Publik information (hemsidor, kyrkokataloger).
* **Least Privilege IAM**:
  - Varje tjänst körs under ett eget dedikerat tjänstekonto (`sa-service-name`) som enbart har rättigheter till de exakta resurser (t.ex. en specifik lagringshink eller en specifik nyckel i KMS) som krävs för dess funktion.
* **Workload Identity Federation (WIF)**:
  - Inga GCP-tjänstekontonycklar (JSON-filer) får någonsin laddas upp till GitHub eller sparas lokalt. Driftsättning sker via GitHub Actions som autentiserar sig federerat via Google WIF.
* **Inga hårdkodade hemligheter**:
  - Alla API-nycklar och tokens lagras i GCP Secret Manager. Tjänsterna hämtar dem via IAM-rättigheter under runtime, alternativt injiceras de via säkra GitHub-miljöhemligheter under driftsättning.

### 3.1 Beroendehantering & CVE-scanning

* **Dependabot**: GitHub Dependabot är aktiverat för att automatiskt övervaka och uppdatera beroenden i alla paketekosystem (pip, npm, GitHub Actions, Terraform).
  - Uppdateringsschema: **Veckovis** (måndagar).
  - PR:er granskas innan merge — automatisk merge är inte tillåten.
* **Safety/pip-audit**: CI-pipelinen kör `pip-audit` mot alla Python-tjänster vid varje PR och nattlig körning för att fånga kända CVE:er.
* **Handlingsregel**: Kritiska (CVSS ≥ 9.0) sårbarheter ska åtgärdas inom **48 timmar**. Höga (CVSS ≥ 7.0) inom **1 vecka**.

---

## 4. GitOps & Terraform Best Practices

* **Terraform som Single Source of Truth**:
  - All infrastruktur i GCP definieras i kod. Manuella ändringar i GCP-konsolen ("ClickOps") är strängt förbjudna. Om en ändring görs måste den först kodas i Terraform och driftsättas.
* **Isolerade miljöer**:
  - Även om katalogen är gemensam, ska miljötillstånd (`terraform.tfstate`) hållas strikt åtskilda via separata tillståndsfiler (t.ex. `terraform.tfstate.dev` och `terraform.tfstate.prod`).
* **Inga tillstånd i versionshantering**:
  - Lokala `terraform.tfstate`-filer och `.tfvars` som innehåller skarpa inställningar eller projekt-ID:n får aldrig checkas in i Git.

### 4.1 CI/CD Pipeline-governance

* **Branch Protection (main)**:
  - Kräv minst **1 godkännande** på PR innan merge.
  - Kräv att CI-jobben (`ci.yml`) passerar grönt innan merge.
  - Ingen direkt push till `main` — alla ändringar sker via PR.
* **Deploy-freeze**:
  - Inga deploys till prod under **helger** eller helgdagar utan explicit godkännande.
  - Prod-deploys kräver manuell `workflow_dispatch` med `environment: prod`-val.
* **Rollback-strategi**:
  - Cloud Run behåller de 3 senaste revisionerna. Vid problem kan trafiken omdirigeras till föregående revision via `gcloud run services update-traffic`.
* **CI-säkerhetsgate**:
  - CI kör `pip-audit` för Python-beroenden och `npm audit` för Node-beroenden vid varje PR.
  - Terraform `fmt -check` och `validate` körs vid varje PR.

---

## 5. UI/UX & Frontend Best Practices

* **Premium-estetik**:
  - Gränssnitt ska kännas levande och lyxiga. Använd moderna typsnitt (t.ex. Inter, Outfit) via Google Fonts istället för standardtypsnitt. Harmoniska HSL-färgpaletter och glasfria gradients (glassmorphism) rekommenderas.
* **Micro-animationer**:
  - Interaktiva element ska ha mjuka transitions (t.ex. `transition: all 0.2s ease-in-out`) vid hovring och klick.
* **Inga trackers eller externa skript på klientsidan**:
  - Enligt vår integritetspolicy och GDPR får medlemsportalen inte ladda några externa skript (t.ex. Google Analytics) eller sätta obehöriga cookies. All språköversättning sker på serversidan eller via statisk HTML-kompilering (Eleventy).

---

## 6. Observability & Monitoring

Vi använder GCP:s inbyggda observabilitetsstack för att minimera extern verktygskostnad.

* **Strukturerad loggning**:
  - Alla Cloud Run-tjänster loggar i JSON-format till Cloud Logging. Loggar ska inkludera: `severity`, `message`, `service`, `trace_id` (om tillgängligt), och `church_id` (organisationskontexten).
  - PII-fält (personnummer, namn, e-post) får **aldrig** loggas, varken i produktion eller utveckling.
* **Error Reporting**:
  - Cloud Error Reporting är automatiskt aktiverat via Cloud Logging. Alla ohandhanterade exceptions rapporteras centralt.
* **SLO-definitioner** (per tjänst):
  - **Tillgänglighet**: ≥ 99.5% (mätt som andelen lyckade HTTP-svar, exkl. 4xx).
  - **Latens (P95)**: < 2 sekunder för API-anrop, < 5 sekunder för rapportgenerering.
  - **Error budget**: 0.5% = ~3.6h/månad tillåten nedtid.

---

## 7. Alerting & Uptime Checks

* **Cloud Monitoring Uptime Checks**:
  - Varje Cloud Run-tjänst som exponeras publikt (`membership-intake`, `certificate-service`, `admin-web`) ska ha en konfigurerad HTTPS uptime check med **5 minuters intervall**.
  - Kontrollerar HTTP 2xx-svar från respektive `/healthz`-endpoint.
* **Alerting-regler**:
  - **5xx-rate > 1%** under 5 minuter → Alert (varning).
  - **Latens P95 > 5s** under 10 minuter → Alert (varning).
  - **Uptime check fail** i 2+ kontroller → Alert (kritisk).
* **Notifieringskanal**:
  - Alerts skickas till en e-postlista (`alerts@compuute.se`) och/eller befintlig webhook (`admin-notify-webhook`).
  - Framtida: koppla till PagerDuty/Opsgenie om teamet växer.

---

## 8. Disaster Recovery & Backup

* **Firestore-backup**:
  - Automatisk daglig export av hela Firestore-databasen till en dedikerad GCS-bucket (`{project_id}-firestore-backups`).
  - Exporten schemaläggs via **Cloud Scheduler** → **Cloud Functions** eller via ett nattligt CI-jobb.
  - Backup-bucketen har livscykelregel: **90 dagars retention**, därefter automatisk radering.
* **RTO / RPO-mål**:
  - **RPO (Recovery Point Objective)**: Maximalt **24 timmar** dataförlust (daglig backup).
  - **RTO (Recovery Time Objective)**: Maximalt **4 timmar** till full återställning av produktionsmiljön.
* **Återställningsförfarande**:
  - Dokumenterat i `docs/13-runbook.md` avsnitt "Firestore Restore".
  - Verifieras kvartalsvis genom en testrestaurering till dev-miljön.
* **Terraform State Backend**:
  - State lagras i en delad GCS-backend (`gs://kyrk-projekt-tfstate`, `infra/terraform/backend.tf`) med objektversionering och native locking. Miljöer isoleras via terraform-workspaces (`dev`/`prod`).
* **Terraform Apply via pipeline (GitOps)**:
  - Infraändringar appliceras av pipelinen, aldrig för hand. PR mot `infra/terraform/**` kör `terraform-plan` (diff per miljö som review-underlag); efter merge till `main` kör `terraform-apply` automatiskt mot **dev**. **Prod** appliceras via manuell `workflow_dispatch` med `environment: prod` (godkännandegate per ops-kontraktet).

---

## 9. GDPR & Datalagringspolicy

Enligt GDPR Art. 5(1)(e) — **lagringsminimering** — ska personuppgifter inte sparas längre än nödvändigt.

* **Aktiva medlemmar**:
  - Fullständig RED-data (personnummer, namn, kontaktuppgifter) lagras krypterat i Firestore så länge personen är aktiv medlem.
* **Utträdda / inaktiva medlemmar**:
  - Vid utträde: personuppgifter anonymiseras eller raderas inom **90 dagar**.
  - Aggregerad statistik (YELLOW) behålls för rapporteringsändamål.
* **Intake-ansökningar (avslagna/avbrutna)**:
  - Ansökningar som inte leder till medlemskap raderas automatiskt efter **90 dagar** via Firestore TTL-policy eller bakgrundsjobb.
* **Loggdata**:
  - Cloud Logging behåller loggar i **30 dagar** (GCP default). Inga loggexporter till långtidslagring konfigureras om inte explicit behov uppstår.
* **Rätt till radering (Art. 17)**:
  - `membership-service` exponerar en intern admin-endpoint för permanent radering av en individs data. Raderar alla dokument i `members`- och `intake_submissions`-kollektionerna kopplade till individen, samt invaliderar eventuella certifikat.
* **Register över behandlingar (Art. 30)**:
  - Upprätthålls i `docs/governance/data-processing-register.md` (skapas vid första produktionslansering).

---

## 10. Incident Response

* **Eskaleringskedja**:
  1. **L1 — Utvecklare on-call**: Tar emot alert, diagnosticerar inom 15 minuter. Konsulterar `docs/13-runbook.md`.
  2. **L2 — Tech Lead / Projektansvarig**: Eskaleras om L1 inte kan lösa inom 1 timme, eller om incidenten berör RED-data.
  3. **L3 — Extern GCP-support**: Kontaktas vid plattformsproblem utanför kontroll (regionalt avbrott, API-problem).
* **Kommunikation**:
  - Intern statusuppdatering till kyrkans styrelse om incidenten påverkar medlemsdata (RED) eller pågår > 2 timmar.
* **Post-mortem**:
  - Skrivs inom 48 timmar efter lösning. Lagras i `incidents/`-katalogen med standardmall:
    - **Sammanfattning**: Vad hände?
    - **Tidslinje**: Kronologisk händelseordning.
    - **Rotorsak**: Varför hände det?
    - **Åtgärder**: Vad gjorde vi? Vad gör vi för att förhindra det i framtiden?
* **Vanliga felscenarier**: Se `docs/13-runbook.md` för detaljerade playbooks.
