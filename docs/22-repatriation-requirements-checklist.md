# 22 — Hemtransport: Dokumentation & Krav (End-to-End)

Komplett checklista för att transportera en avliden person från
Sverige till Etiopien eller Eritrea. Varje steg har:
- Vilket dokument
- Vem som utfärdar det
- Hur lång tid det tar
- Vad det kostar
- Hur AI kan automatisera

## Processöversikt (7-14 dagar)

```
DAG 1-2: SVENSKA DOKUMENT
  □ Dödsbevis (läkare)
  □ Dödsanmälan (Skatteverket)
  □ Transporttillstånd (Skatteverket)
  □ Tullexportdeklaration (Tullverket)

DAG 2-4: PREPARERING
  □ Balsamering (auktoriserat bårhus)
  □ Zinkkista monterad (IATA-godkänd)

DAG 3-5: AMBASSAD
  □ Etiopiska/Eritreanska ambassaden kontaktad
  □ Importtillstånd för hemland

DAG 5-10: FLYGFRAKT
  □ Ethiopian Airlines cargo bokad
  □ Air Waybill utfärdad
  □ Lämnad till cargo-terminal (ARN)

DAG 7-14: ANKOMST
  □ Tull i Addis Abeba / Asmara
  □ Mottagare hämtar
  □ Transport till begravningsplats
  □ Begravning i hemlandet
```

## Steg 1: Svenska dokument

### 1.1 Dödsbevis (Dödsorsaksintyg)

| | |
|---|---|
| **Utfärdare** | Behandlande läkare |
| **Mottagare** | Socialstyrelsen |
| **Tid** | 1-3 dagar (kan ta längre om rättsmedicinsk undersökning) |
| **Kostnad** | 0 kr |
| **Format** | Standardformulär via Socialstyrelsens system |
| **AI-möjlighet** | Bevaka status, skicka påminnelse om det dröjer |

### 1.2 Dödsanmälan till Skatteverket

| | |
|---|---|
| **Utfärdare** | Dödsboet / begravningsbyrån |
| **Mottagare** | Skatteverket |
| **Tid** | Kan göras direkt efter dödsbevis |
| **Kostnad** | 0 kr |
| **Format** | Blankett SKV 7600 eller elektroniskt |
| **AI-möjlighet** | **Auto-ifyllt formulär** baserat på ärendedata |

### 1.3 Passersedel (Laissez-passer)

| | |
|---|---|
| **Utfärdare** | Skatteverket |
| **Mottagare** | Flygbolag + ambassad |
| **Tid** | 1-3 arbetsdagar |
| **Kostnad** | 0 kr |
| **Lag** | Begravningsförordningen (1990:1147) §36 |
| **Krav** | (a) Gravsättningsintyg kan utfärdas, (b) Begravningsentreprenörens intyg att kistan innehåller enbart stoftet + personliga tillhörigheter |
| **Format** | Utfärdas på **svenska + engelska** (eller franska) |
| **AI-möjlighet** | Ansöka digitalt, bevaka handläggningstid |
| **VIKTIGT** | Inom 2 veckor efter export: **returnera bekräftad kopia** till Skatteverket |

**Notera:** Ingen separat tullexportdeklaration behövs.
Passersedeln fungerar som exportdokument — mänskliga kvarlevor
klassificeras inte som gods under tulllagstiftningen.

## Steg 2: Preparering

### 2.1 Balsamering (verifierat)

| | |
|---|---|
| **Utförare** | Licensierad begravningsbyrå |
| **Tid** | 4-8 timmar |
| **Kostnad** | 5 000 – 10 000 kr |
| **Krav** | Krävs för internationell transport (IATA) |
| **Typ** | Arteriell balsamering (formaldehyd) |
| **Intyg** | Måste ange kemikalier + IATA-compliance |
| **Notera** | Ortodox tradition kräver att kroppen behandlas med värdighet |

**Verifierade partners i Sverige:**
- **Evigo Begravningsbyrå** (Göteborg, verksam nationellt) — enda
  svenska byrån med **egen balsameringspersonal**. Hanterar många
  internationella transporter/år. Säljer även zinkkistor.
  Webb: evigo.se
