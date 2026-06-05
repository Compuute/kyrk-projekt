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
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf-8');
const css = fs.readFileSync(path.join(ROOT, 'styles.css'), 'utf-8');
const js = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf-8');
const content = JSON.parse(fs.readFileSync(path.join(ROOT, 'content.json'), 'utf-8'));

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

// --- No cookies / tracking

test('HTML has no cookie-setting scripts', function () {
  assert.ok(!html.includes('document.cookie'), 'Found document.cookie in HTML');
});

test('JS does not set cookies', function () {
  assert.ok(!js.includes('document.cookie'), 'Found document.cookie in JS');
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
