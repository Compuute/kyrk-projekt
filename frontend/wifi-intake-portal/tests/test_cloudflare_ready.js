// Tests that wifi-intake-portal is Cloudflare Pages-ready.
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
const js = fs.readFileSync(path.join(ROOT, 'content.js'), 'utf-8');

test('no external scripts', function () {
  assert.strictEqual((html.match(/<script[^>]+src=["']https?:\/\//gi) || []).length, 0);
});

test('no external stylesheets', function () {
  assert.strictEqual((html.match(/<link[^>]+href=["']https?:\/\//gi) || []).length, 0);
});

test('no document.cookie', function () {
  assert.ok(!html.includes('document.cookie'));
  assert.ok(!js.includes('document.cookie'));
});

test('no analytics', function () {
  for (const a of ['google-analytics', 'gtag', 'fbq', 'hotjar']) {
    assert.ok(!html.toLowerCase().includes(a));
  }
});

test('wrangler.toml exists', function () {
  assert.ok(fs.existsSync(path.join(ROOT, 'wrangler.toml')));
});

console.log('wifi-intake-portal Cloudflare-ready tests done');
