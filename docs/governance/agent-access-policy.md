# Agent Access Policy — Know Your Agent (KYA)

> Detta är **access-/behörighetskomponenten** i [Agent Operating Model](agent-operating-model.md).
> Den styr vilka verktyg/MCP-servrar en agent kopplas till och med vilka scopes.

Hur AI-agenter (Claude Code m.fl.) ges åtkomst till vår driftmiljö. Målet är
att **outsourca underhåll till agenter på ett säkert sätt** — agenten ska
underlätta drift utan att bli en oövervakad väg runt våra kontroller.

Samma princip som redan gäller i [CLAUDE.md](../../CLAUDE.md) /
[ops-contract.yaml](../../ops/ops-contract.yaml): *agenten kör inte rå
infrastruktur — den arbetar genom granskbara, scope:ade gränssnitt.*

---

## 1. Principer (KYA)

1. **Least privilege, read-first.** En agent får läsa innan den får skriva.
   Diagnostik (loggar, status, docs) är lågrisk och hög nytta; mutation är ett
   separat, medvetet beslut.
2. **Scope:a till stacken, inte till leverantören.** Vi kopplar bara in de
   MCP-servrar/verktyg som motsvarar det vi faktiskt kör (Cloudflare Pages +
   Pages Functions + KV) — inte hela leverantörens produktkatalog.
3. **Write/deploy stannar i den kontrollerade pipelinen.** Produktions­ändringar
   går via `deploy.yml` + ops-cli, **inte** via en alltid-på agent-MCP. En agent
   med write-access till prod bryter mot vår "ingen rå infra-access"-princip.
4. **Spårbarhet.** Varje inkopplad agent-åtkomst (server, scope, token-ägare,
   syfte) registreras i tabellen nedan — samma spårbarhet som underbiträden i
   [gdpr-register.md](gdpr-register.md).
5. **Väx i lager.** Förmågor läggs till stegvis, varje lager efter att det förra
   bevisat sig — inte allt på en gång (vi kör aldrig blanket-installern
   `--skill '*' --global` / `agent-setup/prompt.md`).

---

## 2. Lagrad utrullning

| Lager | Förmåga | Risk | Status |
|---|---|---|---|
| **1** | Read-only **diagnos** — Docs, Observability (läs loggar/analys), Builds (läs deploy-status) | Låg | **Aktiv** (denna PR) |
| **2** | **Bindings** — KV-hantering (`kyrka_content`), scoped token | Medel | Ej aktiverad |
| **3** | **Write / deploy** | Hög | **Stannar i `deploy.yml` + ops-cli** — kopplas inte som agent-MCP |

---

## 3. Inkopplade MCP-servrar (register)

Konfiguration: [`.mcp.json`](../../.mcp.json) i repo-roten.

| Server | URL | Auth | Scope | Lager |
|---|---|---|---|---|
| Cloudflare Docs | `https://docs.mcp.cloudflare.com/mcp` | Ingen (publik) | Läs docs | 1 |
| Cloudflare Observability | `https://observability.mcp.cloudflare.com/mcp` | OAuth | **Read-only** | 1 |
| Cloudflare Builds | `https://builds.mcp.cloudflare.com/mcp` | OAuth | **Read-only** | 1 |

Ej inkopplade (medvetet): Bindings (Lager 2), samt alla skriv-/deploy-servrar
(Lager 3). De ~13 övriga Cloudflare-MCP-servrarna motsvarar produkter vi inte
kör och kopplas inte in.

---

## 4. Token- & scope-regler

- **Read-only först.** Vid OAuth-inloggning till Observability/Builds: bevilja
  endast läs-scopes. Ingen write/edit/deploy-scope i Lager 1.
- **En token per syfte.** Återanvänd inte en bred konto-token; skapa scoped
  tokens per server.
- **Ägare dokumenteras.** Den människa som beviljar åtkomsten antecknas i
  registret ovan (vem, scope, datum).
- **Kostnad:** skills och MCP-anslutning är gratis; Observability-loggar ryms i
  Cloudflares gratis-tier (200 000 events/dag) långt över vår trafik.

---

## 5. Granskning

- Vid varje nytt lager: uppdatera registret + motivera i PR.
- Vid deploy-readiness (se [ADR-017](../14-architecture-decisions.md)): omvärdera
  om Lager 2/3 behövs och hur de i så fall scope:as säkert.
- Skills är description-gated (aktiveras bara när relevanta) — installation av
  hela `cloudflare`-pluginet är acceptabelt; det är **MCP-servrarna** (alltid på,
  token-bärande) som denna policy styr.
