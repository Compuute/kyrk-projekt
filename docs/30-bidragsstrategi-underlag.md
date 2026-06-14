# 30 — Bidragsstrategi: data-drivet underlag för de 12 bidragen

> Operativt underlag under [Agentisk driftmodell](28-agentisk-driftmodell.md).
> Beskriver *vilka av de 12 bidragen vi realistiskt kan söka*, *vilken data
> varje ansökan kräver och varifrån den kommer*, och *vad styrelsen behöver
> förbereda före respektive deadline*. Implementationen som automatiserar
> utkasten specas separat (bidragsagenten, se §7).

Datum för underlaget: **2026-06-14**. Katalogkälla:
`services/admin-web/app/data/grants.json` (12 bidrag). KPI-källa:
reporting-/activity-tjänsten (`participants_total`, `activities_count`,
`age_band_counts` + nedbrytning per typ/åldersband).

---

## 1. Församlingsprofil (det som avgör behörighet)

Behörighet avgörs av fakta om församlingen, inte av ansökningstexten. Underlaget
utgår från:

| Faktor | Värde | Källa / status |
|---|---|---|
| Form | Registrerat trossamfund (Etiopisk Ortodox Tewahedo) | ✓ känt |
| Registrerad hos SST | Ja | ✓ känt — **låser upp SST-bidragen** |
| Geografi | Nacka + Stockholm (Medhane Alem) | ✓ känt |
| Verksamhet | Gudstjänst, söndagsskola, ungdoms-/barnverksamhet | ✓ känt |
| Demokratiska stadgar + vald styrelse + årsmöte | Antas ✓ | ⚠️ styrelsen bekräftar |
| Medlemsantal (totalt) | Okänt här | finns i membership-service |
| Medlemmar < 25 år | Okänt här | kräver åldersdata på medlem |
| Verksamhet i antal län | 2 (Sthlm + Nacka = 1 län egentligen) | ⚠️ relevant för MUCF |
| Bokföring/årsredovisning/budget | Styrelsedokument | ⚠️ ej i systemet |

> De tre ⚠️-raderna är de som styr om de svårare bidragen är möjliga. De måste
> bekräftas av styrelsen — gissa inte i ansökan.

---

## 2. Behörighetsscreening — var lägger vi krutet?

Rankat data-drivet mot behörighetskriterierna i katalogen. **Att söka rätt
bidrag är den enskilt största hävstången för beviljandegrad** — en ansökan till
ett bidrag man inte är behörig för beviljas aldrig, oavsett kvalitet.

| Bidrag | Deadline | Belopp | Bedömning | Varför (data-drivet) |
|---|---|---|---|---|
| **SST Organisationsstöd** | 2027-03-15 | 50k–2M SEK | 🟢 **SÖK** | Registrerat trossamfund hos SST = kärnkrav uppfyllt. Primär finansiär. Endast KPI + årsredovisning. |
| **SST Projektbidrag** | 2027-02-01 | 20k–500k SEK | 🟢 **SÖK** | Samma behörighet. Kräver en avgränsad projektidé + budget. |
| **Kommunala verksamhetsbidrag** | 2026-11-01 | 5k–500k SEK | 🟢 **SÖK** | Ideell förening verksam i kommunen, öppen verksamhet. Lägst tröskel (difficulty: easy). Sök i **både** Nacka och Stockholm. |
| **Arvsfonden Lokalstöd** | 2026-09-01 (rullande) | 200k–15M SEK | 🟡 **STRATEGISK** | Direkt kopplad till målet att köpa lokal. Kräver ägande/långtidsavtal + att lokalen används av barn/unga. Hög insats, mycket högt belopp. |
| **Arvsfonden Projektbidrag** | 2026-09-01 (rullande) | 100k–10M SEK | 🟡 **KANSKE** | Kräver *nyskapande* projekt för barn/unga, resultat ska leva vidare. Möjligt med rätt projektdesign. |
| **MUCF Projektbidrag (ungdom)** | 2027-03-01 | 25k–750k SEK | 🟡 **KANSKE** | Ungdomsprojekt (13–25). Ingen medlemströskel. Möjligt om söndagsskola/ungdom paketeras som projekt. |
| **Nordiska ministerrådet — Kultur** | 2027-01-15 | 50k–500k DKK | 🟡 **KANSKE** | Kräver partner från 3 nordiska länder. Etiopisk-ortodoxa församlingar finns i Norge/Danmark → partnerskap realistiskt. |
| **MUCF Organisationsbidrag (ungdom)** | 2026-10-15 | 50k–1,5M SEK | 🔴 **AVSTÅ (nu)** | Kräver **≥1000 medlemmar < 25 år** + verksamhet i **5+ län**. Uppfylls sannolikt inte av en enskild församling. |
| **Erasmus+ KA2** | 2027-03-05 | 120k–400k EUR | 🔴 **AVSTÅ (nu)** | Kräver ≥3 organisationer från 3 programländer + tung EU-administration. |
| **ESF+** | 2027-02-15 | 500k–20M SEK | 🔴 **AVSTÅ (nu)** | Kräver 40–60% medfinansiering + arbetsmarknadsfokus. För tungt nu. |
| **Fritt Ord** | 2026-12-31 | 10k–1M NOK | 🔴 **AVSTÅ** | Norsk yttrandefrihetsfond, kräver norsk koppling. Ej i linje. |
| **Crafoordska stiftelsen** | 2027-04-01 | 10k–300k SEK | 🔴 **AVSTÅ** | Primärt Skåne-regionen; församlingen är i Sthlm/Nacka. |

