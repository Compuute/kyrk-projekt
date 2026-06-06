# 23 — Uppdragsavtal: Ansvarsfördelning & SLA

Professionellt ramverk för begravnings- och hemtransport-tjänsten.
Baserat på SBF:s "God begravningssed", Prisinformationslagen,
och best practice från Fonus/Lavendla/Fenix.

## Tre parter — tydliga roller

```
┌──────────────────────────────────────────────────────┐
│                    KYRKAN                             │
│            (begravningstjänsten)                      │
│                                                       │
│  Koordinator, kontaktpunkt, ceremoni, dokumentation   │
│  "Familjen ringer ETT nummer — vi gör resten"        │
└────────────┬─────────────────────┬───────────────────┘
             │                     │
    ┌────────▼────────┐   ┌───────▼────────────┐
    │    FAMILJEN      │   │    PARTNERS         │
    │   (kunden)       │   │                     │
    │                  │   │  Evigo (balsamering) │
    │  Beslut          │   │  Ethiopian Airlines  │
    │  Information     │   │  Ambassad            │
    │  Betalning       │   │  Kyrkogårdsförvaltn. │
    └──────────────────┘   └─────────────────────┘
```

## Ansvarsmatris — begravning i Sverige

### Vad KYRKAN ansvarar för

| # | Uppgift | SLA (tid) | Verifiering |
|---|---|---|---|
| K1 | **Första kontakt** — svara familjen | Inom 30 min (24/7) | Tidsstämpel i systemet |
| K2 | **Rådgivningsmöte** — gå igenom alternativ med familjen | Inom 24 timmar | Möte bokat i systemet |
| K3 | **Uppdragsavtal** — skriftligt avtal med paketval + pris | Vid rådgivningsmötet | Signerat avtal |
| K4 | **Dödsanmälan** till Skatteverket | Inom 2 arbetsdagar | Bekräftelse i checklistan |
| K5 | **Kista** — beställa och leverera | Inom 3 arbetsdagar | Checklist: log_coffin |
| K6 | **Kylförvaring** — ordna via partner | Inom 24 timmar | Checklist: log_cold_storage |
| K7 | **Transport** till kyrkan | Avtalat datum | Checklist: log_transport_to_church |
| K8 | **Rituell tvagning** (ንጽሕና) koordinering | Före ceremoni | Checklist: log_ritual_washing |
| K9 | **Blommor** — beställa | 3 dagar före ceremoni | Checklist: log_flowers |
| K10 | **Begravningsprogram** (am+sv+en) | 3 dagar före ceremoni | AI-genererat, familj godkänner |
| K11 | **Ceremoni** med präst | Avtalat datum/tid | Checklist: cer_date_set |
| K12 | **ሐዘን** (vigil) — koordinera | Kvällen innan/efter | Checklist: cer_vigil |
| K13 | **Kolliva** — förbereda | Ceremonidagen | Checklist: cer_kolliva |
| K14 | **Kör** — notifiera | 1 vecka före | Checklist: cer_choir |
| K15 | **Gravplats** — koordinera med förvaltningen | Inom 5 arbetsdagar | Checklist: log_grave_confirmed |
| K16 | **Telegram-broadcast** | Samma dag som ceremoni bestäms | Checklist: cer_telegram_broadcast |
| K17 | **Minnessida** — publicera | Inom 3 dagar | Checklist: cer_memorial_page |
| K18 | **Begravningsbevis** — utfärda | Samma dag som ceremoni | Checklist: aft_certificate |
| K19 | **Faktura** — skicka till familjen | Inom 7 dagar efter ceremoni | Checklist: aft_invoice |
| K20 | **Sorg-kalender** — aktivera automatiska påminnelser | Dag 1 efter ceremoni | Checklist: aft_grief_calendar |
| K21 | **NPS/feedback** — fråga familjen | 2 veckor efter ceremoni | Checklist: aft_feedback |

### Vad FAMILJEN ansvarar för