- **Muslimernas Begravningsbyrå** — utför balsamering + zinkkista-
  svetsning för internationella transporter
- **Evighetens Vila** — arrangerar balsamering + internationell transport

### 2.2 Zinkkista (IATA-krav)

| | |
|---|---|
| **Krav** | IATA Dangerous Goods Regulations kräver hermetiskt förseglad metallkista |
| **Material** | Zinkklädd trä, lödd/svetsad försegling |
| **Mått** | Standard: 200 × 60 × 45 cm (kan variera) |
| **Vikt** | Tom: ~50 kg. Med kropp: ~150-250 kg |
| **Kostnad** | 8 000 – 15 000 kr |
| **Leverantör** | Kisttillverkare / grossist — avtal behövs |
| **Tid** | 1-2 dagar (om i lager), 3-5 dagar (beställning) |

## Steg 3: Ambassad-dokumentation

### 3.1 Etiopiens ambassad i Stockholm (verifierat)

| | |
|---|---|
| **Adress** | Birger Jarlsgatan 39, 111 45 Stockholm |
| **Telefon** | +46 8 120 485 00 |
| **Webb** | ethiopianembassy.se |
| **Öppettider** | Mån-Fre 08:30-16:30 |
| **Handläggningstid** | **30 minuter** (om alla dokument kompletta) |
| **Avgift** | **Gratis** |
| **Källa** | ethiopianembassy.org, consular.ethiopianembassy.org |

**Dokument till Etiopiens ambassad (verifierat):**
1. Dödsbevis — original + kopia (apostille kan krävas)
2. Balsameringsintyg — från begravningsbyrån
3. Intyg om icke-smittsam sjukdom — från läkare/hälsomyndighet
4. Begravningsentreprenörens brev — bekräftar att kroppen är förberedd
5. Ansökningsbrev — sökanden täcker kostnader + mottagaruppgifter i Etiopien
6. Pass/ID för den avlidne

**Output:** Ambassaden utfärdar ett tillståndsbrev för transport till Etiopien.

### 3.2 Eritreas ambassad i Stockholm (verifierat)

| | |
|---|---|
| **Adress** | Stjärnvägen 2B, 4:e våningen, Lidingö (PB 1164, 181 23 Lidingö) |
| **Telefon** | +46 8 441 71 70 (konsulär: +46 8 441 71 76) |
| **E-post** | consular@eritrean-embassy.se |
| **Öppettider** | Sön, Tis, Tor, Fre 09:00-12:00 & 14:30-16:30 |
| **Källa** | eritreanembassyuk.org, us.embassyeritrea.org |

**Dokument till Eritreas ambassad:**
1. Dödsbevis — formellt legaliserat (apostille via Notarius Publicus)
2. Läkarintyg — smittfritt
3. Balsameringsintyg
4. Rättsmedicinskt tillstånd (vid onaturlig dödsorsak)
5. Pass/resehandling för den avlidne
6. Eritreanskt national-ID (om ej tillgängligt: 3 eritreaner med giltigt ID kan verifiera)
7. Två vidimerade kopior av dödsbeviset

**⚠️ KRITISK VARNING: 2% diasporaskatt**

Eritreas ambassad kräver bevis på betalning av "Recovery and
Rehabilitation Tax" (2% av årsinkomst, retroaktivt sedan 1992)
innan konsulära tjänster ges. Eritreaner som inte betalat kan
**nekas** ambassad-dokumentation.

**Svenska regeringen** har offentligt kritiserat denna praxis
som tvångsmässig, men den tillämpas fortfarande av ambassaden.

**Mitigation:**
- Kontrollera familjens skattestatus tidigt (dag 1)
- Om ej betalt: **överväg Turkish Airlines-rutt via Istanbul**
  till Asmara utan ambassaddokumentation
- Alternativ: eritreanskt medborgarskap-verifikation via
  tre vittnen med eritreanskt ID

### 3.3 Importtillstånd (hemlandets sida)

| | |
|---|---|
| **Etiopien** | Ethiopian Customs Authority utfärdar importklarering |
| **Eritrea** | Ministry of Health + Customs |
| **Tid** | 2-5 dagar (parallellt med flygbokning) |
| **Ansvarig** | Mottagarpartner i Addis/Asmara hanterar |

