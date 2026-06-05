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

## Sequence diagrams

### 1. Member visits the church website

```
Member          Cloudflare          Cloudflare       GCS
Browser         DNS                 Pages Edge       (content.json)
  │                │                   │                │
  │ GET kyrka.se   │                   │                │
  ├───────────────►│                   │                │
  │                │ resolve to CF     │                │
  │                │──────────────────►│                │
  │                │                   │ edge cache hit?│
  │                │                   │───────┐        │
  │                │                   │  yes  │        │
  │                │                   │◄──────┘        │
  │  HTML+CSS+JS   │                   │                │
  │◄───────────────┼───────────────────┤                │
  │                │                   │                │
  │ JS fetches content.json            │                │
  ├───────────────►│───────────────────┤                │
  │                │                   │ fetch from GCS │
  │                │                   ├───────────────►│
  │                │                   │◄───────────────┤
  │  content.json  │                   │                │
  │◄───────────────┼───────────────────┤                │
  │                │                   │                │
  │ User clicks    │                   │                │
  │ 🇪🇹 አማርኛ      │                   │                │
  │ (client-side   │                   │                │
  │  JS swap,      │                   │                │
  │  no request)   │                   │                │
  │                │                   │                │
```

**Latency:** ~20ms (edge-served). No cold start. No container boot.

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
  │                │                   │                │ notify n8n     │
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

### 4. Quarterly OpenClaw analysis (n8n automated)

```
n8n             Cloud Run          Sanitizer        Anthropic       Cloud Storage
(cron)          reporting-svc      (in n8n)         API             (pending review)
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
   - **No →** it's PropelAuth returning 403 (role check). Check the bearer token.

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

# Redeploy
wrangler pages deploy frontend/member-portal --project-name=kyrka-portal
```

## Cloudflare setup checklist (one-time)

1. **Create Cloudflare account** (free tier) at cloudflare.com
2. **Add domain** `kyrka.se` (or your domain) → Cloudflare gives you nameservers
3. **Update registrar** (Loopia, Binero, etc.) to use Cloudflare nameservers
4. **Create Pages projects:**
   ```bash
   wrangler pages project create kyrka-portal
   wrangler pages project create kyrka-wifi
   ```
5. **Deploy static sites:**
   ```bash
   make deploy-sites
   ```
6. **Configure DNS records:**
   - `kyrka.se` → Pages project `kyrka-portal`
   - `wifi.kyrka.se` → Pages project `kyrka-wifi`
   - `api.kyrka.se` → CNAME to Cloud Run URL (proxied, orange cloud ON)
   - `admin.kyrka.se` → CNAME to Cloud Run URL (proxied, orange cloud ON)
7. **SSL mode:** Full (strict) — Cloudflare verifies the origin cert from GCP
8. **WAF:** Managed rules ON (free tier includes OWASP core rules)
9. **Bot detection:** ON (free tier)
10. **Cache rules:** default is fine for static sites

Total time: ~15 minutes. No Terraform needed — Cloudflare is
configured via dashboard or wrangler CLI.