| # | Uppgift | Deadline | Stöd från kyrkan |
|---|---|---|---|
| F1 | **Kontakta oss** vid dödsfall | Så snart som möjligt | 24/7 telefon + Telegram |
| F2 | **Uppge information** om den avlidne | Vid rådgivningsmötet | Checklista ges av kyrkan |
| F3 | **Välja paket** (Enkel/Standard/Komplett) | Vid rådgivningsmötet | Kyrkan förklarar skillnaderna |
| F4 | **Besluta om hemtransport** (ja/nej + destination) | Vid rådgivningsmötet | Kyrkan informerar om process + pris |
| F5 | **Lämna dödsbevis** (från läkaren) | Inom 3 dagar | Kyrkan påminner + hämtar |
| F6 | **Lämna den avlidnes pass/ID** | Vid rådgivningsmötet | Krävs för ambassad (hemtransport) |
| F7 | **Välja ceremonidatum** | Inom 5 dagar | Kyrkan föreslår tillgängliga datum |
| F8 | **Godkänna begravningsprogram** | 2 dagar före ceremoni | AI-utkast skickas för godkännande |
| F9 | **Informera Eder-förening** (om tillämpligt) | Inom 3 dagar | Kyrkan kan kontakta Eder åt familjen |
| F10 | **Betala** | Enligt avtal (före/efter) | Swish, bankgiro, Eder-bidrag |
| F11 | **Meddela mottagare i hemland** (hemtransport) | Inom 3 dagar | Kyrkan behöver namn + telefon |
| F12 | **Ge minnestext/foto** (om minnessida önskas) | Inom 1 vecka | Kyrkan kan AI-generera utkast |

### Vad PARTNERS ansvarar för

| Partner | Uppgift | SLA | Kyrkans åtgärd vid försening |
|---|---|---|---|
| **Evigo** | Balsamering + zinkkista | 2-3 arbetsdagar | Eskalera till alternativ partner |
| **Ethiopian Airlines (Kales)** | Flygfrakt ARN→ADD | 3+ dagars förbokning | Turkish Airlines backup |
| **Etiopiens ambassad** | Tillståndsbrev | 30 min (vid kompletta dok) | Eskalera via ambassadkontakt |
| **Eritreas ambassad** | Tillståndsbrev | 2-5 arbetsdagar | Alternativ rutt om 2%-skatt blockar |
| **Kyrkogårdsförvaltning** | Gravplats + grävning | 3-5 arbetsdagar | Ring + eskalera |
| **Skatteverket** | Passersedel | 1-3 arbetsdagar | Skicka påminnelse |
| **Mottagare (Addis/Asmara)** | Tull + transport | Vid ankomst | WhatsApp-koordinering |

## Ansvarsmatris — hemtransport (tillägg)

### Vad KYRKAN ansvarar för (utöver ovan)

| # | Uppgift | SLA | Verifiering |
|---|---|---|---|
| H1 | **Ordna balsameringsintyg** | Inom 3 dagar | Checklist: rep_embalming |
| H2 | **Ordna intyg om icke-smittsam sjukdom** | Inom 3 dagar | Checklist: rep_health_cert |
| H3 | **Begravningsentreprenörens intyg** (kistinnehåll) | Vid zinkkista-montering | Checklist: rep_funeral_director_cert |
| H4 | **Ansöka passersedel** (Skatteverket) | Inom 2 dagar | Checklist: rep_passersedel |
| H5 | **Kontakta ambassad** | Dag 1-2 | Checklist: rep_embassy_permit |
| H6 | **Boka flygfrakt** (Ethiopian Airlines HUM) | Min 3 dagar före | Checklist: rep_flight_booked |
| H7 | **Fylla i Air Waybill** | Dag före flyg | Checklist: rep_air_waybill |
| H8 | **Leverera till Arlanda Cargo** | Flygdagen | Checklist: rep_cargo_delivered |
| H9 | **Bekräfta ankomst** med mottagare | Flygdagen | Checklist: rep_arrival_confirmed |
| H10 | **Returnera passersedel-kopia** till Skatteverket | Inom 2 veckor efter export | Checklist: rep_passersedel_returned |

