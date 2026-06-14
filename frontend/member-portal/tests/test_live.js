// Livestream page tests
const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..', 'dist');
const html = fs.readFileSync(path.join(ROOT, 'live', 'index.html'), 'utf-8');
const content = JSON.parse(fs.readFileSync(path.join(ROOT, 'content.json'), 'utf-8'));

test('live page has video area', function () {
  assert.ok(html.includes('video-area'), 'must have video embed area');
});

test('live page reads YouTube channel from content.json', function () {
  assert.ok(html.includes('youtube_channel_id'), 'must read channel ID from config');
  assert.ok(html.includes('/embed/live_stream?channel='), 'must embed the channel live stream');
});

test('live page embeds via privacy-friendly nocookie domain', function () {
  // No YouTube tracking cookies; matches the site's no-tracking promise.
  assert.ok(html.includes('youtube-nocookie.com'), 'must use youtube-nocookie.com');
});

test('live page time-gates the embed by schedule (no error box off-hours)', function () {
  assert.ok(html.includes('live_schedule'), 'must read live_schedule from config');
  assert.ok(html.includes('Europe/Stockholm'), 'must evaluate the window in church-local time');
  assert.ok(html.includes('isLiveNow'), 'must gate the embed behind a live-window check');
});

test('live page honours live_embed=false (button instead of unembeddable iframe)', function () {
  // Some channels disable embedding → an iframe shows "This video is
  // unavailable". Those churches set live_embed:false and get a watch button.
  assert.ok(html.includes('live_embed'), 'must read the live_embed flag');
  assert.ok(html.includes('canEmbed'), 'must branch on embeddability');
  assert.ok(html.includes('Se gudstjänsten live'), 'must offer a watch button');
});

test('content.json has youtube_channel_id field', function () {
  assert.ok('youtube_channel_id' in (content.church || {}), 'church must have youtube_channel_id');
});

test('content.json has youtube_handle field', function () {
  assert.ok('youtube_handle' in (content.church || {}), 'church must have youtube_handle');
});

test('live page falls back to handle-based live link when no channel id', function () {
  assert.ok(html.includes('youtube_handle'), 'must read handle from config');
  // Uses YouTube\'s always-current live URL for a handle (@name/live),
  // not a hardcoded video id that would go stale after the stream ends.
  assert.ok(html.includes('/live'), 'must link to the @handle/live URL');
});

test('live page does not hardcode a video id', function () {
  // A specific /live/<id> or watch?v=<id> would show last week\'s stream.
  assert.strictEqual(html.match(/youtube\.com\/live\/[A-Za-z0-9_-]{8,}/), null,
    'no hardcoded video id — must resolve current stream via channel or handle');
});

test('live page has weekly schedule', function () {
  assert.ok(html.includes('schedule'), 'must show service schedule');
  assert.ok(html.includes('11:00') || html.includes('Söndag'), 'must show Sunday service');
});

test('live page has bilingual text', function () {
  assert.ok(html.includes('ቅዳሴ'), 'must have Amharic for liturgy');
  assert.ok(html.includes('Gudstjänst'), 'must have Swedish');
});

test('live page has CTA buttons', function () {
  assert.ok(html.includes('./intake') || html.includes('intake.html'), 'must link to membership');
  assert.ok(html.includes('./donate') || html.includes('donate.html'), 'must link to donation');
});

test('live page has back link', function () {
  assert.ok(html.includes('href="./"') || html.includes('./index.html'), 'must link back to main');
});

test('live page has no cookies', function () {
  assert.ok(!html.includes('document.cookie'), 'no cookies');
});

test('live page has fallback for no stream', function () {
  assert.ok(html.includes('no-stream'), 'must show fallback when not live');
});

test('content.json has live link', function () {
  assert.ok(content.links && content.links.live, 'links must include live');
  assert.ok(content.links.live.url === './live', 'live link must point to ./live');
});

test('live page is modulärt (channel from config, not hardcoded)', function () {
  // The YouTube channel ID must come from content.json, not be hardcoded
  assert.ok(html.includes('config.church') && html.includes('youtube_channel_id'),
    'channel ID must be loaded from content.json, not hardcoded');
  // Verify no hardcoded channel ID in HTML
  var hardcoded = html.match(/channel\/UC[A-Za-z0-9_-]{20,}/);
  assert.strictEqual(hardcoded, null, 'no hardcoded YouTube channel ID');
});

console.log('member-portal live page tests done');
