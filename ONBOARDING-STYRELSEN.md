# Styrelsen — Översikt

Det här dokumentet förklarar vad som byggts, vad det kostar,
och vad styrelsen behöver besluta om.

## Plattformens syfte

Systemet är byggt för att supportera **samtliga kyrkor under
Etiopisk-Ortodoxa Tewahedo Kyrkan Ärkestiftet i Sverige**
(org.nr 252002-8859).

Enligt Sveriges kristna råd (SKR) har ärkestiftet **9 församlingar**
med totalt **~3 250 registrerade medlemmar**.

Varje kyrka under ärkestiftet kan använda samma plattform med
sin egen profil, sitt eget Swish-nummer, sin egen YouTube-kanal
och sitt eget innehåll. En ny kyrka ansluts på **5 minuter**
genom att byta 5 värden i en konfigurationsfil.

## Kyrkorna — verifierad data

### Etiopisk-Ortodoxa Tewahedo Kyrkan Ärkestiftet i Sverige

**Org.nr:** 252002-8859
**Grundat:** 1986 av Ärkebiskop Elias
**Antal församlingar:** 9
**Totalt medlemmar:** ~3 250 (SKR)

| # | Församling | Stad | Org.nr |
|---|---|---|---|
| 1 | Debreselam Medhanealem (ärkestiftets HK) | Bandhagen, Stockholm | — |
| 2 | Menbere Tsebaot S:t Selasse | Stockholm (Sveavägen 17) | 252004-8642 |
| 3 | Abune Tekle Haymanot | Saltsjö-Boo, Nacka | 802492-9237 |
| 4 | Menbere Tsebaot Kidist Selassie | Norsborg, Stockholm | — |
| 5 | Debre Hail S:t Gabriel | Göteborg | 252004-8451 |
| 6 | Församlingen i Skåne | Malmö/Lund | 802427-3123 |
| 7 | Debre Mitmaq Kidest Mariam | Lund | 252004-8584 |
| 8 | Lund Debre Mewi S:t Michael | Lund | 252004-9855 |
| 9 | Etiopisk Gabriel Ortodox Kyrka | Umeå | 802449-6609 |

Källa: SKR, Allabolag, Bolagsfakta

### Eritreansk-Ortodoxa Tewahdo Kyrkan i Sverige

Eritreanska kyrkan är en **separat organisation** sedan
Eritreas autokefali 1993. Teologiskt likartad men
organisatoriskt oberoende.

| Data | Siffra |
|---|---|
| Aktiva medlemmar | ~3 000 |
| Helgdeltagare | ~5 000 |
| Registrerade församlingar | ~50 |
| Städer | Stockholm, Göteborg, Uppsala, Sundsvall, Norrköping, Örebro, Malmö m.fl. |
| Nationell organisation | Eritreanska Ortodoxa Tewahdo Kyrkan i Sverige (EOKTS) |

**Plattformen kan stödja eritreanska församlingar också** —
samma kodbas, separerad data. Kräver samarbetsavtal
mellan ärkestiften.

### Total marknad

| Grupp | Församlingar | Medlemmar |
|---|---|---|
| Etiopisk-Ortodoxa | 9 | ~3 250 |
| Eritreansk-Ortodoxa | ~50 | ~3 000–5 000 |
| **Totalt** | **~59** | **~6 250–8 250** |

## Vad vi har byggt

### Hemsida (LIVE)

**https://kyrka-portal.pages.dev**

8 sidor, alla på svenska och amhariska:

| Sida | Vad den gör |
|---|---|
| **Startsida** | Visar aktiviteter, meddelanden och snabblänkar |
| **Bli medlem** | Registreringsformulär med GDPR-samtycke |
| **Ge en gåva** | Swish-betalning + bankgiro |
| **Gudstjänst live** | YouTube-stream av gudstjänster |
| **Begravningstjänster** | 6 paket med priser, hemtransport, jämförelse med Fonus |
| **Om oss** | Kyrkans historia och Tewahedo-tron |
| **Kontakt** | Adress, telefon, tider |
| **Integritetspolicy** | GDPR-policy |

**Kostnad:** 0 kr/mån (Cloudflare Pages gratis plan)

**Ny kyrka = 5 minuters setup:**
1. Kopiera konfigurationsfilen (content.json)
2. Byt kyrkans namn (sv + am)
3. Byt Swish-nummer
4. Byt adress
5. Byt YouTube-kanal
6. Deploy — klart

### Admin-system (byggt, ej igång)

Ett internt system för kyrkans administration:

| Funktion | Vad det gör |
|---|---|
| **Medlemshantering** | Godkänn/avslå nya medlemmar |
| **Certifikat** | Utfärda dop-, vigsel- och söndagsskolebevis (10 typer) |
| **KPI-dashboard** | Se deltagarantal och kostnad per aktivitet |
| **Bidragstracker** | 12 bidragskällor med deadlines och AI-genererade ansökningar |
| **Begravningsärenden** | Checklista, hemtransport-spårning, sorg-kalender |
| **Content-editor** | Redigera hemsidans text på svenska och amhariska |
| **GDPR-rapport** | Generera underlag med en knapptryckning |

Alla funktioner är **per kyrka** — varje kyrka ser bara sin egen data.

**Kostnad vid drift:** ~200 kr/mån totalt (Google Cloud Run, scale-to-zero)

### Begravningstjänst (dokumenterad, ej lanserad)

Komplett tjänstekatalog med 6 paket:

