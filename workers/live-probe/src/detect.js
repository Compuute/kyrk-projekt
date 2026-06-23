// Pure live-detection helpers — no I/O, so they are unit-testable with bare
// node (see ../test/detect.test.mjs). The Worker (index.js) wires these to
// fetch() + KV.

// Parse a channel's /live page HTML. A live broadcast exposes isLive /
// isLiveBroadcast = true in the embedded player response; the canonical
// <link> (or the first videoId) gives the current stream's video id.
export function parseLiveFromHtml(html) {
  if (!html) return { isLive: false, videoId: '' };
  const live = /"isLive"\s*:\s*true/.test(html) || /"isLiveBroadcast"\s*:\s*true/.test(html);
  if (!live) return { isLive: false, videoId: '' };
  let m = html.match(/<link[^>]+rel="canonical"[^>]+href="https:\/\/www\.youtube\.com\/watch\?v=([\w-]{11})"/);
  if (!m) m = html.match(/"videoId"\s*:\s*"([\w-]{11})"/);
  return { isLive: true, videoId: m ? m[1] : '' };
}

// Parse a YouTube Data API search.list response (eventType=live). The API is
// authoritative — it both confirms the live state and returns the canonical
// video id, which we prefer over the scraped one.
export function parseLiveFromApi(json) {
  const items = (json && json.items) || [];
  for (const it of items) {
    const id = it && it.id && it.id.videoId;
    const isLive = it && it.snippet && it.snippet.liveBroadcastContent === 'live';
    if (id && isLive) return { isLive: true, videoId: id };
  }
  return { isLive: false, videoId: '' };
}

// Decide whether the church doc needs a KV write. We only write on a real
// change — KV's free tier allows ~1000 writes/day, and the cron runs every
// 2 min (720 ticks/day per church), so writing every tick would blow it.
export function liveStateChanged(church, result) {
  const prevLive = (church && church.live_now) === true;
  const prevId = (church && church.live_video_id) || '';
  const nextId = result.isLive ? (result.videoId || '') : '';
  return result.isLive !== prevLive || nextId !== prevId;
}