### Vad FAMILJEN ansvarar för (hemtransport)

| # | Uppgift | Deadline | Stöd från kyrkan |
|---|---|---|---|
| HF1 | **Besluta om destination** (stad i Etiopien/Eritrea) | Dag 1 | Kyrkan frågar vid rådgivningsmötet |
| HF2 | **Uppge mottagare** (namn, telefon, adress) | Inom 3 dagar | Kyrkan behöver detta för AWB + mottagning |
| HF3 | **Lämna pass/ID** för den avlidne | Inom 2 dagar | Krävs av ambassaden |
| HF4 | **Eritrea: Verifiera 2%-skattestatus** | Dag 1 | Kyrkan informerar om kravet |
| HF5 | **Meddela familj i hemland** om beräknad ankomst | När flyg är bokat | Kyrkan ger exakt datum + flygnummer |

## Kundkommunikation — 10 kontaktpunkter

```
TIDSLINJE (begravning i Sverige — 7-14 dagar)

Dag 0   ☎️  KONTAKTPUNKT 1: Familjen ringer
             → Kyrkan svarar inom 30 min
             → "Vi tar hand om allt. Boka rådgivningsmöte."

Dag 0-1 🤝  KONTAKTPUNKT 2: Rådgivningsmöte (60 min)
             → Gå igenom paket, priser, önskemål
             → Skriva uppdragsavtal
             → Familjen tar INGA beslut under press
             → "Ta 24 timmar att bestämma om ni vill"

Dag 1-2 📋  KONTAKTPUNKT 3: Bekräftelse (Telegram/SMS)
             → "Vi har startat ert ärende. Här är er checklista."
             → Länk till ärendet i systemet (read-only för familjen)

Dag 3-5 📝  KONTAKTPUNKT 4: Begravningsprogram skickas
             → AI-genererat utkast (am+sv+en)
             → "Godkänn eller ändra innan [datum]"

Dag 5-7 ⛪  KONTAKTPUNKT 5: Ceremonin
             → Kyrkan hanterar allt
             → Familjen sörjer i frid

Dag 7   📄  KONTAKTPUNKT 6: Begravningsbevis
             → Utfärdas digitalt
             → Skickas till familjen

Dag 7-10 💳 KONTAKTPUNKT 7: Faktura
             → Itemiserad faktura (varje post separat)
             → Betalningsplan om behov finns
             → Eder-bidrag avräknas automatiskt

Dag 10  🌐  KONTAKTPUNKT 8: Minnessida publicerad
             → "Er minnessida är live: [länk]"
             → Familjen kan redigera/lägga till

Dag 14  💬  KONTAKTPUNKT 9: Uppföljning
             → "Hur upplevde ni vår tjänst?"
             → NPS-fråga (0-10)
             → "Finns det något vi kunde gjort bättre?"

Dag 3/7/12/40/180/365  🕊️  KONTAKTPUNKT 10: ተዝካር-påminnelser
             → Automatiska (n8n workflow)
             → "Idag är ሳልስት för [namn]. Kontakta familjen."
             → Vid dag 40 + 1 år: erbjud ceremoniplanering
```

## Uppdragsavtalet — vad som ska stå

### Obligatorisk information (Prisinformationslagen)

| Fält | Innehåll |
|---|---|
| Kyrkans namn + org.nr | Abune Tekle Haymanot, 802492-9237 |
| Kontaktperson | Begravningsansvarig + telefon |
| Paketval | Enkel / Standard / Komplett |
| Paketpris | Exakt belopp inkl. moms |
| Hemtransport | Ja/Nej + destination + pris |
| Totalpris | Paket + hemtransport |
| Eder-bidrag | Namn + belopp (avräknas) |
| Att betala | Totalpris – Eder-bidrag |
| Betalningsvillkor | Inom 30 dagar / delbetalning |
| Vad som ingår | Itemiserad lista (se paket) |
| Vad familjen ansvarar för | Dödsbevis, pass, mottagare, godkännanden |
| Kyrkans åtagande | Koordination, ceremoni, dokument, sorg-kalender |
| Avbokning | Gratis avbokning inom 24h; därefter kostnader uppkomna |
| Klagomål | Kontakta [person], eskaleras till styrelsen |

