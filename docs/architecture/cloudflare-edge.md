# Updated Architecture with Cloudflare Edge

```
                              INTERNET
                                 │
                     ┌───────────┴───────────┐
                     │     CLOUDFLARE         │
                     │  DNS + CDN + WAF +     │
                     │  DDoS (free tier)      │
                     └───────────┬───────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
    ┌─────────┴─────────┐ ┌─────┴──────┐  ┌────────┴────────┐
    │ Cloudflare Pages  │ │ Cloudflare │  │  Cloudflare     │
    │ (static, edge)    │ │ Pages      │  │  proxy → GCP    │
    │                   │ │ (static)   │  │  Cloud Run      │
    │ member-portal     │ │ wifi-      │  │                 │
    │ sv + am           │ │ intake-    │  │  membership-    │
    │ content.json      │ │ portal     │  │  intake (RED)   │
    │ from GCS          │ │            │  │  membership-    │
    └───────────────────┘ └────────────┘  │  service (RED)  │
                                          │  certificate-   │
                                          │  service (RED)  │
                                          │  reporting-     │
                                          │  service (YLW)  │
                                          │  admin-web      │
                                          └─────────────────┘
                                                   │
                                          ┌────────┴────────┐
                                          │   GCP (EU)      │
                                          │   Firestore     │
                                          │   Cloud KMS     │
                                          │   BigQuery      │
                                          │   Secret Mgr    │
                                          └─────────────────┘
```

## What lives where

| Layer | What | Why here |
|---|---|---|
| **Cloudflare Pages** | member-portal, wifi-intake-portal | Static HTML, global edge, instant load, free SSL, free CDN, free DDoS |
| **Cloudflare proxy** | Routes to Cloud Run services | WAF, DDoS mitigation, bot detection on dynamic endpoints |
| **GCP Cloud Run** | 4 backend services + admin-web | Python/FastAPI, Firestore access, KMS, PropelAuth — needs a real runtime |
| **GCP Firestore** | All persistent data | EU multi-region, CMEK, per-collection scoping |
| **GCP KMS** | personal_number encryption | Customer-managed key, CMEK for Firestore |
| **GCP BigQuery** | Analytics export | YELLOW-zone reporting |
| **GCP Secret Manager** | API keys, tokens | Per-secret IAM bindings |

## Why this split

**Static sites on Cloudflare Pages:**
- Zero cold start (edge-served, not a container)
- Global CDN without configuration
- Automatic SSL without Terraform
- Free DDoS protection
- Deploys in 5 seconds (`wrangler pages deploy`)
- No GCS bucket, no Cloud CDN, no load balancer, no managed cert to maintain

**Dynamic services stay on GCP:**
- They need Firestore, KMS, BigQuery — all GCP-native
- IAM per-service-account requires GCP
- CMEK requires GCP KMS
- Defense-in-depth model (per-SA isolation) is GCP IAM

**Cloudflare as proxy for Cloud Run:**
- Adds WAF + DDoS on the dynamic endpoints too
- No code change — just a DNS proxy setting
- If Cloudflare goes down, flip DNS back to direct Cloud Run URLs (5 min rollback)

## What ops does differently

Before (GCS hosting):
```bash
# Deploy static site (5 steps)
gsutil rsync -r ./frontend/member-portal gs://project-member-portal
gcloud compute backend-buckets create ...
gcloud compute url-maps create ...
gcloud compute ssl-certificates create ...
gcloud compute target-https-proxies create ...
```

After (Cloudflare Pages):
```bash
# Deploy static site (1 step)
wrangler pages deploy ./frontend/member-portal --project-name=kyrka-portal
```

## Failure modes

| Scenario | Impact | Rollback |
|---|---|---|
| Cloudflare outage (rare, ~99.99% SLA) | Static sites unreachable. Dynamic services unreachable via proxy. | Flip DNS to direct Cloud Run URLs (5 min). Static sites temporarily unavailable. |
| GCP Cloud Run outage | Dynamic services down. Static sites still served from Cloudflare edge. | Cloud Run revision rollback (1 min). |
| Bad static deploy | Wrong content on portal. | `wrangler pages rollback` (instant). |
| Bad dynamic deploy | Service errors. | Cloud Run traffic shift to previous revision (1 min). |

Note: static sites on Cloudflare Pages survive a GCP outage. The
member-portal stays up even if every Cloud Run service is down. That's
a resilience benefit GCS doesn't give you (GCS goes down with GCP).
