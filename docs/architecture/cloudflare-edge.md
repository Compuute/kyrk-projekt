# Architecture: Cloudflare Edge Layer

## System architecture

```
                              INTERNET
                                 │
                     ┌───────────┴───────────┐
                     │     CLOUDFLARE         │
                     │  DNS + CDN + WAF +     │
                     │  DDoS + Bot detect     │
                     │  (free tier)           │
                     └───────────┬───────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
    ┌─────────┴─────────┐ ┌─────┴──────┐  ┌────────┴────────┐
    │ Cloudflare Pages  │ │ Cloudflare │  │  Cloudflare     │
    │ (static, edge)    │ │ Pages      │  │  proxy → GCP    │
    │                   │ │ (static)   │  │  Cloud Run      │
    │ member-portal     │ │ wifi-      │  │                 │
    │ kyrka.se          │ │ intake-    │  │  api.kyrka.se   │
    │ sv + am           │ │ portal     │  │                 │
    └───────────────────┘ └────────────┘  └────────┬────────┘
                                                    │
                                          ┌─────────┴─────────┐
                                          │  GCP Cloud Run    │
                                          │  europe-north1    │
                                          │                   │
                                          │  membership-      │
                                          │   intake (RED)    │
                                          │   --allow-unauth  │
                                          │                   │
                                          │  membership-      │
                                          │   service (RED)   │
                                          │   --no-allow      │
                                          │   + KMS access    │
                                          │                   │
                                          │  certificate-     │
                                          │   service (RED)   │
                                          │   --no-allow      │
                                          │                   │
                                          │  reporting-       │
                                          │   service (YELLOW)│
                                          │   --no-allow      │
                                          │   + BigQuery      │
                                          │                   │
                                          │  admin-web        │
                                          │   --allow-unauth  │
                                          │   (no data, UI)   │
                                          └─────────┬─────────┘
                                                    │
                                          ┌─────────┴─────────┐
                                          │  GCP Data Layer   │
                                          │  (EU only)        │
                                          │                   │
                                          │  Firestore (CMEK) │
                                          │  Cloud KMS        │
                                          │  BigQuery         │
                                          │  Secret Manager   │
                                          │  Cloud Storage    │
                                          └───────────────────┘
```

**Edge compute (Pages Functions).** The member-portal is not purely static: a
Cloudflare Pages Function (`functions/_middleware.ts`) runs at the edge on every
HTML request. It does the language-prefix redirect (`/sv`, `/am`), reads the
visitor's `selected_church`/`selected_language` cookies, pulls that church's
config from **Workers KV** (`kyrka_content`), and injects it into the page via
`HTMLRewriter` — so per-church content is rendered at the edge with no origin
round-trip. The same hook point evaluates **feature flags** (`docs/27`) when
active. **Auth** is Zitadel Cloud OIDC (ADR-016): `admin-web` runs the
authorization-code flow; downstream services verify bearer tokens against
Zitadel's JWKS (see sequence 5).

## Sequence diagrams

### 1. Member visits the church website

```
Member          Cloudflare Pages         Pages Function          Workers KV
Browser         (static dist/)           _middleware.ts          (kyrka_content)
  │                   │                       │                       │
  │ GET /             │                       │                       │
  ├──────────────────►│ onRequest             │                       │
  │                   ├──────────────────────►│                       │
  │                   │        no /sv|/am prefix → read cookie/       │
  │                   │        Accept-Language → 302 /sv/             │
  │  302 → /sv/       │                       │                       │
  │◄──────────────────┼───────────────────────┤                       │
  │ GET /sv/          │                       │                       │
  ├──────────────────►├──────────────────────►│                       │
  │                   │   fetch base HTML from ASSETS (dist/)         │
  │                   │◄──────────────────────┤                       │
  │                   │   read selected_church cookie → get config    │
  │                   │                       ├──────────────────────►│
  │                   │                       │◄──────────────────────┤
  │                   │   HTMLRewriter: inject window.__KYRK_CONFIG__ │
  │                   │   (+ window.__KYRK_FLAGS__ when flags active),│
  │                   │   set lang display CSS, set selected_language │
  │  HTML (config     │                       │                       │
  │  already inlined) │                       │                       │
  │◄──────────────────┼───────────────────────┤                       │
  │                   │                       │                       │
  │ Switch language → client-side swap (no request);                  │
  │ church switch → set cookie, edge re-renders on next nav           │
  │                   │                       │                       │
```

**Latency:** ~20ms (edge-served, config inlined at the edge from KV — no
separate content.json round-trip). No cold start. No container boot.

### 2. New member submits intake form