**Slutsats:** fokusera på **3 säkra** (SST org, SST projekt, Kommun) + **1 strategisk
med byggnadsmålet** (Arvsfonden Lokalstöd). De övriga 8 är antingen ej behöriga
eller kräver partnerskap/förarbete som inte hinns med till närmaste deadline.

---

## 3. Data-readiness — vad systemet ger vs. vad styrelsen måste bidra med

Varje `required_data`-fält i katalogen klassat efter källa:

| Krav (förekommer i flera bidrag) | Källa | Status |
|---|---|---|
| `participants_total` | **Auto** — activity/reporting-tjänsten | ✅ finns, används redan i `/generate` |
| `activities_count` | **Auto** — activity/reporting-tjänsten | ✅ finns |
| `age_band_counts` | **Auto** — activity/reporting-tjänsten | ✅ finns |
| `member_count` | **System** — membership-service | 🟠 finns som data, ej kopplat till bidrag — behöver en räkne-endpoint |
| `member_count_youth` | **System** — membership-service | 🔴 kräver åldersdata per medlem; samlas ej strukturerat ännu |
| `annual_report` (årsredovisning) | **Styrelsen** | 🟠 dokument, laddas upp |
| `financial_statement` (bokslut) | **Styrelsen** | 🟠 dokument; ingen bokföringsintegration |
| `board_composition` (styrelse) | **Styrelsen** | 🟠 dokument; kan struktureras i systemet senare |
| `budget`, `project_plan`, `timeline`, `expected_outcomes` | **Styrelsen** (projektspecifikt) | 🟠 fylls i per ansökan; utkast genereras (se §7) |
| `building_plans`, `ownership_documentation` (Arvsfonden lokal) | **Styrelsen** | 🔴 kräver fastighetsunderlag |

**Tre datagap att stänga nu så vi är redo till deadline:**
1. **Medlemsräkning till bidrag** — exponera `member_count` (och, om möjligt, antal
   < 25 år) från membership-service till bidragsflödet. Liten utveckling.
2. **Ekonomiunderlag** — standardisera årsredovisning + bokslut som uppladdningsbara
   bilagor (krävs av SST org, MUCF, Kommun).
3. **Ungdomsåldersdata** — om MUCF/Arvsfonden ska bli möjliga måste ålder på
   medlemmar/deltagare registreras strukturerat (GRÖN aggregatnivå räcker, ingen
   RÖD PII behövs i ansökan).

---

## 4. Deadline-tidslinje (närmast först, från 2026-06-14)

| Deadline | Bidrag | Bedömning | Ledtid kvar |
|---|---|---|---|
| 2026-09-01 | Arvsfonden Projekt + Lokal | 🟡 | ~2,5 mån |
| 2026-10-15 | MUCF Organisationsbidrag | 🔴 | — |
| 2026-11-01 | Kommunala verksamhetsbidrag | 🟢 | ~4,5 mån |
| 2026-12-31 | Fritt Ord | 🔴 | — |
| 2027-01-15 | Nordmin Kultur | 🟡 | ~7 mån |
| 2027-02-01 | SST Projektbidrag | 🟢 | ~7,5 mån |
| 2027-02-15 | ESF+ | 🔴 | — |
| 2027-03-01 | MUCF Projektbidrag | 🟡 | ~8,5 mån |
| 2027-03-05 | Erasmus+ KA2 | 🔴 | — |
| 2027-03-15 | SST Organisationsstöd | 🟢 | ~9 mån |
| 2027-04-01 | Crafoordska | 🔴 | — |

> God nyhet: de tre säkra (SST × 2, Kommun) har **lång ledtid** — gott om tid att
> samla ekonomi-/medlemsunderlag. Arvsfonden Lokalstöd är rullande (styrelsen
> beslutar 4 ggr/år) så den kan lämnas in när fastighetsunderlaget finns.

---

## 5. Utkast-skelett för de prioriterade (sektioner mappade mot kriterier)

Skeletten visar *exakt* vilka fält som fylls automatiskt (KPI) och vilka styrelsen
matar in. Bidragsagenten (§7) skriver prosan; här är strukturen.

