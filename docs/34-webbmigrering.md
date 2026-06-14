# 34 — Webbmigrering: ersätt `teklehaymanot.se/a/` med portalen

> Beslut och plan för att lägga ner den gamla WordPress-sajten och låta den
> nya plattformen (member-portal + admin-web) vara församlingens webb.
> Beslutsunderlaget är data-drivet (inventering nedan). Komplement till
> [25-deploy-och-innehallsflode.md](25-deploy-och-innehallsflode.md) (KV-flödet)
> och [32-driftoverlamning-och-portabilitet.md](32-driftoverlamning-och-portabilitet.md).

## 1. Inventering av den gamla sajten (data, 2026-06-14)

Hämtat via WordPress REST API (`/a/wp-json/wp/v2/...`):

| Mått | Värde |
|---|---|
| Plattform | **WordPress** (wp-content/wp-includes/wp-json bekräftat) |
| Sidor (`pages`) | **1** — `sample-page` ("ቀዳሚ ገጽ"), WP:s standard-sida |
| Inlägg (`posts`) | **~50**, enbart **amhariska**, **2014–2020** (nyaste 2020-06-21) |
| Media | **36** filer |
| Aktivitet | **Vilande sedan 2020** (~5 år) |

Slutsats: `/a/` är en **vilande amharisk blogg**, inte en funktionsrik sajt.
Den saknar allt portalen redan har (medlemskap, gåvor, kalender, livestream,
certifikat, bidrag, tvåspråkighet, PWA). Det finns **inget funktionellt att
integrera** — värdet är ett fåtal tidlösa texter + de 36 bilderna.

## 2. Beslut: fortsätt på portalen, skörda innehåll, lägg ner WordPress

Att behålla/integrera WordPress återinför precis den underhålls-, säkerhets- och
persondependens vi dokumenterat oss bort från ([32](32-driftoverlamning-och-portabilitet.md)).
Vi **ersätter** den, **kurerar** ~8–10 tidlösa stycken och **AI-översätter** dem
till svenska (translatorn är nu inkopplad) — en innehållsuppgradering, inte bara
en flytt.

## 3. Återanvändningsmatris

| Gammalt innehåll (översättning) | Behåll? | Ny plats |
|---|---|---|
| ታሪክ (historik) | ✅ | Om oss |
| ቃለ አዋዲ / መተዳደሪያ ደንብ (stadgar) | ✅ | Om oss / "Stadgar" |
| ካህናት (präster/klerus) | ✅ | Om oss / Kontakt |
| አገልግሎት (tjänster/verksamhet) | ✅ | Om oss |
| ያግኙን (kontakt) | ✅ | Kontakt (verifiera adress/telefon) |
| Undervisning — ሰሙነ ሕማማት, የትንሣኤው ትርጉም, ጾምና ጥቅሙ, ክርስቲያናዊ ሥነ ምግባር, መስቀል | ✅ (återkommer årligen) | Bibliotek / ny "Undervisning" |
| ወጣትነት በቤተክርስቲያን (ungdom) | ✅ | Söndagsskola / ungdom |
| Datumstämplade årsprogram (2014 påsk m.m.), dubbletter | ❌ arkiveras | — |
| Interna konfliktinlägg (2014: ቅጣት / Vårby skolan) | ❌ utelämnas | — |
| 36 bilder | ✅ | Re-hostas som WebP i portal/KV |
| WordPress-tema/PHP/plugins | ❌ | Annan stack; återinför bördan |
| Domän & SEO | ✅ | `teklehaymanot.se` → Cloudflare Pages + 301-redirects |

## 4. Migreringssteg

1. **Export** (klart): `wp-json`-dump av `posts` (slug/date/title/content) +
   medialista (`teklehaymanot-posts.json`, `teklehaymanot-media.txt`).
2. **Kurera** de tidlösa styckena per §3 (släpp daterade event + konflikter +
   dubbletter).
3. **AI-översätt** varje behållen text am→sv via translatorn → tvåspråkigt.
4. **Mappa** in i KV-innehållsmodellen (`kyrka_content`) / portalsidor; lägg
   ev. till en "Undervisning"-sektion om teaching-innehåll ska visas.
5. **Bilder**: ladda ner de 36, optimera till WebP, hosta i portalen.
6. **Domän-cutover**: peka `teklehaymanot.se` mot Cloudflare Pages; lägg
   **301-redirects** från indexerade gamla URL:er (SEO).
7. **Avveckla** WordPress-installen (ta bort en hel säkerhets-/underhållsyta).

## 5. Agent vs. människa

- 🤖 Agent: export-parsning, kurering enligt regler, AI-översättning, KV-mappning,
  redirect-karta, WebP-konvertering.
- 🧑 Människa: godkänn vilka texter som behålls (redaktionellt/teologiskt),
  domän-DNS-cutover, slutlig avveckling av WordPress-kontot/hostingen.

## 6. Nästa steg

Bearbeta `teklehaymanot-posts.json` → producera (a) kurerad lista, (b) am→sv-
översättningar, (c) KV-/sid-innehåll, (d) redirect-karta. Därefter människo-
granskning och cutover.

## 7. Genomförd skörd — Nacka (status)

Den repeterbara skörden är körd för **Nacka** (Abune Tekle Haymanot =
teklehaymanot.se). Den gamla WordPress-databasen (49 inlägg) kemtvättades:
dubbletter, nästan tomma poster, daterade event och interna konfliktinlägg
 filtrerades bort → **21 bestående artiklar** (mest kateketiskt material:
ዐቢይ ጾም-serien, ሰሙነ ሕማማት, ትንሣኤ, kristen etik, högtider, historik, ungdom).

- Innehållet ligger i **`frontend/member-portal/churches/nacka/teachings.json`**
  (samma per-kyrka-modell som `content.json`), kategoriserat och tvåspråkigt
  förberett: **fullständig amharisk originaltext** (omedelbart värde för
  medlemmarna) + **svenska titlar**; historiken är **helt översatt** (märkt som
  redaktionellt utkast pga tidigare namn/plats). Övriga svenska översättningar
  är flaggade *"under granskning"* och fylls på efter teologisk granskning.
- Renderas i **Bibliotek** via en tillgänglig, tvåspråkig sektion
  (`<details>` — tangentbord/skärmläsare, läsbar radlängd, inga externa
  skript), som visar amhariskan alltid och svenskan när den är klar.
- `churches/stockholm/teachings.json` finns som **tom struktur** — redo för
  Hagsätras skörd med samma metod när den kyrkans sajt finns.

**Playbook-bekräftelse:** detta *är* metoden för att ta in övriga kyrkor —
peka skörden mot kyrkans gamla sajt, skriv till `churches/<slug>/teachings.json`,
samma Bibliotek-renderare visar den. Inget per-kyrka-specialfall i koden.
