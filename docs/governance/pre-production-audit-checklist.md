# Pre-production audit-checklista

Ett papper för styrelsen att beta av **innan skarp lansering** (första
produktionsdeploy med riktig persondata). Komplement till
[`17-audit-readiness.md`](../17-audit-readiness.md), som listar vad vi *visar*
vid en granskning; den här listar vad som måste vara *klart* först.

> Statusnyckel: ✅ klart · 🟡 pågår · 🔴 ej påbörjat · ✋ kräver mänskligt/juridiskt beslut

## Grindar (blockerande för produktion)

| # | Grind | Krav | Ägare | Status |
|---|-------|------|-------|--------|
| 1 | **Dataresidens auth** | **Beslut 2026-06-13: migrera Zitadel från US- till EU/CH-region.** Görs när lösningen är färdigutvecklad, **innan** den fylls med live-data. TIA-vägen är inte aktuell. Idag: US, endast syntetisk data (ADR-017). | Ops + styrelse | 🔴 ej påbörjat |
| 2 | **DPIA (Art. 35)** | Genomför konsekvensbedömning för personnummer + barndata (söndagsskola). Mall nedan. | DPO/styrelse | 🔴 ✋ |
| 3 | **Art. 9-bedömning** | Dokumentera laglig grund för religiös tillhörighet (föreningsundantaget 9(2)(d)) + `selected_church`-inferensen. Mall nedan. | DPO/styrelse | 🔴 ✋ |
| 4 | **Underbiträdesavtal (Art. 28)** | Signera DPA med Google Cloud och Zitadel. | Ops/styrelse | 🔴 |

## Redan stängt (dokument matchar verklighet)

- ✅ Integritetspolicyn speglar verkligheten (ingen aktiv mätning).
- ✅ ADR-017: JWKS/TLS-verifiering markerad åtgärdad (matchar koden).
- ✅ Suveränitetsdoc: auth-vendor = Zitadel + US-region-caveat.
- ✅ PWA-mätning vilande (`METRICS_ENABLED = false`) — ingen ePrivacy-skyldighet
  förrän den ev. aktiveras (se `docs/26`).
- ✅ Tidigare auth-leverantör borttagen ur alla nuläges-docs (ersatt av Zitadel);
  CI-tripwire hindrar regression.

---

## Mall: DPIA (Art. 35) — fyll i

> Att fyllas i av personuppgiftsansvarig/DPO. Detta är ett skelett, inte en
> färdig bedömning.

**Behandling som bedöms:** _(t.ex. medlemsregister med personnummer; barndata i söndagsskola)_

| Del | Att fylla i |
|-----|-------------|
| Systematisk beskrivning av behandlingen | … |
| Ändamål och rättslig grund | … |
| Nödvändighet och proportionalitet | … |
| Identifierade risker för registrerade | _(t.ex. röjande av personnummer, barns uppgifter, religiös tillhörighet)_ |
| Befintliga skyddsåtgärder | KMS-kryptering, zonmodell, RBAC, audit trail, EU-residens (dataplan) … |
| Restrisk efter åtgärder | … |
| Slutsats / beslut | _(genomför / avstå / villkor)_ |
| Datum + ansvarig | … |

## Mall: Art. 9-bedömning (känsliga uppgifter) — fyll i

| Del | Att fylla i |
|-----|-------------|
| Vilken känslig uppgift? | Religiös tillhörighet (medlemskap; `selected_church` kan indirekt antyda det) |
| Rättslig grund Art. 9.2 | _(förslag: 9.2(d) — ideell förening med religiöst syfte, behandling av medlemmar/f.d. medlemmar, ingen utlämning utan samtycke)_ |
| Omfattas `selected_church`-kakan? | _(bedöm: funktionellt val vs inferens om tro)_ |
| Skyddsåtgärder | … |
| Slutsats / beslut | … |
| Datum + ansvarig | … |
