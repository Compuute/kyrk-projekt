// Universal page quality tests — runs against EVERY HTML page in member-portal.
//
// This test file enforces standards that ALL pages must meet:
// 1. Every page except index.html has a working back-link to ./index.html
// 2. No broken internal links
// 3. No external scripts (privacy)
// 4. No cookies (privacy)
// 5. No analytics (privacy)
// 6. Has viewport meta (mobile-first)
// 7. Has charset meta (Unicode/Amharic)
//
// When you add a NEW page, this test automatically covers it.
// If it fails, your page is missing something required.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..');
const pages = fs.readdirSync(ROOT).filter(function (f) {
  return f.endsWith('.html');
});

console.log('  Found ' + pages.length + ' HTML pages: ' + pages.join(', '));

// ================================================================
// Per-page tests (run for EVERY .html file)
// ================================================================

pages.forEach(function (page) {
  var html = fs.readFileSync(path.join(ROOT, page), 'utf-8');

  // --- Back link (all pages except index.html)
  if (page !== 'index.html') {
    test(page + ' has back-link to ./index.html', function () {
      assert.ok(
        html.includes('href="./index.html"'),
        page + ' must have href="./index.html" as back-link. Found none.'
      );
    });

    test(page + ' back-link target exists', function () {
      assert.ok(
        fs.existsSync(path.join(ROOT, 'index.html')),
        'index.html must exist for back-link to work'
      );
    });
  }

  // --- No broken internal links
  test(page + ' has no broken internal links', function () {
    var links = html.match(/href="\.\/([^"?#]+)"/g) || [];
    links.forEach(function (link) {
      var target = link.replace('href="./', '').replace('"', '');
      assert.ok(
        fs.existsSync(path.join(ROOT, target)),
        page + ' links to ./' + target + ' which does NOT exist'
      );
    });
  });

  // --- No external scripts
  test(page + ' has no external scripts', function () {
    var ext = (html.match(/<script[^>]+src=["']https?:\/\//gi) || []);
    assert.strictEqual(ext.length, 0,
      page + ' has external scripts: ' + ext.join(', '));
  });

  // --- No cookies
  test(page + ' sets no cookies', function () {
    assert.ok(!html.includes('document.cookie'),
      page + ' must not set cookies');
  });

  // --- No analytics
  test(page + ' has no analytics', function () {
    var trackers = ['google-analytics', 'gtag(', 'fbq(', 'hotjar', 'segment', 'mixpanel'];
    trackers.forEach(function (t) {
      assert.ok(!html.toLowerCase().includes(t),
        page + ' contains analytics tracker: ' + t);
    });
  });

  // --- Has viewport meta (mobile-first)
  test(page + ' has viewport meta', function () {
    assert.ok(html.includes('viewport'),
      page + ' must have <meta name="viewport"> for mobile-first');
  });

  // --- Has charset meta (Unicode for Amharic)
  test(page + ' has UTF-8 charset', function () {
    assert.ok(html.toLowerCase().includes('charset="utf-8"') || html.toLowerCase().includes("charset='utf-8'"),
      page + ' must declare UTF-8 charset for Amharic support');
  });
});

// ================================================================
// Cross-page consistency tests
// ================================================================

test('service worker caches all HTML pages', function () {
  var sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf-8');
  pages.forEach(function (page) {
    assert.ok(
      sw.includes('/' + page),
      'sw.js must cache /' + page + ' for offline support'
    );
  });
});

test('content.json exists and is valid JSON', function () {
  var raw = fs.readFileSync(path.join(ROOT, 'content.json'), 'utf-8');
  var config = JSON.parse(raw);
  assert.ok(config.version, 'content.json must have version');
  assert.ok(config.church, 'content.json must have church');
});

console.log('all-pages quality tests done (' + pages.length + ' pages checked)');
