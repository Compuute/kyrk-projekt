# kyrka-live-probe

Scheduled Cloudflare Worker that detects when a church's YouTube channel is
**live right now** and records it in KV, so the public live page
(`/live`) can show the player automatically **any day** a stream is on —
not only inside a fixed weekly schedule window.

## How it works (hybrid detection)

Every 2 minutes the cron fires `scheduled()`, which for each church doc in the
`kyrka_content` KV namespace:

1. **Scrapes** `https://www.youtube.com/channel/<id>/live` (free, fast). This is
   the primary detector and is what makes "any day" cheap.
2. **Confirms via the YouTube Data API** *only when the scrape sees a live
   stream*. The API (`search.list`, `eventType=live`) is authoritative — it
   confirms the state and returns the canonical video id. Because it only fires
   while a stream is live, we stay far inside the **10,000 units/day** free quota
   (`search.list` costs 100 units/call).
3. **Writes** `church.live_now` + `church.live_video_id` back to KV **only on a
   state change** (KV free tier ≈ 1000 writes/day; the cron alone would be 720
   ticks/day/church).

The Pages middleware (`functions/_middleware.ts`) already injects the whole
church doc as `window.__KYRK_CONFIG__`, so the live page just reads
`config.church.live_now` / `live_video_id`. `scripts/sync-church-kv.mjs` never
touches these runtime fields, so content syncs don't clobber live state.

If `YT_API_KEY` is **not** set, the probe still works via scraping alone (less
robust against scrape false positives, and the EU consent wall could hide the
markers — mitigated with `gl=US&hl=en` + a `CONSENT` cookie).

## One-time setup (manual — needs your Cloudflare + Google accounts)

1. **Create a YouTube Data API v3 key**
   - Google Cloud Console → APIs & Services → Library → enable **YouTube Data
     API v3**.
   - Credentials → Create credentials → **API key**. Restrict it to the
     YouTube Data API.
2. **Store the key as a Worker secret** (never commit it):
   ```sh
   cd workers/live-probe
   wrangler secret put YT_API_KEY      # paste the key when prompted
   ```
3. **Deploy the Worker (with its cron trigger):**
   ```sh
   cd workers/live-probe
   wrangler deploy
   ```
   The `[triggers] crons` in `wrangler.toml` registers the every-2-min schedule.

## Verify

- `wrangler tail kyrka-live-probe` and watch for `live state changed: … -> LIVE …`
  while a stream is on.
- Open `/live` for that church — the player should appear within ~2 min of the
  stream starting, on any weekday, and disappear within ~2 min of it ending.

## Test

```sh
node test/detect.test.mjs    # pure detection-logic unit tests (no network)
```
