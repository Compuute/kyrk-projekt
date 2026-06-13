# 26 — PWA-mätning & mobilapp-beslutet (A → B på siffror)

Det här dokumentet förklarar **varför** medlemsportalen redan är en mobilapp i
allt utom namn, **vilka få anonyma siffror** vi samlar för att kunna fatta nästa
beslut, och **exakt vilka trösklar** som flyttar oss från en ren PWA (väg A) till
en butikspaketerad app (väg B).

---

## 1. Beslutet: PWA nu, app-paketering på mätbar tröskel

`docs/03-mvp-scope.md` slår redan fast under *Out of scope*:

> "Member-facing mobile app (native) — **PWA covers this**"

Det beslutet står fast. Det vi saknade var **data** för att veta *när* det blir
fel. Tre vägar utvärderades:

| Väg | Vad | Jobb | App Store | Underhåll |
|-----|-----|------|-----------|-----------|
| **A. PWA (nu)** | Installerbar Eleventy-PWA på Cloudflare Edge | — | Nej | En kodbas |
| **B. Wrappa PWA** | Capacitor/TWA paketerar samma PWA till app | Medel | Ja | En kodbas |
| **C. Native** | React Native/Flutter, separat kod | Stort | Ja | Dubbelt |

Väg C är utesluten så länge volymen är låg (det bryter mot "0 dependencies, låg
drift"-principen). Frågan är bara **A → B**, och den ska avgöras av siffror, inte
magkänsla. Tidigare gick det inte: portalen är byggd *zero tracking, zero
cookies* (`frontend/member-portal/README.md`), så vi hade ingen mätning alls.

Det här dokumentet stänger den luckan — med minsta möjliga, integritetsbevarande
mätning.

---

## 2. Vad vi mäter (och inte)

Anonyma **aggregerade räknare** i KV-namespacet `kyrka_metrics` (zon: **YELLOW**).
Endpoint: `functions/m.ts` (`POST /m`). Sändaren: `trackEvent()` i `app.ts`.

| Händelse | Betyder | Används till |
|----------|---------|--------------|
| `app_open` | en enhet öppnade appen (max 1/dygn/enhet) | DAU, retention-nämnare |
| `pwa_install` | PWA:n installerades på hemskärm | installations-adoption |
| `push_prompt` | notis-frågan visades | opt-in-rate (nämnare) |
| `push_grant` | användaren tillät notiser | opt-in-rate (täljare) |
| `push_deny` | användaren nekade notiser | friktion |
| `retain_w1/_w2/_w4/_w12` | enhet fortfarande aktiv 1/2/4/12 veckor efter första öppning | retention-kurva |

**Push opt-in-rate** = `push_grant / push_prompt`.
**Retention vecka N** = `retain_wN / pwa_install` (eller `/ app_open`-kohort).

Vi mäter **aldrig**: IP-adress, identifierare, sidvägar, klick, enhets-id,
geografi, eller något PII. Inga tredjepartsverktyg (ingen GA, ingen pixel).

---

## 3. Hur mätningen bevarar integriteten

Tre egenskaper gör det här *ospårbart* och därför utanför "tracking"-löftet:

1. **Ingen identifierare skickas någonsin.** Varje beacon innehåller bara ett
   ord ur en fast allowlist (`{ "e": "app_open" }`). Edgen kan inte koppla två
   beacons till samma enhet — den ökar bara en dygnsräknare.
2. **Retention räknas lokalt, rapporteras anonymt.** Enheten håller själv reda på
   sitt första öppningsdatum i `localStorage` och skickar `retain_wN` *en gång*
   när en milstolpe nås. Servern ser "någon enhet nådde vecka N", aldrig vem.
   Det här är kohort-räkning utan kohort-id.
3. **Respekterar bortval.** `trackEvent()` tystnar om `navigator.doNotTrack`
   är satt eller om `localStorage['metricsOptOut'] === 'true'`. Beaconen använder
   `credentials: 'omit'` — inga cookies följer med.

Ingress-validering (`ALLOWED_EVENTS.includes(...)` i `functions/m.ts`) gör att
endpointen inte kan bli en fritext-sink. Räknare självdör efter 90 dagar (TTL).

### Den ärliga varningen (ePrivacy / PECR)
Mätningen behandlar **ingen personuppgift** (GDPR) — men den *skriver till
`localStorage`* för avdubblering. Lagring på användarens enhet för
analysändamål är enligt ePrivacy art. 5.3 normalt **inte** "strikt nödvändig"
och kan kräva samtycke, till skillnad från de funktionella språk-/församlings-
kakorna. Vi mildrar genom DNT-respekt + opt-out, men **personuppgiftsansvarig
ska ta ställning** till om en lättviktig samtyckes-/informationsrad behövs
(se GDPR-registret §5). Detta är medvetet flaggat, inte dolt.

---

## 4. A → B-trösklar (revidera om 1–2 kvartal)

Samla siffror i **ett–två kvartal**, läs sedan av. Gå från PWA (A) till
butikspaketering (B, Capacitor) **om något av följande är sant och mätt**:

1. **Installations-adoption planar ut lågt** — t.ex. < 15 % av återkommande
   `app_open`-enheter har en `pwa_install`, trots en synlig install-prompt.
2. **Push-opt-in är hög men leveransen sviktar på iOS** — `push_grant`-rate är
   god men retention bland push-opt-in-enheter ligger inte över icke-opt-in
   (tecken på att webb-push på iOS är opålitlig för målgruppen).
3. **Retention läcker tidigt** — `retain_w4 / pwa_install` < ~20 %, vilket tyder
   på att "appen" inte upplevs som en app (butiksikon + notiser kan hjälpa).
4. **App Store blir en reell upptäcktskanal** — kvalitativt: medlemmar (särskilt
   äldre) söker i butiken i stället för webben.

Om inget av detta inträffar: **stanna på A**, fortsätt mäta, omvärdera nästa
kvartal. Beslutet loggas som ADR-018 i `docs/14-architecture-decisions.md`.

---

## 5. Nästa konkreta steg (oberoende, små)

1. Skapa KV-namespacet: `wrangler kv:namespace create kyrka_metrics` → klistra in
   id:t i `frontend/member-portal/wrangler.toml`.
2. Sätt `METRICS_TOKEN` som Pages-secret för att kunna läsa aggregaten
   (`GET /m` med headern `x-metrics-token`).
3. Lägg en "Aktivera notiser / ማሳወቂያ አንቃ"-knapp som anropar
   `window.requestPushPermission()` (mäter opt-in-rate). Knappen är medvetet
   *inte* auto-triggad — ingen påträngande prompt vid laddning.
4. Efter 1–2 kvartal: läs av mot trösklarna i §4.

---

## Status (beslut 2026-06-13): UPPSKJUTET — vilande

Mobilapp (A→B) och PWA-mätning **skjuts upp tills vidare**. Vi går framåt utan
app.

- **Mätningen är vilande:** `METRICS_ENABLED = false` i `app.ts`, ingen deploy,
  inget `kyrka_metrics`-KV skapat. Den samlar **ingenting**. Integritetspolicyn
  och GDPR-registret §5 säger därför (korrekt) att ingen mätning sker.
- **Koden är byggd och deploy-redo** — återaktivering är billig.
- **Trigger för att återuppta:** *kvalitativ* efterfrågan, inte ett datum —
  medlemmar som frågar efter en app, eller pastor/admin som ser
  installationsfriktion. (Medan mätningen är av kan efterfrågan inte ses
  kvantitativt, och det är ett medvetet val.)
- **När triggern slår in:** sätt `METRICS_ENABLED = true` (CI-tripwiren tvingar
  då fram uppdatering av integritetspolicyn + GDPR §5 + ePrivacy-beslut),
  aktivera enligt §5, kör 1–2 kvartal, fatta A→B mot §4-trösklarna.
