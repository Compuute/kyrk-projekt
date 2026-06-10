# Issue: Beslut & setup — Wi-Fi captive portal (`wifi-intake-portal`)

> **Status:** Backlog — för diskussion i en senare sprint. **Inget beslut taget.**
> Featuren finns byggd men är inte i drift. Den här issuen samlar underlag för
> att besluta: behåller, pausar (hold) eller avvecklar vi den?

## Kategori
- [x] Produkt / Funktion (medlems-outreach)
- [x] Infrastruktur / Nätverk
- [x] Beslut krävs (behov ej fastställt)
- [ ] Felrättning (Bug)

## Beskrivning

`frontend/wifi-intake-portal/` är en **captive portal** — landningssidan som visas
när en besökare ansluter till församlingens fria Wi-Fi. Tanken är ett mjukt
**outreach-/funnelverktyg**: en vänlig, kontextanpassad välkomstskärm som visar
vad som händer i dag (vardag/söndag/temaveckor) och puffar mot medlemskap,
barn-/ungdomsverksamhet och gåvor. Privacy-first i linje med projektets profil:
statisk HTML, inga kakor, ingen spårning, `noindex`, tvåspråkig (sv/en).

## Nuläge (varför den inte "bara funkar")

1. **Content-flödet är dött.** README hänvisar till ett n8n-workflow
   (`automation/n8n/workflows/wifi_portal_content_update.json`) för att pusha
   `content.json` — men den filen finns inte, och n8n är borttaget ur hela
   projektet (vi undviker alltid-på-system). Portalen visar bara statisk
   exempel-config tills något annat skriver innehållet.
2. **Sidan beviljar inte internetåtkomst.** `content.js` gör enbart
   `loadContent` / `decideContent` / `renderContent` — det finns inget
   authorize-/session-anrop. Själva "släpp på internet"-steget måste komma
   från nätverksutrustningen.
3. **Den kräver hårdvara i lokalen** (se nedan) som vi i dag inte vet om vi har.
4. Den kostar ändå underhåll: egen Cloudflare Pages-deploy (`kyrka-wifi`), en
   content-bucket i Terraform, ett eget CI-testjobb och en rad i `deploy-sites`.

## Krav på Wi-Fi i lokalen (för att den ska göra nytta)

En captive portal kräver att **nätverksutrustningen** sköter både att visa sidan
och att släppa på trafiken. Föreslagen plattform: **Ubiquiti UniFi** (billig,
låg driftbörda, "External Portal Server"-stöd). Krav:

1. **UniFi-AP + controller** (eller motsvarande prosument-/företagsgear). Vanliga
   hemmaroutrar räcker inte.
2. **Separat gäst-SSID/VLAN**, isolerat från ev. admin-/internnät.
3. **Walled garden (förhandsallowlist):** oinloggad enhet måste nå portalens
   värdar innan internet beviljas — vitlista Cloudflare Pages-domänen
   (`kyrka-wifi…pages.dev` eller egen domän) + content-bucketen
   (`storage.googleapis.com`/vår bucket).
4. **External portal + redirect:** controllern pekas mot vår portal-URL och
   fångar enhetens första HTTP-anrop → OS:ets captive-portal-detektering triggar
   "Logga in på nätverket"-rutan. Portalen körs över HTTPS (Cloudflare).
5. **Access-grant-integration:** eftersom sidan saknar authorize-anrop måste vi
   antingen lägga till en "Fortsätt till internet"-knapp som anropar UniFi:s
   authorize-endpoint, eller köra nätet öppet och använda sidan som ren splash.

## Beslutsalternativ (att diskutera)

### Alternativ A — Behåll & färdigställ (UniFi)
Arbetsmoment om vi går vidare:
- Köp/konfigurera UniFi-AP + controller; sätt upp gäst-SSID/VLAN.
- Konfigurera walled garden (vitlista portal-domän + content-bucket).
- Peka UniFi external portal mot Cloudflare Pages-sidan.
- **Kod:** lägg till "Fortsätt till internet"-knapp i `index.html`/`content.js`
  som anropar UniFi:s authorize-endpoint (controllerns guest-auth-flöde).