### 5.1 SST Organisationsstöd (🟢 primär)
- **Sammanfattning** — församlingens roll och verksamhet *(styrelse + auto-KPI)*
- **Verksamhetens omfattning** — `activities_count`, `participants_total`,
  `age_band_counts` senaste 12 mån *(auto)*
- **Medlemsunderlag** — `member_count` *(system, behöver kopplas — §3.1)*
- **Demokrati & värdegrund** — stadgar, årsmöte, styrelse *(styrelse)*
- **Ekonomi** — årsredovisning + bokslut *(styrelse, bilaga)*
- **Bedömningskriterium att möta:** "stärker de grundläggande värderingar samhället
  vilar på" → koppla verksamheten (integration, språk, ungdom) explicit.

### 5.2 SST Projektbidrag (🟢)
- **Projektnamn + syfte** *(styrelse)*
- **Projektplan, tidsplan, budget** *(styrelse — agenten genererar utkast)*
- **Förväntade resultat** — koppla till KPI-baslinje *(auto + styrelse)*
- **Bedömningskriterium:** "stärker trossamfundets roll i samhället."

### 5.3 Kommunala verksamhetsbidrag (🟢 lägst tröskel — börja här)
- **Verksamhetsplan + aktiviteter** *(auto-KPI + styrelse)*
- **Öppenhet** — visa att verksamheten är öppen för kommuninvånare *(styrelse)*
- **Ekonomi + medlemsantal** *(styrelse + system)*
- Sök separat i **Nacka** och **Stockholm**.

### 5.4 Arvsfonden Lokalstöd (🟡 strategisk — byggnadsmålet)
- **Lokalbehov + målgrupp barn/unga** *(styrelse + auto-KPI)*
- **Ägande/långtidsavtal + ritningar** *(styrelse — kräver fastighetsunderlag)*
- **Hållbarhet** — hur lokalen lever vidare *(styrelse)*

---

## 6. "Störst chans att bli beviljad" — heuristik per finansiärstyp

Generella mönster hos svenska/nordiska finansiärer (att bygga in i agentens
genererings- och granskningspass):

- **Svara exakt på kriterierna.** Varje uttalat behörighets-/bedömningskriterium
  ska ha en motsvarande, namngiven sektion i ansökan.
- **Bevis slår påståenden.** Konkreta KPI ("X deltagare i Y aktiviteter senaste
  året") väger tyngre än adjektiv. Använd systemets siffror.
- **Budget i nivå.** Sök inom `amount_range`; visa egen insats/medfinansiering där
  det efterfrågas (ESF+, ofta Arvsfonden).
- **Hållbarhet/efterlevnad.** Arvsfonden och projektbidrag kräver att resultat
  lever vidare efter bidragsperioden — beskriv förvaltningen.
- **Inga påhitt.** Saknas data → skriv `[saknas: …]` och be styrelsen komplettera,
  hellre än att gissa. Felaktiga uppgifter underkänner ansökan.

> Specifik data om *tidigare beviljade föreningars* ansökningar kunde inte hämtas
> automatiskt (finansiärernas sajter blockerar maskinhämtning, HTTP 403). När
> nätverkspolicy tillåter, eller med manuellt nedladdade beviljade exempel, kan
> agenten tränas mot dem. Tills dess används kriterie- och bevismönstren ovan.

---

## 7. Koppling till bidragsagenten (lösningen)

Allt ovan blir körbart genom bidragsagenten (separat spec): en port +
Claude-adapter som, per bidrag, drar ihop **(a) auto-KPI**, **(b) styrelsens
projektinput** och **(c) finansiärens kriterier/required_data** till ett
färdigt, granskningsbart utkast på rätt språk — med ett självgranskningspass mot
kriterierna och hård PII-spärr (endast GRÖNA aggregat lämnar tjänsten). Modell-id
i env/config per användningsfall enligt CLAUDE.md. Människa (styrelsen) godkänner
alltid utkastet före inlämning.

---

## 8. Nästa steg

**Styrelsen (ägaruppgifter):**
1. Bekräfta stadgar/årsmöte/styrelse-status (§1).
2. Ta fram senaste årsredovisning + bokslut (krävs av SST org, MUCF, Kommun).
3. Besluta projektidé för SST Projektbidrag + Kommun.
4. För Arvsfonden Lokalstöd: ta fram fastighets-/ägandeunderlag.

**System (utveckling):**
1. Koppla `member_count` (membership-service) till bidragsflödet (§3.1).
2. Bidragsagent enligt spec (§7) — börja med SST-bidragen.
3. Åtgärda Firestore-IAM för `grant_applications` (403-bannern på `/grants`).

**Prioritetsordning att söka:** Kommun (lägst tröskel) → SST Projekt → SST Org →
Arvsfonden Lokalstöd (när fastighetsunderlag finns).