## Steg 4: Flygfrakt

### 4.1 Ethiopian Airlines Cargo (verifierat)

| | |
|---|---|
| **Star Alliance** | Ja — partner med SAS/Lufthansa |
| **Direkt rutt** | ARN → ADD (Addis Abeba Bole) — **direkt nonstop** (ET715/ET714) |
| **Flygplan** | Boeing 787/777, ~7:45 flygtid |
| **Cargo GSA Sverige** | **Kales Group** |
| **GSA-adress** | Söderbyvägen 3C, SE-190 60 Arlandastad |
| **GSA-telefon** | +46 8 594 411 90 |
| **GSA-email** | adam.gunnarsson@kales.com |
| **GSA-öppettider** | Mån-Fre 08:00-17:30 |
| **Bokningskontor** | Isafjordsgatan 32C, 164 40 Kista |
| **Boknings-tel** | +46 8 440 0060 |
| **Boknings-email** | Etres.sweden@aviareps.com |
| **Cargo-kod** | **HUM** (human remains) |
| **Min. förbokning** | **3 dagar** före transport |
| **Bokning via** | **E-post** till cargo-kontoret |
| **Prismodell** | Per offert — kontakta GSA |
| **Leverans** | Arlanda Cargo Terminal |

**Krav från Ethiopian Airlines (IATA CTM-standard):**
1. Air Waybill (fraktsedel) — korrekt ifylld
2. Dödsbevis (original)
3. Intyg om icke-smittsam sjukdom
4. Balsameringsintyg (med info om kemikalier + IATA-compliance)
5. Passersedel (Skatteverket)
6. Ambassad-tillstånd (Etiopien)
7. Hermetiskt förseglad zinkkista (svetsad)
8. Mottagaruppgifter i Addis Abeba

### 4.2 Alternativa flygbolag

| Flygbolag | Rutt | Fördelar |
|---|---|---|
| Turkish Airlines Cargo | ARN → IST → ADD/ASM | Dagliga avgångar, bra Eritrea-rutt |
| Lufthansa Cargo | ARN → FRA → ADD | Star Alliance, pålitligt |
| Emirates SkyCargo | ARN → DXB → ADD | Via Dubai |

### 4.3 Air Waybill (Flygfraktsedel)

| | |
|---|---|
| **Utfärdare** | Flygbolaget / cargo-agenten |
| **Kostnad** | ~$20 per AWB |
| **Innehåll** | Avsändare, mottagare, innehåll, vikt, mått, deklaration |
| **AI-möjlighet** | **Auto-ifyllt** baserat på ärendedata + flygbokningsdata |

## Steg 5: Mottagning i hemland

### 5.1 Tull i Addis Abeba (Bole Airport)

| | |
|---|---|
| **Ansvarig** | Ethiopian Customs Authority |
| **Dokument** | AWB, dödsbevis, importtillstånd |
| **Handläggningstid** | 2-6 timmar (vid ankomst) |
| **Kostnad** | Varierar — mottagarpartner hanterar |

### 5.2 Mottagarpartner

| | |
|---|---|
| **Uppgift** | Hämta vid flygplatsen, tullklarera, transportera till begravningsplats |
| **Etiopien** | Lokalt begravningsföretag i Addis Abeba |
| **Eritrea** | Lokalt begravningsföretag i Asmara |
| **Kostnad** | 3 000 – 5 000 kr |
| **Kommunikation** | Via telefon/WhatsApp — vi bekräftar ankomst |

## Kostnadskalkyl (total)

| Post | Kostnad |
|---|---|
| Balsamering | 5 000 – 10 000 kr |
| Zinkkista | 8 000 – 15 000 kr |
| Ambassad-avgifter | 1 000 – 3 000 kr |
| Flygfrakt (Ethiopian Airlines) | 20 000 – 35 000 kr |
| Tullhantering (Sverige) | 0 kr |
| Mottagning i Addis/Asmara | 3 000 – 5 000 kr |
| Diverse (transport till Arlanda etc) | 2 000 – 3 000 kr |
| **Total kostnad** | **39 000 – 71 000 kr** |
| **Vårt pris till familjen** | **55 000 – 75 000 kr** |
| **Marginal** | **4 000 – 16 000 kr** |

