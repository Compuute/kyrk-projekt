# 31 — Versionering och releaser

Hur en commit blir en **spårbar version** i prod. Målet är GitOps-provenance:
varje deployad artefakt ska kunna pekas tillbaka till exakt en oföränderlig
git-ref, så att "vad kör i prod?" och "rulla tillbaka till X" har entydiga svar.

## Schema

- **Semver** `vMAJOR.MINOR.PATCH` på `main`, som **annoterade** taggar.
- **0.x** = pre-produktion (funktionsuppbyggnad före skarp data). Bump till
  **1.0.0** när första skarpa onboardingen sker.
- `package.json` `version` hålls i synk med senaste taggen (utan `v`-prefix).

## RULE 3 — released tags är oföränderliga

En pushad `vX.Y.Z` flyttas **aldrig**. En korrigering shippar som nästa version
(`vX.Y.Z+1`), även om originalet är minuter gammalt. Att tvinga om en tagg
bryter den spårbara evidens-kedjan som är hela poängen. (Interna `-rc`/`-alpha`
får flyttas; släppta semver-taggar får inte.)

## Skär en release

```bash
scripts/release.sh 0.2.0          # bumpar package.json + skapar annoterad tagg v0.2.0
git show v0.2.0                   # granska
git push origin main v0.2.0       # pusha commit + tagg
```

Committer/tagger måste vara människan (Compuute), aldrig ett AI-verktyg
(AI-RULES.md RULE 4) — verifieras av `commit-hygiene`-gaten.

## Deploya en version (deploy-from-tag)

Backend (`deploy.yml`) deployar **från en tagg**, inte en lös branch:

1. Actions → **deploy** → Run workflow → välj **ref = `v0.2.0`**, environment = `dev`/`prod`.
2. `version`-jobbet kör `git describe --tags` → `v0.2.0` och stämplar den i:
   - **image-taggar** (`…/<service>:v0.2.0` utöver `:<sha>`),
   - **`APP_VERSION`** env på varje Cloud Run-tjänst,
   - **deploy-sammanfattningen** (vad som gick live).
3. Prod kräver manuellt godkännande (CLAUDE.md Forbidden Actions).

Frontend (Cloudflare Pages) auto-bygger `main`; en frontend-release motsvarar
den tagg vars commit Pages senast byggde.

## Rollback

Deploya helt enkelt föregående tagg: Run workflow → ref = `v0.1.0`. Eftersom
images är taggade per version finns föregående artefakt kvar — inget ombygge.

## Läs av vad som kör

- Cloud Run: `APP_VERSION` i tjänstens env (eller deploy-sammanfattningen).
- Image: `…/<service>:vX.Y.Z` i Artifact Registry.
- Git: `git describe --tags <sha>` mappar en commit till närmaste release.