### Itemiserad prislista (transparens)

**Standard-paket (28 000 kr):**

| Post | Pris |
|---|---|
| Kista (standard ek) | 6 000 kr |
| Transport (hämtning + till kyrkan + till kyrkogården) | 4 000 kr |
| Kylförvaring (5 dygn) | 3 000 kr |
| Ceremoni (präst, kyrka, ljud) | 5 000 kr |
| Blommor (kistdekoration + bukett) | 3 000 kr |
| Begravningsprogram (tryckt, 50 st) | 2 000 kr |
| Digital minnessida (permanent) | 1 000 kr |
| Koordination + administration | 4 000 kr |
| **Totalt** | **28 000 kr** |

**Hemtransport-tillägg (65 000 kr):**

| Post | Pris |
|---|---|
| Balsamering (via Evigo) | 8 000 kr |
| Zinkkista (IATA-godkänd, svetsad) | 12 000 kr |
| Flygfrakt (Ethiopian Airlines ARN→ADD) | 28 000 kr |
| Ambassad-dokumentation | 2 000 kr |
| Passersedel + tullhantering | 1 000 kr |
| Mottagning i Addis Abeba/Asmara | 5 000 kr |
| Koordination + administration | 9 000 kr |
| **Totalt** | **65 000 kr** |

## KPI:er — mäta kvalitet

### Operativa KPI:er (mäts per ärende)

| KPI | Mål | Hur |
|---|---|---|
| **Svarstid** — första kontakt | ≤ 30 minuter | Tidsstämpel i systemet |
| **Tid till rådgivningsmöte** | ≤ 24 timmar | Bokningssystem |
| **Checklista-komplettering** | 100% före ceremoni | Automatisk i plattformen |
| **Programleverans** | ≥ 3 dagar före ceremoni | Systemet |
| **Hemtransport total tid** | ≤ 14 dagar | Systemet (registered → delivered) |
| **Faktura skickad** | ≤ 7 dagar efter ceremoni | Systemet |

### Kvalitets-KPI:er (mäts kvartalsvis)

| KPI | Mål | Metod |
|---|---|---|
| **NPS (Net Promoter Score)** | ≥ 70 | Fråga vid kontaktpunkt 9 |
| **CSAT (Customer Satisfaction)** | ≥ 85% | 1-5 skala vid feedback |
| **Klagomål** | ≤ 5% av ärenden | Loggat i systemet |
| **Förseningar** | ≤ 10% av ärenden | Checklista vs SLA |
| **Hemtransport inom 14 dagar** | ≥ 90% | Systemet |
| **Sorg-kalender-precision** | 100% | n8n-workflow leveransbekräftelse |

### Finansiella KPI:er (mäts månadsvis)

| KPI | Mål | Metod |
|---|---|---|
| **Begravningar/mån** | Växande trend | Dashboard |
| **Genomsnittlig intäkt/ärende** | ≥ 30 000 kr | Dashboard |
| **Kostnad/ärende** | ≤ 60% av intäkt | Bokföring |
| **Eder-samarbeten** | Växande antal | Systemet |
| **Hemtransport-andel** | ~25-30% | Systemet |

## Eskalering — när det inte fungerar

```
NIVÅ 1: BEGRAVNINGSANSVARIG
  Hanterar: Normala förseningar, partnerkoordination
  Tid: Samma dag

NIVÅ 2: STYRELSEORDFÖRANDE
  Hanterar: Klagomål, prisavvikelser, partnerbrott
  Tid: Inom 24 timmar

NIVÅ 3: STYRELSEN
  Hanterar: Allvarliga klagomål, rättsliga frågor
  Tid: Inom 1 vecka

EXTERN: SBF ETISKA RÅD (om SBF-auktoriserade)
  Hanterar: Tvister som ej lösts internt
  Tid: Enligt SBF:s process
```