```
Member          Cloudflare          Cloudflare       Cloud Run         Firestore
Browser         WAF + DDoS          Proxy            membership-intake
  │                │                   │                │                │
  │ POST /intake   │                   │                │                │
  ├───────────────►│                   │                │                │
  │                │ WAF check         │                │                │
  │                │ (SQL injection,   │                │                │
  │                │  XSS, bot score)  │                │                │
  │                │───────┐           │                │                │
  │                │ pass  │           │                │                │
  │                │◄──────┘           │                │                │
  │                │ forward to proxy  │                │                │
  │                │──────────────────►│                │                │
  │                │                   │ proxy to CR    │                │
  │                │                   ├───────────────►│                │
  │                │                   │                │ rate limit     │
  │                │                   │                │ check (app)    │
  │                │                   │                │───────┐        │
  │                │                   │                │ pass  │        │
  │                │                   │                │◄──────┘        │
  │                │                   │                │ validate       │
  │                │                   │                │ (Pydantic)     │
  │                │                   │                │ store pending  │
  │                │                   │                ├───────────────►│
  │                │                   │                │◄───────────────┤
  │                │                   │                │ queue          │
  │                │                   │                │ BackgroundTask │
  │                │                   │                │ (notify admin) │
  │  202 Accepted  │                   │                │                │
  │◄───────────────┼───────────────────┼────────────────┤                │
  │                │                   │                │                │
```

**Defense layers traversed:** Cloudflare DDoS → Cloudflare WAF → Cloudflare bot detect → App rate limiter → Pydantic validation → Firestore write = **6 layers**.

### 3. Admin approves intake + generates grant application

```
Admin           Cloudflare       Cloud Run        Cloud Run          Cloud Run        Anthropic
Browser         Proxy            admin-web        membership-intake  reporting-svc    API
  │                │                │                │                  │                │
  │ POST /submit-  │                │                │                  │                │
  │  ions/{id}/    │                │                │                  │                │
  │  approve       │                │                │                  │                │
  ├───────────────►│───────────────►│                │                  │                │
  │                │                │ forward token  │                  │                │
  │                │                ├───────────────►│                  │                │
  │                │                │                │ forward token    │                │
  │                │                │                │ to membership-   │                │
  │                │                │                │ service (POST    │                │
  │                │                │                │ /members)        │                │
  │                │                │                │ ─── ─── ─── ──► │                │
  │                │                │                │ ◄── ─── ─── ─── │                │
  │                │                │                │ mark approved    │                │
  │                │                │                │ + redact PII     │                │
  │  303 redirect  │                │                │                  │                │
  │◄───────────────┼────────────────┼────────────────┤                  │                │
  │                │                │                │                  │                │
  │ POST /grants/  │                │                │                  │                │
  │  arv.../       │                │                │                  │                │
  │  generate      │                │                │                  │                │
  ├───────────────►│───────────────►│                │                  │                │
  │                │                │ get KPI data   │                  │                │
  │                │                ├────────────────┼─────────────────►│                │
  │                │                │◄───────────────┼──────────────────┤                │
  │                │                │ render draft   │                  │                │
  │                │                │ (template +    │                  │                │
  │                │                │  KPI numbers)  │                  │                │
  │  HTML draft    │                │                │                  │                │
  │◄───────────────┼────────────────┤                │                  │                │
  │                │                │                │                  │                │
```

### 4. Quarterly OpenClaw analysis (scheduled runtime agent)

> Trigger is **Cloud Scheduler** (n8n was decommissioned — ADR-015). This is the
> "report agent" pattern from the [Agent Operating Model](../governance/agent-operating-model.md)
> / [doc 28](../28-agentisk-driftmodell.md): scheduler → worker → sanitizer → LLM
> → pending → human approval. The sanitizer (whitelist) is the PII guarantee.

```
Cloud           Cloud Run          Sanitizer        Anthropic       Firestore
Scheduler       reporting-svc      (in service)     API             (pending review)
  │                │                  │                │                │
  │ GET /reports/  │                  │                │                │
  │ board-export   │                  │                │                │
  ├───────────────►│                  │                │                │
  │◄───────────────┤                  │                │                │
  │ YELLOW data    │                  │                │                │
  │                │                  │                │                │
  │ run sanitizer  │                  │                │                │
  │ (yellow-only   │                  │                │                │
  │  profile)      │                  │                │                │
  ├────────────────┼─────────────────►│                │                │
  │                │                  │ check fields   │                │
  │                │                  │ against        │                │
  │                │                  │ whitelist      │                │
  │                │                  │───────┐        │                │
  │                │                  │ pass  │        │                │
  │◄───────────────┼──────────────────┤◄──────┘        │                │
  │                │                  │                │                │
  │ call Anthropic │                  │                │                │
  │ with template  │                  │                │                │
  │ + sanitized    │                  │                │                │
  │   data         │                  │                │                │
  ├────────────────┼──────────────────┼───────────────►│                │
  │                │                  │                │ structured     │
  │                │                  │                │ JSON response  │
  │◄───────────────┼──────────────────┼────────────────┤                │
  │                │                  │                │                │
  │ validate       │                  │                │                │
  │ response       │                  │                │                │
  │ schema         │                  │                │                │
  │                │                  │                │                │
  │ store as       │                  │                │                │
  │ pending_review │                  │                │                │
  ├────────────────┼──────────────────┼────────────────┼───────────────►│
  │                │                  │                │                │
  │ notify admin   │                  │                │                │
  │ (Telegram)     │                  │                │                │
  │                │                  │                │                │
```

