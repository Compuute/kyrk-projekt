// Unit tests for the pure live-detection helpers. Run with bare node:
//   node workers/live-probe/test/detect.test.mjs
import assert from 'node:assert';
import { parseLiveFromHtml, parseLiveFromApi, liveStateChanged } from '../src/detect.js';

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

// --- parseLiveFromHtml

test('detects a live broadcast and the canonical video id', () => {
  const html =
    '<link rel="canonical" href="https://www.youtube.com/watch?v=abc123DEF45">' +
    '...{"isLive":true,"videoId":"abc123DEF45"}...';
  const r = parseLiveFromHtml(html);
  assert.equal(r.isLive, true);
  assert.equal(r.videoId, 'abc123DEF45');
});

test('falls back to videoId field when no canonical link', () => {
  const r = parseLiveFromHtml('garbage "isLiveBroadcast":true more "videoId":"ZYXwvu98765" end');
  assert.equal(r.isLive, true);
  assert.equal(r.videoId, 'ZYXwvu98765');
});

test('reports offline when no live markers present', () => {
  const r = parseLiveFromHtml('<html>just a channel page, no stream</html>');
  assert.equal(r.isLive, false);
  assert.equal(r.videoId, '');
});

test('empty html is treated as offline', () => {
  assert.deepEqual(parseLiveFromHtml(''), { isLive: false, videoId: '' });
});

// --- parseLiveFromApi

test('reads live state + id from a search.list response', () => {
  const json = { items: [{ id: { videoId: 'LIVEvid1234' }, snippet: { liveBroadcastContent: 'live' } }] };
  assert.deepEqual(parseLiveFromApi(json), { isLive: true, videoId: 'LIVEvid1234' });
});

test('upcoming/none broadcasts are not treated as live', () => {
  const json = { items: [{ id: { videoId: 'soon0000000' }, snippet: { liveBroadcastContent: 'upcoming' } }] };
  assert.deepEqual(parseLiveFromApi(json), { isLive: false, videoId: '' });
});

test('empty api response is offline', () => {
  assert.deepEqual(parseLiveFromApi({ items: [] }), { isLive: false, videoId: '' });
});

// --- liveStateChanged (the KV-write gate)

test('no write when state is unchanged (offline -> offline)', () => {
  assert.equal(liveStateChanged({ live_now: false }, { isLive: false, videoId: '' }), false);
});

test('write when going live', () => {
  assert.equal(liveStateChanged({ live_now: false }, { isLive: true, videoId: 'newLive0001' }), true);
});

test('write when the live video id changes mid-broadcast', () => {
  assert.equal(
    liveStateChanged({ live_now: true, live_video_id: 'oldVid00001' }, { isLive: true, videoId: 'newVid00002' }),
    true
  );
});

test('no write while the same stream stays live', () => {
  assert.equal(
    liveStateChanged({ live_now: true, live_video_id: 'sameVid0001' }, { isLive: true, videoId: 'sameVid0001' }),
    false
  );
});

test('write when going offline', () => {
  assert.equal(liveStateChanged({ live_now: true, live_video_id: 'wasLive0001' }, { isLive: false, videoId: '' }), true);
});

console.log('live-probe detect tests done');
