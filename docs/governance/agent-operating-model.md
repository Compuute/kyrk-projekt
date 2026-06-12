# Agent Operating Model (master)

**Den auktoritativa modellen för hur agentiska AI-grupper utvecklar och driftar
kyrk-projekt säkert.** Det här dokumentet är paraplyet; det styr över och länkar
ihop de befintliga delarna:

| Komponent | Roll | Plats |
|---|---|---|
| Verksamhetsregler (RULE 1–4) | hur en session arbetar | [CLAUDE.md](../../CLAUDE.md) + [AI-RULES.md](../../AI-RULES.md) |
| Dev-agentroller + modellpolicy | vilka bygg-agenter, vilken modell | [`.claude/agents/`](../../.claude/agents) + CLAUDE.md §4 |
| Runtime-agentkatalog + skuld + färdplan | vilka drift-agenter, i vilken ordning | [docs/28](../28-agentisk-driftmodell.md) |
| Ops-domänens grindar | approval/forbidden/escalation för drift | [ops-contract.yaml](../../ops/ops-contract.yaml) |
| Åtkomst/least privilege (KYA) | vilka verktyg/MCP en agent kopplas till | [agent-access-policy.md](agent-access-policy.md) |
| Release-säkerhet | rampa ändringar 0→100, kill switch | [docs/15](../15-ab-testing-strategy.md) + [docs/27](../27-feature-flag-workflow.md) |

Beslut: [ADR-021](../14-architecture-decisions.md). Aligned med Anthropics best
practice för agenter.

---

## 1. Premiss

Teamet är AI-agentgrupper (Claude Code m.fl.) plus mänskliga ägare. Agenter gör
merparten av **byggandet och diagnosen**; människor äger de **oåterkalleliga
besluten** och förblir ansvariga. Modellen antar att agenter är snabba och
kapabla men kan vara **självsäkert fel** — så säkerheten kommer från
*deterministiska räcken och tydliga mänskliga grindar*, inte från att lita på
agentens omdöme. (Detta repos CLAUDE.md skrevs själv efter att
självsäkert-overifierade påståenden kostade cykler — modellen kodifierar fixen.)

## 2. Principer

1. **Deterministiska räcken > omdöme.** En agent kan inte prata sig förbi en röd
   CI-check. Enforcement ligger i kod, inte i prompts.