### 5. Admin login + downstream auth (Zitadel OIDC)

> Auth migrated from PropelAuth to **Zitadel Cloud** (ADR-016). `admin-web` runs
> the OIDC authorization-code flow; downstream services verify the bearer token
> locally against Zitadel's JWKS. The JWKS fetch is the trust anchor for every
> session — it is fetched over **TLS with certificate + hostname verification**
> (a prior `CERT_NONE` bypass was removed; a repo guard now blocks reintroducing
> it). Region caveat: the instance is currently US-region on the free tier until
> the EU move — see ADR-017.

```
Admin        admin-web         Zitadel          membership-service   Zitadel
Browser      (JWTSession)      (OIDC IdP)        (ZitadelAuthAdapter) JWKS endpoint
  │              │                 │                   │                  │
  │ GET /admin   │                 │                   │                  │
  ├─────────────►│ no session →    │                   │                  │
  │              │ 302 to Zitadel  │                   │                  │
  │  302 login   │                 │                   │                  │
  │◄─────────────┤                 │                   │                  │
  │ login at Zitadel (sv/am)       │                   │                  │
  ├───────────────────────────────►│                   │                  │
  │  302 /login/callback?code=...  │                   │                  │
  │◄───────────────────────────────┤                   │                  │
  │ GET /callback?code             │                   │                  │
  ├─────────────►│ exchange code   │                   │                  │
  │              ├────────────────►│ /oauth/v2/token   │                  │
  │              │◄────────────────┤ id_token (RS256)  │                  │
  │              │ set kyrk_session│                   │                  │
  │  303 + cookie│ (HttpOnly)      │                   │                  │
  │◄─────────────┤                 │                   │                  │
  │              │                 │                   │                  │
  │ action needing a RED service (bearer = OIDC token) │                  │
  ├─────────────►├────────────────────────────────────►│                  │
  │              │                 │   verify token:   │ GET /oauth/v2/   │
  │              │                 │   fetch JWKS      │ keys (TLS-VERIFY)│
  │              │                 │                   ├─────────────────►│
  │              │                 │                   │◄─────────────────┤
  │              │                 │   RS256 sig + iss/aud/exp + role +    │
  │              │                 │   church scope (org-id → portal slug) │
  │              │                 │   → Actor, or 401/403                 │
  │   result     │                 │                   │                  │
  │◄─────────────┼─────────────────────────────────────┤                  │
  │              │                 │                   │                  │
```

**Trust anchor:** the JWKS fetch. If its TLS verification were disabled, a MITM
could serve forged signing keys and forge admin tokens — which is why the
`CERT_NONE` bypass was removed across all five auth adapters and a guard test
(`test_project_security_guard`) blocks its return.

## What Cloudflare sees vs what GCP sees

| Data | Cloudflare sees | GCP sees |
|---|---|---|
| HTTP request URL | Yes | Yes |
| HTTP headers (incl. bearer token) | Yes (encrypted in transit) | Yes |
| Request body (intake form data) | Yes (encrypted in transit) | Yes |
| Firestore documents | **No** | Yes |
| KMS keys / plaintext | **No** | Yes |
| BigQuery data | **No** | Yes |
| Secret Manager values | **No** | Yes |
| Decrypted personnummer | **No** | Yes (only in membership-service process memory) |

**Cloudflare is a transport-layer proxy.** It sees HTTP traffic but never
accesses the data layer. All persistent storage, encryption, and secrets
stay in GCP EU. This is why adding Cloudflare does not weaken our
security model — it's a shield in front, not a replacement for what's
behind.

## DNS configuration

```
kyrka.se                → Cloudflare Pages (member-portal)
www.kyrka.se            → CNAME to kyrka.se
wifi.kyrka.se           → Cloudflare Pages (wifi-intake-portal)
api.kyrka.se            → Cloudflare proxy → Cloud Run (membership-intake)
admin.kyrka.se          → Cloudflare proxy → Cloud Run (admin-web)
internal.kyrka.se       → Cloud Run direct (membership-service, certificate-service, reporting-service)
                          NOT proxied — internal services talk to each other via Cloud Run URLs
```

