// PWA readiness tests. Verifies manifest, service worker, and icons.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf-8');

// --- manifest.json

test('manifest.json exists and is valid JSON', function () {
  const raw = fs.readFileSync(path.join(ROOT, 'manifest.json'), 'utf-8');
  const m = JSON.parse(raw);
  assert.ok(m.name, 'manifest must have name');
  assert.ok(m.short_name, 'manifest must have short_name');
  assert.strictEqual(m.display, 'standalone', 'display must be standalone');
  assert.ok(m.start_url, 'must have start_url');
});

test('manifest has correct theme color', function () {
  const m = JSON.parse(fs.readFileSync(path.join(ROOT, 'manifest.json'), 'utf-8'));
  assert.strictEqual(m.theme_color, '#3b5bdb');
});

test('manifest has icons in required sizes', function () {
  const m = JSON.parse(fs.readFileSync(path.join(ROOT, 'manifest.json'), 'utf-8'));
  const sizes = m.icons.map(function (i) { return i.sizes; });
  assert.ok(sizes.includes('192x192'), 'needs 192x192 icon');
  assert.ok(sizes.includes('512x512'), 'needs 512x512 icon');
});

test('icon files exist', function () {
  assert.ok(fs.existsSync(path.join(ROOT, 'icons', 'icon-192.png')), 'icon-192.png missing');
  assert.ok(fs.existsSync(path.join(ROOT, 'icons', 'icon-512.png')), 'icon-512.png missing');
});

// --- HTML meta tags

test('HTML links to manifest.json', function () {
  assert.ok(html.includes('rel="manifest"'), 'missing <link rel="manifest">');
  assert.ok(html.includes('manifest.json'), 'manifest.json not referenced');
});

test('HTML has theme-color meta', function () {
  assert.ok(html.includes('name="theme-color"'), 'missing theme-color meta');
});

test('HTML has apple-mobile-web-app-capable', function () {
  assert.ok(html.includes('apple-mobile-web-app-capable'), 'missing apple PWA meta');
});

test('HTML has apple-touch-icon', function () {
  assert.ok(html.includes('apple-touch-icon'), 'missing apple-touch-icon link');
});

// --- Service worker

test('sw.js exists', function () {
  assert.ok(fs.existsSync(path.join(ROOT, 'sw.js')), 'sw.js missing');
});

test('HTML registers service worker', function () {
  var appJs = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf-8');
  var registeredInHtml = html.includes('serviceWorker.register') || html.includes('registerServiceWorker');
  var registeredInApp = appJs.includes('serviceWorker.register');
  assert.ok(registeredInHtml && registeredInApp, 'SW must be registered via HTML or app.js');
});

test('sw.js caches essential files', function () {
  const sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf-8');
  assert.ok(sw.includes('index.html'), 'sw must cache index.html');
  assert.ok(sw.includes('styles.css'), 'sw must cache styles.css');
  assert.ok(sw.includes('app.js'), 'sw must cache app.js');
  assert.ok(sw.includes('content.json'), 'sw must cache content.json');
});

test('sw.js uses network-first for content.json', function () {
  const sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf-8');
  assert.ok(sw.includes('content.json') && sw.includes('fetch(event.request)'),
    'content.json should be network-first for fresh data');
});

test('sw.js handles push notifications', function () {
  const sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf-8');
  assert.ok(sw.includes("addEventListener('push'"), 'sw must handle push events');
  assert.ok(sw.includes('showNotification'), 'sw must show notifications');
});

// --- No tracking (PWA must not violate privacy pledge)

test('sw.js does not track or phone home', function () {
  const sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf-8');
  assert.ok(!sw.includes('analytics'), 'sw must not include analytics');
  assert.ok(!sw.includes('google-analytics'), 'sw must not phone Google');
});

console.log('member-portal PWA tests done');