## Familjevänliga hjälpmedel

### Checklista till familjen (ges vid rådgivningsmötet)

```
□ Dödsbevis (hämtas från läkaren/sjukhuset)
□ Den avlidnes pass eller ID-handling
□ Foton till minnessidan (valfritt)
□ Minnestext (valfritt — vi kan skriva ett förslag)
□ Val av paket (Enkel / Standard / Komplett)
□ Hemtransport: Ja / Nej
  □ Om ja: mottagarens namn + telefon i hemland
  □ Om ja (Eritrea): kontrollera 2%-skattestatus
□ Eder-förening: namn + kontaktperson
□ Särskilda önskemål (blommor, musik, gäster)
□ Betalningsmetod (Swish / bankgiro / Eder)
```

### Informationsblad till familjen (bilingualt)

| Dokument | Språk | Format |
|---|---|---|
| "Vad händer nu?" — steg-för-steg | Sv + Am | PDF/print |
| Paket & priser — jämförelse | Sv + Am | PDF/web |
| Hemtransport — hur det fungerar | Sv + Am | PDF/web |
| ተዝካር-kalender — memorial-dagar | Sv + Am | PDF/web |
| "Dina rättigheter" — konsumentinfo | Sv | PDF |

### AI-underlättande för familjen

| Behov | Utan AI | Med AI-plattform |
|---|---|---|
| Dödsanmälan | Familjen fyller i blankett | **Auto-ifylld**, familjen signerar |
| Begravningsprogram | Familjen skriver själva | **AI-utkast** på am+sv+en, familjen godkänner |
| Minnestext | Familjen skriver under sorg | **AI-förslag** baserat på info från mötet |
| Kondoleansbrev | Familjen skriver | **AI-mall** (am+sv) |
| Bouppteckningsguide | Familjen googlar | **AI-guide** anpassad per situation |
| Hemtransportdokumentation | Familjen förstår inte | **Kyrkan gör allt** — AI-genererade dokument |

## Jämförelse med kommersiella byråer

| | Fonus | Lavendla | **Vi** |
|---|---|---|---|
| Uppdragsavtal | Ja (SBF-standard) | Ja (online) | **Ja (digitalt + print)** |
| Itemiserad prislista | Delvis (på begäran) | Ja (online) | **Ja (alltid synlig)** |
| Kundmapp/checklista | Digital | Digital | **Digital + AI-driven** |
| Svarstid | Kontorstid | 24/7 (online) | **24/7 (telefon + Telegram)** |
| Uppföljning efter | Nej | Memorial 20 dagar | **ተዝካር 1 år (6 kontaktpunkter)** |
| NPS-mätning | Nej | Ja | **Ja (automatisk)** |
| Kulturell anpassning | Nej | Nej | **Ortodox tradition som standard** |
| Flerspråkigt | Nej | Nej | **Am + Sv + En** |
| Hemtransport | Outsourcad/saknas | Saknas | **Kärntjänst med SLA** |
| Eder-integration | Nej | Nej | **Inbyggd i avtal + prissystem** |

## Plattformskomponenter att bygga

| Komponent | Beskrivning | Prioritet |
|---|---|---|
| **Uppdragsavtal-generator** | AI-genererar avtal från ärendedata | P0 |
| **Familjens checklista (read-only vy)** | Familjen ser progress utan inloggning | P1 |
| **Itemiserad faktura-generator** | AI-genererar faktura per post | P0 |
| **NPS-formulär** | Automatiskt efter 2 veckor | P1 |
| **KPI-dashboard (begravning)** | Svarstid, volym, NPS, förseningar | P1 |
| **Informationsblad (PDF)** | "Vad händer nu?" bilingualt | P0 |
| **Begravningsprogram-mall** | AI-genererat trilingualt dokument | P0 |
| **Kondoleansbrev-mall** | AI-genererat am+sv | P2 |
| **Bouppteckningsguide** | AI-guide per situation | P2 |
