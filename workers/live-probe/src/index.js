// kyrka-live-probe — scheduled Worker that detects when each church's YouTube
// channel is broadcasting and records it in KV, so the public live page can
// show the player automatically ANY DAY a stream is on (not only inside a
// fixed weekly schedule window).
//
// Strategy (hybrid — see workers/live-probe/README.md):
//   1. Every ~2 min, cheaply scrape the channel's /live page (free, fast).
//   2. When the scrape sees a live stream, confirm it via the official
//      YouTube Data API (authoritative state + canonical video id). The API
//      only fires while a stream is live, so we stay well inside the
//      10,000-units/day free quota (search.list = 100 units/call).
//   3. Write church.live_now / live_video_id to KV ONLY on a state change.
//
// The middleware (functions/_middleware.ts) already injects the whole church
// KV doc as window.__KYRK_CONFIG__, so no extra plumbing is needed on read.

import { parseLiveFromHtml, parseLiveFromApi, liveStateChanged } from './detect.js';

const UA = 'Mozilla/5.0 (compatible; KyrkaLiveProbe/1.0; +https://github.com/Compuute/kyrk-projekt)';

async function scrapeLive(channelId) {
  // gl/hl + CONSENT cookie keep YouTube from serving the EU consent wall,
  // which would otherwise hide the live markers from an edge PoP.
  const url = 'https://www.youtube.com/channel/' + channelId + '/live?hl=en&gl=US';
  const res = await fetch(url, {
    headers: { 'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9', Cookie: 'CONSENT=YES+1' },
    redirect: 'follow',
  });
  if (!res.ok) return { isLive: false, videoId: '' };
  return parseLiveFromHtml(await res.text());
}

async function confirmViaApi(channelId, key) {
  const url = 'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&eventType=live&channelId='
    + encodeURIComponent(channelId) + '&key=' + encodeURIComponent(key);
  const res = await fetch(url);
  if (!res.ok) throw new Error('YouTube API ' + res.status);
  return parseLiveFromApi(await res.json());
}

async function probeChurch(key, env) {
  const raw = await env.kyrka_content.get(key);
  if (!raw) return;
  let doc;
  try { doc = JSON.parse(raw); } catch { return; }
  const church = doc && doc.church;
  const channelId = church && church.youtube_channel_id;
  if (!channelId) return; // not a church doc, or no channel configured

  // 1) cheap scrape
  let result = await scrapeLive(channelId);

  // 2) confirm via API whenever the scrape thinks it's live (authoritative
  //    state + canonical video id; corrects scrape false positives too).
  if (env.YT_API_KEY && result.isLive) {
    try { result = await confirmViaApi(channelId, env.YT_API_KEY); } catch (e) { /* keep scrape result */ }
  }

  // 3) write only on change
  if (!liveStateChanged(church, result)) return;
  church.live_now = result.isLive;
  church.live_video_id = result.isLive ? (result.videoId || '') : '';
  church.live_changed_at = new Date().toISOString();
  await env.kyrka_content.put(key, JSON.stringify(doc));
  console.log('live state changed: ' + key + ' -> ' + (result.isLive ? 'LIVE ' + church.live_video_id : 'offline'));
}

export default {
  async scheduled(_event, env, ctx) {
    const list = await env.kyrka_content.list();
    for (const k of list.keys) {
      ctx.waitUntil(
        probeChurch(k.name, env).catch((e) => console.log('probe ' + k.name + ' failed: ' + (e && e.message)))
      );
    }
  },
};
