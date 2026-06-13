# Kapacitets- & förbättringsunderlag

Ett levande register i två delar:
1. **Vad plattformen redan kan** (kapaciteter) — så styrelse/team vet utgångsläget.
2. **Önskemål & möjligheter** för nya funktioner — prioriterbart, så vi kan bygga
   vidare medvetet.

Paras med [`functional-test-plan.md`](functional-test-plan.md) (kapaciteterna i
testbar form) och beslutslogiken i [`14-architecture-decisions.md`](14-architecture-decisions.md).

> **Statusnyckel:** ✅ finns · 📋 planerad · 🔎 utvärderas · 💡 idé · ⏸️ medvetet uppskjuten
> Förslagen nedan är **underlag för prioritering, inte beslut**.

---

## Del 1 — Nuvarande kapaciteter (vad vi HAR)

| Område | Kapacitet |
|--------|-----------|
| **Medlemskap** | Publik registrering (enskild/familj), godkännandeflöde, medlemslivscykel, RBAC, audit, KMS-krypterat personnummer, statistik |
| **Betalning** | Swish deep-links (avgift + donation), autogiro/Billecta-port, tezkar-port, bankrapport |
| **Certifikat** | Utfärda/återkalla/frys dopcertifikat, **publik verifiering utan identitetsläckage** |
| **Rapportering** | Aktiviteter m. åldersband, månads-/kvartalsrapport, styrelse-/bankexport (YELLOW-aggregat) |
| **Begravning** | Fallhantering, checklista, noter, minnessida, (del av) hemtransport-spårning |
| **Admin** | Webb-UI för intake, certifikat, KPI, bidrag, innehållseditor, audit, begravningar, skattesamtycke, datakvalitet |
| **Publik portal** | Installerbar PWA, offline, tvåspråkig sv/am, multi-församling via KV, 15 sidor, live-stream-embed |
| **Edge** | Språk-routing, KV-driven config per församling, säkerhetsheaders |
| **AI/automation** | OpenClaw-mallar (kvartalsvarians, ROI, planering, bidragsnarrativ), sanitizer (PII-skydd före LLM), bidragsdatabas |
| **Säkerhet/governance** | Zonmodell RED/YELLOW/GREEN, hexagonal arkitektur, Zitadel OIDC/RBAC, audit trail, GDPR-register, CI-guards inkl. doc-drift-tripwires |
| **Mätning** | Integritetsbevarande PWA-mätning — **byggd men vilande** (`METRICS_ENABLED=false`) |

---

## Del 2 — Förbättrings- & funktionsregister

### 2.1 Medlemsupplevelse
| ID | Önskemål / möjlighet | Värde | Insats | Status | Not |
|----|----------------------|-------|--------|--------|-----|
| IMP-01 | Inloggad medlemsportal (self-service: medlemskap, betalhistorik, kontaktuppdatering) | Hög | Hög | 💡 | Kräver OIDC/PKCE; RED-data bakom session (`mobile-web`) |
| IMP-02 | Etiopisk-ortodox liturgisk kalender (helgon/fastedagar, sv+am) | Hög | Medel | 💡 | Kulturellt starkt, låg PII, differentierande |
| IMP-03 | Digitalt medlemskort / dopcertifikat i appen | Medel | Medel | 💡 | Bygger på certificate-service |
| IMP-04 | Kalender med påminnelser / "lägg till i kalender" | Medel | Låg | 💡 | |
| IMP-05 | Live-stream + arkiv av gudstjänster | Medel | Låg | 🔎 | Embed finns; arkiv kvarstår |
| IMP-06 | Böne-/förbönsförfrågningar | Medel | Medel | 💡 | PII-känsligt — zonbedömning krävs |

### 2.2 Kommunikation
| ID | Önskemål / möjlighet | Värde | Insats | Status | Not |
|----|----------------------|-------|--------|--------|-----|
| IMP-10 | Push-notiser (aktiviteter/meddelanden) | Hög | Medel | ⏸️ | `sw.js`-handler finns; subscribe-flow saknas (FUT-02) |
| IMP-11 | Telegram-bot för medlemmar (broadcast/info) | Medel | Medel | 💡 | Admin-bot specad (doc 18) |
| IMP-12 | Nyhetsbrev / utskick (e-post) | Låg | Medel | 💡 | PII — underbiträde + samtycke |
| IMP-13 | SMS-notiser | Låg | Medel | ⏸️ | Out of scope MVP; kostnad |