**Begravning i Sverige:**
- Enkel begravning: 19 000 kr
- Begravning med ceremoni: 28 000 kr
- Komplett med sorgestöd: 35 000 kr

**Hemtransport till Etiopien/Eritrea:**
- Hemtransport: 70 000 kr
- Med avskedsceremoni: 85 000 kr
- Komplett med sorgestöd: 100 000 kr

Barn under 18: gratis.

Begravningstjänsten kan drivas centralt (ärkestiftet) eller
per kyrka — se styrelsebeslut #22.

**Intäktspotential (alla 9 kyrkor):**

| Mått | Siffra |
|---|---|
| Ortodoxa i Sverige (ETH+ERI) | ~6 250–8 250 personer |
| Dödsfall/år (~0.5%) | ~30–40 |
| Om vi tar 50% av marknaden | ~15–20 begravningar/år |
| Genomsnittlig intäkt/begravning | ~40 000 kr |
| Hemtransport-andel (~30%) | ~5–6 hemtransporter/år |
| **Estimerad årsintäkt** | **800 000–1 500 000 kr** |

## Vad det kostar

| Post | Kostnad |
|---|---|
| Hemsida (Cloudflare Pages) | 0 kr/mån |
| Backend (Google Cloud Run) | ~200 kr/mån (vid drift) |
| Domännamn (valfritt) | ~100 kr/år |
| Extra kyrka (hemsida) | 0 kr (samma plattform) |
| **Total driftkostnad** | **~200 kr/mån oavsett antal kyrkor** |

Utvecklingskostnaden hittills: 0 kr (byggt med AI-verktyg).

## Vad styrelsen behöver besluta

### Beslut som väntar (GitHub Issues)

Alla beslut finns som ärenden i GitHub:
**https://github.com/Compuute/.github/issues**

| # | Beslut | Prioritet |
|---|---|---|
| **#22** | Central begravningstjänst eller per kyrka? | Styrelsebeslut |
| **#6** | Utse begravningsansvarig | Styrelsebeslut |
| **#7** | Teckna ansvarsförsäkring (15-25K kr/år) | Styrelsebeslut |
| **#13** | Uppdatera stadgar med begravningsverksamhet | Årsmötesbeslut |

### Validering som behöver göras

| # | Vad | Vem |
|---|---|---|
| **#1** | Prata med 5 familjer som begravt via Fonus | Styrelsemedlem |
| **#2** | Prata med 3 Eder-föreningar | Styrelseordförande |
| **#3** | Ring Evigo (balsameringspartner) | Begravningsansvarig |
| **#4** | Ring Ethiopian Airlines cargo | Begravningsansvarig |
| **#5** | Besök Etiopiens ambassad | Begravningsansvarig |

## Säkerhet och GDPR

- **Inga personuppgifter** lagras på hemsidan
- **Inga kakor**, ingen spårning, ingen analytics
- **Personnummer** krypteras med Google Cloud KMS
- **GDPR-register** (Art. 30) dokumenterat
- **Granskningsrapport** genereras med en knapptryckning
- **224 automatiska säkerhetstester**
- **Data separerad per kyrka** — ingen kyrka kan se en annans data

## Samtliga församlingar — plattformsstöd

```
ETIOPISK-ORTODOXA ÄRKESTIFTET (org.nr 252002-8859)
│
├── 1. Debreselam Medhanealem (Stockholm)     ← Ärkestiftets HK
├── 2. Menbere Tsebaot S:t Selasse (Stockholm)
├── 3. Abune Tekle Haymanot (Nacka)           ← Pilot, LIVE
├── 4. Menbere Tsebaot Kidist Selassie (Norsborg)
├── 5. Debre Hail S:t Gabriel (Göteborg)
├── 6. Församlingen i Skåne (Malmö/Lund)
├── 7. Debre Mitmaq Kidest Mariam (Lund)
├── 8. Debre Mewi S:t Michael (Lund)
└── 9. Etiopisk Gabriel (Umeå)

ERITREANSK-ORTODOXA (separat org, möjlig framtida expansion)
├── ~50 församlingar i hela Sverige
└── Kräver samarbetsavtal med EOKTS

Samma kodbas. Separerad data. 0 kr per ny kyrka.
```

## Dokument att läsa

| Dokument | Vad det handlar om |
|---|---|
| [Begravningsbyrå analys](docs/19-funeral-bureau-investment-analysis.md) | Marknad, konkurrens, P&L |
| [Strategiska investeringar](docs/20-funeral-strategic-investments.md) | 8 investeringsområden |
| [Tjänstekatalog](docs/24-funeral-service-catalog.md) | 6 paket med priser och ansvar |
| [Ansvarsfördelning](docs/23-funeral-service-agreement.md) | SLA, KPI, kundresa |
| [GDPR-register](docs/governance/gdpr-register.md) | Art. 30 registerförteckning |

## Nästa steg

1. Styrelsen beslutar om begravningstjänsten (#22, #6, #7)
2. Validering: prata med familjer och Eder (#1, #2)
3. Partneravtal: Evigo + Ethiopian Airlines (#3, #4)
4. Ambassadbesök (#5)
5. Lansera begravningstjänsten (efter validering)
6. Anslut kyrka #2

**Allt spårbart i GitHub Issues:**
https://github.com/Compuute/.github/issues

## Frågor?

Kontakta Daniel eller öppna en diskussion:
https://github.com/Compuute/.github/discussions
