# Styrelsen — Översikt

Det här dokumentet förklarar vad som byggts, vad det kostar,
och vad styrelsen behöver besluta om.

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

**Kostnad vid drift:** ~200 kr/mån (Google Cloud Run, scale-to-zero)

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

**Dokumentation klar:**
- Ansvarsfördelning (kyrkan / familjen / partners)
- Ambassad-krav (verifierade)
- Ethiopian Airlines cargo (kontaktuppgifter)
- Evigo som balsameringspartner
- SLA:er och KPI:er

## Vad det kostar

| Post | Kostnad |
|---|---|
| Hemsida (Cloudflare Pages) | 0 kr/mån |
| Backend (Google Cloud Run) | ~200 kr/mån (vid drift) |
| Domännamn (valfritt) | ~100 kr/år |
| **Total driftkostnad** | **~200 kr/mån** |

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

### Validering som behöver göras (ej styrelse, men viktigt)

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

## Dokument att läsa

| Dokument | Vad det handlar om |
|---|---|
| [Begravningsbyrå analys](docs/19-funeral-bureau-investment-analysis.md) | Marknad, konkurrens, P&L |
| [Strategiska investeringar](docs/20-funeral-strategic-investments.md) | 8 investeringsområden, beslutskarta |
| [Tjänstekatalog](docs/24-funeral-service-catalog.md) | 6 paket med priser och ansvar |
| [Ansvarsfördelning](docs/23-funeral-service-agreement.md) | SLA, KPI, kundresa |
| [GDPR-register](docs/governance/gdpr-register.md) | Art. 30 registerförteckning |
| [Audit-beredskap](docs/17-audit-readiness.md) | Förberedelse för granskning |

## Nästa steg

1. Styrelsen beslutar om begravningstjänsten (#22, #6, #7)
2. Validering: prata med familjer och Eder (#1, #2)
3. Partneravtal: Evigo + Ethiopian Airlines (#3, #4)
4. Ambassadbesök (#5)
5. Lansera begravningstjänsten (efter validering)

**Allt spårbart i GitHub Issues:**
https://github.com/Compuute/.github/issues

## Frågor?

Kontakta Daniel eller öppna en diskussion:
https://github.com/Compuute/.github/discussions