- **Content:** återkoppla `content.json`-uppdatering via den nya modellen
  (FastAPI BackgroundTasks eller edge-KV) i stället för n8n — eller börja med en
  statisk `content.json` i bucketen.
- Uppdatera README (ta bort n8n-referensen) och `docs/`.

### Alternativ B — Hold (frys)
- Behåll koden men markera tydligt som "ej i drift / väntar på beslut".
- Uppdatera README så n8n-referensen inte ljuger.
- Ta bort den från `deploy-sites` så vi inte deployar en halvfärdig sida.
- Behåll CI-testet (det är grönt och billigt) eller flagga som icke-blockerande.

### Alternativ C — Avveckla (ta bort)
- Radera `frontend/wifi-intake-portal/`.
- Ta bort content-bucketen i `infra/terraform/modules/storage` (`*-wifi-portal-content`).
- Ta bort CI-jobbet `wifi-intake-portal (Node)` och raden i `Makefile`/`deploy-sites`.
- Ta bort referenser i README/docs.

## Beslutsunderlag / öppna frågor

- **Har eller planerar vi gäst-Wi-Fi i lokalen?** Om nej → Alt. B eller C.
- Finns budget/vilja för UniFi-hårdvara och nätverkssättning?
- Är outreach-värdet (puffa medlemskap/gåvor vid uppkoppling) värt underhållet?
- Om ja till behov: prioritera Alt. A till en kommande sprint.

## Rekommendation

Sätt **Hold (Alt. B)** tills behovsfrågan är besvarad i sprintplaneringen — så
vi inte deployar en halvfärdig portal, men inte heller slänger arbete som kan
återanvändas. Besluta A vs C när vi vet om gäst-Wi-Fi är aktuellt.

## Definition of Done (DoD)

### För själva beslutsärendet (denna issue stängs när):
- [ ] Behovsfrågan ("har/planerar vi gäst-Wi-Fi i lokalen?") är besvarad och dokumenterad.
- [ ] Ett alternativ (A / B / C) är valt och motiverat i sprintplaneringen.
- [ ] Det valda alternativets acceptanskriterier nedan är uppfyllda.
- [ ] Vilseledande n8n-referenser i README/docs är borttagna (gäller oavsett väg).

### Alt. A — Behåll & färdigställ (klart när):
- [ ] UniFi gäst-SSID/VLAN uppsatt och isolerat från admin-/internnät.
- [ ] Walled garden vitlistar portal-domän + content-bucket; oinloggad enhet kan ladda portalen.
- [ ] External portal pekar mot Cloudflare Pages-sidan; redirect triggar captive-portal-rutan på **iOS och Android**.
- [ ] "Fortsätt till internet"-knapp implementerad och anropar UniFi authorize-endpoint — en testenhet får **faktiskt** internet efter klick.
- [ ] `content.json` uppdateras via ny mekanism (BackgroundTasks/edge-KV) eller statisk fil i bucket; portalen visar rätt sektion för vardag/söndag/event.
- [ ] README uppdaterad (n8n borta); `docs/12-operations.md` beskriver drift.
- [ ] `make test` grönt inkl. wifi-portal-testet; deployad till `kyrka-wifi`.
- [ ] Verifierat på minst en riktig enhet i lokalen (iOS + Android).

### Alt. B — Hold (klart när):
- [ ] README + denna issue tydligt märkta "ej i drift / väntar på beslut".
- [ ] n8n-referensen borttagen ur README (så den inte ljuger).
- [ ] Portalen borttagen ur `deploy-sites` (deployas inte halvfärdig).
- [ ] CI-testet behållet grönt men markerat icke-blockerande, eller medvetet kvar.
- [ ] Koden orörd och återanvändbar; beslut A/C schemalagt till **namngiven** framtida sprint.

### Alt. C — Avveckla (klart när):
- [ ] `frontend/wifi-intake-portal/` borttagen.
- [ ] Content-bucketen (`*-wifi-portal-content`) borttagen ur Terraform **och applad** i dev + prod.
- [ ] CI-jobbet `wifi-intake-portal (Node)` + rader i `Makefile`/`deploy-sites` borttagna.
- [ ] Alla README/docs-referenser borttagna.
- [ ] `make test` grönt; `grep -r wifi-intake-portal` ger inga döda referenser.