**Only public-facing endpoints go through Cloudflare.** Internal
service-to-service communication (e.g., intake → membership-service
during approval) goes directly via Cloud Run service URLs, never
through Cloudflare. This means:
- No Cloudflare latency on internal calls
- No Cloudflare dependency for service-to-service communication
- If Cloudflare goes down, internal operations continue

## Failure modes and rollback

| Scenario | Impact | Detection | Rollback |
|---|---|---|---|
| **Cloudflare global outage** | Static sites + proxied endpoints down. Internal services unaffected. | Cloudflare status page + external monitoring | Change DNS A-records to direct Cloud Run URLs (5 min). Static sites temporarily unavailable until DNS propagates. |
| **Cloudflare Pages deploy broke** | Wrong content on portal | Visual check after deploy | `wrangler pages deployment rollback` (instant) |
| **Cloudflare WAF false positive** | Legitimate requests blocked (403) | User reports + Cloudflare analytics | Cloudflare dashboard → Security → WAF → disable the specific rule |
| **Cloudflare cache serving stale content** | Old content visible after update | Check `cf-cache-status` header | Cloudflare dashboard → Caching → Purge Everything. Or: add `?v=2` cache-buster to content.json URL. |
| **GCP Cloud Run outage** | Dynamic services down. Static sites still served from Cloudflare edge. | e2e.yml healthz fails | Cloud Run revision rollback. Static sites unaffected. |

## Ops troubleshooting guide

### "The website is down"

1. Check `https://www.cloudflarestatus.com/` — is it a Cloudflare outage?
   - **Yes →** flip DNS to direct Cloud Run URLs. Static sites are temporarily down.
   - **No →** continue to step 2.

2. `curl -I https://kyrka.se` — what does the response look like?
   - `cf-cache-status: HIT` → Cloudflare is serving from cache. The site is up.
   - `cf-cache-status: MISS` + 200 → Cloudflare fetched from origin. Working.
   - `cf-cache-status: MISS` + 5xx → Origin (GCS or Cloud Run) is down. Check GCP.
   - No `cf-` headers → DNS is not pointing to Cloudflare. Check DNS.

3. Check Cloudflare Analytics → Security → check for blocked requests.

### "The API returns 403"

1. Is it Cloudflare WAF blocking the request?
   - `curl -v https://api.kyrka.se/intake` — look for `cf-mitigated: challenge` header.
   - **Yes →** Cloudflare WAF false positive. Dashboard → Security → WAF → check the rule → add an exception for `/intake`.
   - **No →** the service rejected the token (role check). The `ZitadelAuthAdapter`
     verifies the OIDC bearer token's RS256 signature against Zitadel's JWKS and
     checks the role claim. A 403 means a valid token without the required role; a
     401 means the token failed verification (expired/wrong issuer/aud). Check the
     token's claims and that `ZITADEL_ISSUER_URL` matches.

### "Content is stale after update"

1. The content editor saves to GCS. Cloudflare caches it at edge.
2. Options:
   - Wait for cache TTL (default: 4 hours for Pages assets)
   - Purge: `curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" -H "Authorization: Bearer {token}" -d '{"purge_everything":true}'`
   - Or: change the `content.json` URL in `app.js` to include a version query param.

### "Deploy failed on Cloudflare Pages"

```bash
# Check deployment status
wrangler pages deployment list --project-name=kyrka-portal

# Rollback to previous deployment
wrangler pages deployment rollback --project-name=kyrka-portal

# Redeploy (build with Eleventy first)
npx @11ty/eleventy
wrangler pages deploy frontend/member-portal/dist --project-name=kyrka-portal
```

## Cloudflare setup checklist (one-time)

1. **Create Cloudflare account** (free tier) at cloudflare.com
2. **Add domain** `kyrka.se` (or your domain) → Cloudflare gives you nameservers
3. **Update registrar** (Loopia, Binero, etc.) to use Cloudflare nameservers
4. **Create Pages project:**
   ```bash
   wrangler pages project create kyrka-portal
   ```
5. **Deploy static sites:**
   ```bash
   make deploy-sites
   ```
6. **Configure DNS records:**
   - `kyrka.se` → Pages project `kyrka-portal`
   - `api.kyrka.se` → CNAME to Cloud Run URL (proxied, orange cloud ON)
   - `admin.kyrka.se` → CNAME to Cloud Run URL (proxied, orange cloud ON)
7. **SSL mode:** Full (strict) — Cloudflare verifies the origin cert from GCP
8. **WAF:** Managed rules ON (free tier includes OWASP core rules)
9. **Bot detection:** ON (free tier)
10. **Cache rules:** default is fine for static sites

Total time: ~15 minutes. No Terraform needed — Cloudflare is
configured via dashboard or wrangler CLI.