2. **Människan äger det oåterkalleliga; agenter äger det reversibla-och-verifierade.**
3. **RED-data når aldrig en LLM.** Sanitizer-profiler är obligatoriska; agenter
   *beslutar* aldrig i RED-zonen — de förbereder, människan godkänner ("Approve
   AI output"). (doc 28)
4. **Least privilege per roll**, tillagt i lager (KYA), aldrig blanket.
5. **Verifiera mot målet** (RULE 1). Diagnos skiljs från fix; pushback med data
   är jobbet, sycophancy är en bugg.
6. **Allt agentarbete är spårbart** — utan AI-committers (RULE 4). Runtime-aktör
   = agentens servicekonto, varje aktion auditloggas.
7. **Pipelines före agentramverk.** Deterministiska flöden med ett LLM-steg + ett
   mänskligt godkännande slår tunga ramverk (doc 28 §5). Omprövas vid >3
   agentflöden i drift.
8. **Väx i lager.** Förmåga förtjänas, beviljas inte i förväg.

## 3. Två sorters agenter — under samma governance

### 3a. Dev-agenter — bygger plattformen ([`.claude/agents/`](../../.claude/agents))

| Roll | Modell | Får | Får inte |
|---|---|---|---|
| **utforskare** | Haiku | read-only kodsökning/kartläggning (Read/Grep/Glob/Bash); svarar med slutsats | ändra något; gissa på arkitektur/säkerhet (ska eskalera) |
| **implementerare** | Sonnet | implementera mot **färdig spec/DoD**, kopiera etablerade mönster | välja vid tvetydighet/designbeslut (stannar och rapporterar) |
| **granskare** | Opus | granska diff/PR — prioritet: (1) PII-läckor, (2) korrekthet (kyrk-scoping), (3) arkitektur | godkänna sitt eget arbete |

Modell-default + eskaleringsregler i CLAUDE.md §4 (Sonnet default; Fable/Opus vid
öppna/högriskuppgifter). Ingen roll merger sin egen PR, deployar till prod, eller
agerar på en §5-grind ensam.

### 3b. Runtime-agenter — driftar församlingen ([docs/28](../28-agentisk-driftmodell.md))

Rapport-, kassörs-, bidrags-, intake-, söndagsskole- och ops-agenten — var och en
med zon (RED/YELLOW/GREEN) och krav (scheduler, notifier-retries, granskningsvy).
Alla följer OpenClaw-mönstret: **sanitizer → mall → LLM → schemavalidering →
pending → mänsklig granskning**. Detaljerad katalog, hävstångsordning och
beroenden: doc 28 §4.

## 4. Räckesstacken (deterministisk enforcement)

Grön CI är en **förutsättning för mänsklig review** — en agents PR är inte "klar"
förrän räckena är gröna. Varje grind stoppar ett specifikt agent-felläge:

| Grind | Enforcar | Stoppar |
|---|---|---|
| commit-hygiene (no AI committers) | RULE 4 — committer = människan | AI-namn i historiken |
| repo guard (arkitektur/säkerhet/täckning/docs-freshness/TLS) | hexagonala gränser, ingen PII i webhooks, ≥60% cov, ingen `CERT_NONE`, docs = kod | självsäkert-fel struktur-/säkerhetsändringar |
| `tests/test_shared_auth_sync.py` | kanonisk auth-källa identisk i alla tjänster | drift i agent-identitetens auth (doc 28 skuld 1) |
| flagg-hygien + advisor | flaggor har ägare+utgång; risk-signal på hög-blast-radius | flagg-skuld; oflaggade riskändringar |
| ci/pytest, frontend-e2e/playwright | beteende | funktionella regressioner |
| `.claude/settings.json`-hooks (Stop: guard-tester; Write: vendor-lock) | tester före "klart"; inga vendor-imports i routes/ports | agent rapporterar klart med rött; vendor lock-in |
| terraform-plan (PR) / terraform-apply (approval) | infra granskas före apply | ogranskad infra-mutation |

## 5. Människan måste godkänna — agenten eskalerar, agerar aldrig ensam

Generaliserar [`ops-contract.yaml` → `approval_required`](../../ops/ops-contract.yaml):

- **Merge till main / promote till produktion** (deploy är en mänsklig "promote",
  inte auto-ship — [docs/15](../15-ab-testing-strategy.md)).
- **Prod-deploy, rollback, secret-rotation, terraform apply, Firestore-restore.**
- **Godkänna AI-output i RED-zonen** ("Approve AI output", endast `admin`).
- **Datamodell-/schemaändringar.**
- **Pengar / affärsantaganden** (t.ex. år-3-begravningsprognoserna).
- **Suveränitet / dataresidens** (t.ex. EU-region, [ADR-017](../14-architecture-decisions.md)).
- **Ändra en släppt semver-tagg** — förbjudet; rättelser släpps som nästa version
  (RULE 3, oföränderlig bevis-kedja).

## 6. Aldrig autonomt + stoppvillkor

Förbjudet oavsett roll ([`ops-contract.yaml` → `forbidden_operations`](../../ops/ops-contract.yaml)):
radera Firestore-data, ändra IAM/billing/DNS, inaktivera säkerhet (auth/KMS/WAF),
läsa/exportera RED-zon-PII, `git push --force` till main. Plus RULE 3/4.

**Agentdrift pausas omedelbart** (doc 28 §7) om: PII upptäcks i en LLM-payload
eller agentlogg; en agent agerar utanför sin RBAC-roll eller utan auditpost;
godkännandekön kringgås.

## 7. Attribution & audit (Know Your Agent)

- **Committer = människan** (RULE 4) → ansvar är otvetydigt, bevis-kedjan ren.
- **Per-agent-spår ligger utanför git-author:** *vilken agent gjorde vad* fångas
  i (a) en `Agents:`-sektion i PR-beskrivningen (roll + vad) och (b)
  sessionstranscripts. Runtime: aktör = agentens **servicekonto**, varje aktion i
  `audit_events`-kollektionen.
- **Åtkomst** (vilken MCP/token/scope) registreras i [agent-access-policy.md](agent-access-policy.md).

## 8. Verifieringskontrakt

Varje agentändring **verifieras mot det konkreta målet** (RULE 1) och räckena är
gröna **före** mänsklig review. Ett påstående "X funkar" accepteras inte förrän
det körts mot X. Att ha fel efter verifiering är okej; att ha rätt utan
verifiering räknas inte.

## 9. Runtime-arkitektur (för drift-agenter)

Ingen tung orkestrering i steg 1 (doc 28 §5). Mönstret är pipelines:

```
Cloud Scheduler → Pub/Sub → små Python-workers (hexagonala)
   → Anthropic API bakom LLMPort → pending-kö i admin-web → mänskligt godkännande
```

Omprövningspunkt: >3 agentflöden i drift + dokumenterat orkestreringsbehov. För
kodunderhåll: Claude Code i GitHub Actions (befintligt).

## 10. Förutsättningar — skuld som blockerar säker agentdrift

Agentdrift förutsätter att de "blockerar agenter"-poster i doc 28 §1 är lösta —
särskilt kanoniskt kyrk-id (skuld 1–3, delvis löst via `libs/shared-auth/` +
sync-vakten), kö/scheduler (skuld 5, största blockeraren), ärlig täckning (skuld
6) och leveransgaranti i notifier-adaptrar (skuld 8). Färdplan: doc 28 §6.

## 11. Hur allt hänger ihop

```
            Agent Operating Model  (detta dokument — master)
                          │
   ┌──────────┬───────────┼───────────┬────────────┬───────────┐
 CLAUDE.md   .claude/    doc 28      ops-contract  KYA-access  CI-gates +
 RULE 1-4    agents/     (runtime-   (approval/    (.mcp.json) settings-hooks
 + §4 modell (dev-roller catalog +   forbidden/    least priv  (enforcement)
  -policy)   utforskare/ roadmap +   escalation)
             implement./ skuld)
             granskare
```

Master:n är policyn; CI-gates + hooks är mekanismen; människan är den ansvariga
ägaren. Nya förmågor (ny MCP-server, ny agent-roll, write-behörighet) läggs till
genom att ändra master:n + berörda referensdokument i en PR granskad av en
människa — aldrig ad hoc.
