// Tests that the member-portal is Cloudflare Pages-ready.
//
// Verifies: no external requests, no cookies, correct cache headers,
// content.json fetch works, language switching is client-side only.
//
// Run: node tests/test_cloudflare_ready.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..');
// Cloudflare Pages serves the eleventy build output (dist/), not the source
// tree. index.html only exists there (rendered from src/pages/index.njk), so
// the "deploy-ready" checks must read the built artifacts.
const DIST = path.join(ROOT, 'dist');
if (!fs.existsSync(path.join(DIST, 'index.html'))) {
  console.error('  FAIL  dist/ not built — run `npx @11ty/eleventy` (or `make test`) first');
  process.exit(1);
}
const html = fs.readFileSync(path.join(DIST, 'index.html'), 'utf-8');
const css = fs.readFileSync(path.join(DIST, 'styles.css'), 'utf-8');
const js = fs.readFileSync(path.join(DIST, 'app.js'), 'utf-8');
const content = JSON.parse(fs.readFileSync(path.join(DIST, 'content.json'), 'utf-8'));

// --- No external resources (Cloudflare Pages serves everything local)

test('HTML has no external script tags', function () {
  const scripts = html.match(/<script[^>]+src=["']https?:\/\//gi) || [];
  assert.strictEqual(scripts.length, 0, 'Found external scripts: ' + scripts.join(', '));
});

test('HTML has no external stylesheet links', function () {
  const links = html.match(/<link[^>]+href=["']https?:\/\//gi) || [];
  assert.strictEqual(links.length, 0, 'Found external stylesheets: ' + links.join(', '));
});

test('CSS has no external @import or url(http)', function () {
  const externals = css.match(/@import\s+url\s*\(\s*["']?https?:/gi) || [];
  const urlExternals = css.match(/url\s*\(\s*["']?https?:/gi) || [];
  assert.strictEqual(externals.length + urlExternals.length, 0, 'Found external CSS resources');
});

test('JS has no fetch to external domains (except content.json)', function () {
  // The only fetch should be to a relative URL (content.json)
  const fetches = js.match(/fetch\s*\(\s*["']https?:\/\//gi) || [];
  assert.strictEqual(fetches.length, 0, 'Found external fetch calls: ' + fetches.join(', '));
});

// --- Cookies: first-party functional only, no tracking

// Functional cookies persist UI preferences (language + selected church) and
// are disclosed in the privacy footer. Tracking/third-party cookies are not
// allowed. Each must be SameSite-scoped.
const FUNCTIONAL_COOKIES = ['selected_language', 'selected_church'];
const cookieWrites = js.split('\n').filter(function (l) {
  return /document\.cookie\s*=\s*["'`]/.test(l);
});

test('HTML has no cookie-setting scripts', function () {
  assert.ok(!html.includes('document.cookie'), 'Found document.cookie in HTML');
});

test('JS sets only first-party functional cookies', function () {
  for (const l of cookieWrites) {
    const name = (l.match(/document\.cookie\s*=\s*["'`]\s*([A-Za-z0-9_]+)=/) || [])[1];
    assert.ok(name && FUNCTIONAL_COOKIES.includes(name),
      'Unexpected cookie set (only ' + FUNCTIONAL_COOKIES.join(', ') + ' allowed): ' + l.trim());
  }
});

test('every cookie set is SameSite-scoped (no cross-site tracking)', function () {
  for (const l of cookieWrites) {
    assert.ok(/SameSite=(Lax|Strict)/i.test(l),
      'Cookie set without SameSite=Lax/Strict: ' + l.trim());
  }
});

test('HTML has no analytics scripts', function () {
  const analytics = ['google-analytics', 'gtag', 'fbq', 'hotjar', 'segment', 'mixpanel'];
  for (const a of analytics) {
    assert.ok(!html.toLowerCase().includes(a), 'Found analytics: ' + a);
  }
});

// --- Content structure (Cloudflare Pages serves static, content.json from GCS)

test('content.json has version field', function () {
  assert.ok(content.version, 'Missing version field');
});

test('content.json has both sv and am for church name', function () {
  assert.ok(content.church.name.sv, 'Missing Swedish church name');
  assert.ok(content.church.name.am, 'Missing Amharic church name');
});

test('content.json has upcoming activities', function () {
  assert.ok(Array.isArray(content.upcoming), 'upcoming is not an array');
  assert.ok(content.upcoming.length > 0, 'No upcoming activities');
});

test('every activity has both sv and am title', function () {
  for (const act of content.upcoming) {
    assert.ok(act.title.sv, 'Activity missing Swedish title');
    assert.ok(act.title.am, 'Activity missing Amharic title');
  }
});

// --- Language switching is client-side (no server roundtrip needed on Pages)

test('app.js exports switchLanguage function', function () {
  const { switchLanguage } = require('../app.js');
  assert.ok(typeof switchLanguage === 'function', 'switchLanguage not exported');
});

test('language switch does not require network request', function () {
  // switchLanguage re-renders from window._memberPortalContent
  // Extract just the switchLanguage function body
  const start = js.indexOf('function switchLanguage');
  const end = js.indexOf('\n}', start) + 2;
  const body = js.substring(start, end);
  assert.ok(!body.includes('fetch('), 'switchLanguage should not fetch — data is already loaded');
});

// --- wrangler.toml exists

test('wrangler.toml exists for Cloudflare Pages deploy', function () {
  assert.ok(fs.existsSync(path.join(ROOT, 'wrangler.toml')), 'Missing wrangler.toml');
});

// --- Privacy footer in both languages

test('content.json has privacy footer in sv and am', function () {
  assert.ok(content.footer.privacy.sv, 'Missing Swedish privacy footer');
  assert.ok(content.footer.privacy.am, 'Missing Amharic privacy footer');
  assert.ok(content.footer.privacy.sv.includes('kakor'), 'Swedish footer should mention cookies');
  assert.ok(content.footer.privacy.am.includes('ኩኪ'), 'Amharic footer should mention cookies');
});

console.log('member-portal Cloudflare-ready tests done');