## AI-automatisering per steg

| Steg | Manuellt idag | Med AI-plattform |
|---|---|---|
| Dödsanmälan (SKV 7600) | Handskriven/ifylld | **Auto-ifylld** från ärendedata |
| Transporttillstånd-ansökan | Manuellt formulär | **AI-genererad** ansökan |
| Tullexportdeklaration | Manuellt system | **Auto-genererad** med rätt koder |
| Air Waybill | Manuellt via cargo-agent | **Auto-ifylld** från ärendedata |
| Ambassad-brev | Manuellt | **AI-genererat** (am + en) |
| Begravningsprogram | Manuellt | **AI-genererat** (am + sv + en) |
| Mottagarkoordination | Telefon/WhatsApp | **Automatisk notifiering** |
| Statusuppdatering | Telefon till familj | **Push-notis** via app |
| Sorg-kalender | Manuellt | **Automatisk** (dag 3/7/12/40) |
| **Total tid per ärende** | **15-20 timmar** | **5-8 timmar** |

## Dokumentmallar att bygga (AI-genererade)

| Mall | Språk | Status |
|---|---|---|
| Dödsanmälan (SKV 7600-stöd) | Svenska | 🔨 Att bygga |
| Transporttillstånds-ansökan | Svenska | 🔨 Att bygga |
| Tullexportdeklaration | Svenska/Engelska | 🔨 Att bygga |
| Ambassad-brev (Etiopien) | Amhariska/Engelska | 🔨 Att bygga |
| Ambassad-brev (Eritrea) | Tigrinja/Engelska | 🔨 Att bygga |
| Air Waybill-data | Engelska | 🔨 Att bygga |
| Balsameringsintyg-begäran | Svenska | 🔨 Att bygga |
| Mottagarbekräftelse | Amhariska/Engelska | 🔨 Att bygga |
| Begravningsprogram | Am + Sv + En | 🔨 Att bygga |
| Kondoleansbrev-mall | Amhariska + Svenska | 🔨 Att bygga |
| Minnestext (memorial page) | Amhariska + Svenska | 🔨 Att bygga |
| Kvitto/faktura | Svenska | 🔨 Att bygga |

## Partneravtal att teckna

| Partner | Prioritet | Status |
|---|---|---|
| Ethiopian Airlines Cargo (Stockholm/Frankfurt) | Kritisk | ❌ Att göra |
| Turkish Airlines Cargo | Bra att ha | ❌ Att göra |
| Balsameringspartner (Stockholm) | Kritisk | ❌ Att göra |
| Zinkkista-leverantör | Kritisk | ❌ Att göra |
| Etiopiens ambassad (Stockholm) | Kritisk | ❌ Att göra |
| Eritreas ambassad (Stockholm) | Kritisk | ❌ Att göra |
| Mottagarpartner Addis Abeba | Kritisk | ❌ Att göra |
| Mottagarpartner Asmara | Kritisk | ❌ Att göra |
| Arlanda Cargo Terminal | Bra att ha | ❌ Att göra |

## Risker och mitigeringar

| Risk | Sannolikhet | Mitigation |
|---|---|---|
| Ambassad försenad | Medel | Kontakta tidigt (dag 1), ha backup-kontakt |
| Flygfrakt-plats ej tillgänglig | Låg | Boka 2-3 dagar i förväg, alt. rutt via IST |
| Balsamering försenad | Låg | 2+ partneravtal |
| Tullproblem i Addis | Medel | Mottagarpartner med tull-erfarenhet |
| Zinkkista ej i lager | Medel | Håll 1-2 i förråd (vid volym) |
| Dokumentfel | Medel | AI-verifiering av alla dokument före inskick |

## Checklista i plattformen (redan byggt)

Admin-web funeral module har redan 29-punkts checklista:
- 20 poster för svensk begravning
- 9 poster för hemtransport

Se `services/admin-web/app/ports/funeral_tracker.py` för
fullständig lista med `CHECKLIST_ITEMS_REPATRIATION`.