### 2.3 Admin & effektivitet
| ID | Önskemål / möjlighet | Värde | Insats | Status | Not |
|----|----------------------|-------|--------|--------|-----|
| IMP-20 | Förbättrad dashboard/analytics (YELLOW) | Hög | Medel | 🔎 | Bygger på reporting-service |
| IMP-21 | Bulk-import av medlemmar | Medel | Medel | 💡 | Migrering från befintligt register |
| IMP-22 | Automatisk avgiftspåminnelse | Hög | Medel | 💡 | Via n8n + Swish |
| IMP-23 | Volontär-/frivilligschemaläggning | Medel | Medel | 💡 | |
| IMP-24 | AI-sammanfattning av kvartalsdata för styrelse | Medel | Låg | 🔎 | OpenClaw + sanitizer finns |

### 2.4 Intäkt & insamling
| ID | Önskemål / möjlighet | Värde | Insats | Status | Not |
|----|----------------------|-------|--------|--------|-----|
| IMP-30 | Återkommande donationer / klart autogiroflöde | Hög | Medel | 📋 | Billecta-port finns |
| IMP-31 | Kampanjsidor (t.ex. kapell/byggnad, Arvsfonden) | Hög | Låg | 💡 | Statisk sida + Swish |
| IMP-32 | Tezkar/minnesgåvor online | Medel | Låg | 💡 | Tezkar-port finns |
| IMP-33 | Online-bokning begravningstjänst | Hög | Hög | 🔎 | Funeral-modul delvis byggd |

### 2.5 AI & automation
| ID | Önskemål / möjlighet | Värde | Insats | Status | Not |
|----|----------------------|-------|--------|--------|-----|
| IMP-40 | AI-översättning sv↔am i innehållseditorn | Hög | Låg | ✅/🔎 | `content-editor/translate` finns — bredda |
| IMP-41 | AI-assisterad bidragsansökan | Hög | Låg | ✅ | Grants-narrativ finns |
| IMP-42 | AI-genererat utbildningsinnehåll (Youth Tech) | Medel | Hög | ⏸️ | Arkitektur förberedd (MVP out of scope) |

### 2.6 Plattform & teknik
| ID | Önskemål / möjlighet | Värde | Insats | Status | Not |
|----|----------------------|-------|--------|--------|-----|
| IMP-50 | Mobilapp-wrapper (A→B, Capacitor) | Villkorad | Medel | ⏸️ | Avvaktar kvalitativ efterfrågan (docs/26) |
| IMP-51 | Självservice-onboarding för ny församling | Medel | Medel | 💡 | Idag KV + churches.json |
| IMP-52 | Aktivera vilande mätning | Villkorad | Låg | ⏸️ | Trigger: app-efterfrågan (docs/26 §Status) |

### 2.7 Compliance & förtroende (förutsättningar)
| ID | Åtgärd | Värde | Insats | Status | Not |
|----|--------|-------|--------|--------|-----|
| IMP-60 | Zitadel US→EU-migrering | Blockerande | Låg | 📋 | Före live-data (gate 1) |
| IMP-61 | DPIA + Art. 9-bedömning + DPA-signering | Blockerande | — | 📋 | `governance/pre-production-audit-checklist.md` |
| IMP-62 | WCAG-tillgänglighetsgranskning | Medel | Låg | 💡 | Design siktar redan AAA |
| IMP-63 | Cookie-/samtyckesbanner (om mätning aktiveras) | Villkorad | Låg | ⏸️ | ePrivacy art. 5.3 |

---

## Hur registret hålls levande
- Ny idé → lägg en rad med ID, värde, insats, status 💡 och en kort not.
- När något beslutas → uppdatera status (📋/🔎) och, om arkitektoniskt, skriv en ADR.
- När något byggs → flytta kapaciteten till **Del 1** och lägg testfall i
  `functional-test-plan.md` (§6 → aktiva sektioner).
- Prioritera grovt på **värde vs insats**; blockerande compliance-rader (2.7)
  går före nya funktioner inför skarp lansering.
