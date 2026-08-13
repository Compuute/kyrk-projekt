# 35 — Kyrko-multitenancy och onboarding

> Hur de olika kyrkorna hålls åtskilda i systemet, och vad som krävs för att
> onboarda en ny kyrka. Skrivet efter att isoleringen verifierats mot koden
> 2026-06-14. Relaterat: [06-auth-strategy.md](06-auth-strategy.md),
> [29-identitets-och-iam-principer.md](29-identitets-och-iam-principer.md),
> zonmodellen i [01-architecture-red-yellow-green.md](01-architecture-red-yellow-green.md).

---

## 1. Tenant-modellen

**En kyrka = en Zitadel-org. `church_id` = org-id.**

Varje inloggad användares `church_id` kommer från deras Zitadel-org (claim
`urn:zitadel:iam:org:id`), bärs i JWT:n och fylls i `Actor`/`SessionInfo` i
varje tjänst. All data stämplas med utfärdarens `church_id` från sessionen —
**aldrig** från formulärinmatning — så en kyrka kan inte skapa data åt en
annan.

Konsekvens: kyrko-gränsen är bara verklig om varje kyrka faktiskt är sin egen
org i Zitadel. Ligger flera kyrkor i samma org delar de `church_id` och ser
varandras data — hur väl koden än isolerar. Det är därför onboarding (§3)
börjar med att skapa org:en.

> **Dev-läget just nu:** alla testanvändare ligger i samma org
> (`376713621675772982`). Därför ser man "allt" i dev — det är tekniskt en
> kyrka. Separationen blir verklig först när varje kyrka är egen org.

## 2. Var isoleringen sitter (verifierat)

Isoleringen är påtvingad i domän-/servicelagret i varje tjänst, inte i UI:t,
och täcks av tester:

| Område | Mekanism | Bevis |
|---|---|---|
| Certifikat — hämta/ladda ner | `_load_scoped`: `cert.church_id != actor.church_id` → 404 | certificate_service.py |
| Certifikat — lista | `list_for_church` → `repo.list_by_church(actor.church_id)` | test_list_returns_only_own_church |
| Söndagsskola — grupper/närvaro | filtreras på `church_id`; lärare ser bara egna grupper | test_groups_are_church_isolated |
| Begravning | `list_cases(session.church_id)` | test_church_isolation |
| Intake/gåvor | scopas på `church_id` i listningar | — |

Den publika verify-endpointen (`/certificates/verify/{id}`) returnerar bara
icke-PII (typ, datum, kyrkonamn, status) — aldrig namn — och är medvetet
öppen så vem som helst kan kontrollera äkthet.

Regel för nya vyer: **varje listning/uppslag som rör kyrkodata måste scopas
på `actor.church_id`**, och få ett isolationstest (kyrka A ser inte kyrka B).

## 3. Onboarda en kyrka

Spåras i epic [#113](https://github.com/Compuute/kyrk-projekt/issues/113);
en issue per kyrka (#104–#112). Ordning:

1. **Skapa Zitadel-org** för kyrkan. Notera org-id → detta är kyrkans
   `church_id` i produktion.
2. **Skapa admin-användare** + tilldela rollen `admin`. Lägg till
   pastor-/lärar-användare med roller (`pastor`, `editor`, `teacher`) efter
   behov. Roller styr vad man får göra; org:en styr vilken kyrka man tillhör.
3. **Verifiera churches.json** — namn (sv/am) + stad. Kanonisk källa är
   `frontend/member-portal/churches.json`; admin-web har en guardad kopia
   (`app/data/churches.json`, skyddad av `tests/test_churches_sync.py`).
   Ändra alltid den kanoniska och synka — patcha aldrig en kopia.
4. **KV-config / content.json** för medlemsportalen (swish/bankgiro/avgifter
   per kyrka).
5. **Skapa söndagsskolegrupper** (Grunderna, Fortsättning, Krar, Begena ...)
   via admin-web → Söndagsskola.
6. **Röktest av isolering:** logga in som kyrkan, utfärda ett testcertifikat,
   och bekräfta från en annan kyrkas inloggning att det **inte** syns.

## 4. Två identiteter att inte blanda ihop

- **`church_id` (Zitadel-org)** — tenant-gränsen. Vem ser vad.
- **`church_id`-slug i churches.json** (`nacka`, `stockholm`, ...) — används
  för att slå upp tvåspråkiga *visningsnamn* (t.ex. på certifikatet). Det är
  inte samma sak som org-id. Certifikatet stämplas med org-id för isolering;
  det visade kyrkonamnet kommer från den valda slug-kyrkan. Båda behövs.

## 5. Roller (sammanfattning)

`admin`, `pastor`, `editor`, `viewer`, `teacher`. Kanoniska auth-adaptrar i
`libs/shared-auth/` (synkas till tjänsterna, guardas av
`tests/test_shared_auth_sync.py`). Exempel: certifikat utfärdas av
`admin`/`pastor`; söndagsskolenärvaro tas av `teacher` (bara egna grupper);
`viewer` är läsbehörighet.
