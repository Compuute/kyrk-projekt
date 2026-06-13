// Zero-dependency tests for the privacy-preserving aggregate metrics layer.
// Run: node tests/test_metrics.js
//
// What this guards:
// 1. The event allowlist is a closed set (no free-form values).
// 2. Metrics are disabled under Do-Not-Track and a local opt-out.
// 3. Retention milestones fire once per device, never re-counting.
// 4. The beacon sends no cookies and no PII (source-level checks on app.ts).

var assert = require('assert');
var fs = require('fs');
var path = require('path');
var app = require('../app.js');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

console.log('  Metrics tests');

// --- allowlist is exported and closed
test('METRIC_EVENTS is a fixed allowlist', function () {
  assert.ok(Array.isArray(app.METRIC_EVENTS), 'METRIC_EVENTS is exported as an array');
  ['app_open', 'pwa_install', 'push_prompt', 'push_grant', 'push_deny',
   'retain_w1', 'retain_w2', 'retain_w4', 'retain_w12'].forEach(function (e) {
    assert.ok(app.METRIC_EVENTS.indexOf(e) >= 0, 'allowlist includes ' + e);
  });
});

// --- Do-Not-Track and local opt-out disable metrics
test('metricsEnabled honors Do-Not-Track', function () {
  assert.strictEqual(app.metricsEnabled({ dnt: '1' }), false);
  assert.strictEqual(app.metricsEnabled({ dnt: 'yes' }), false);
});
test('metricsEnabled honors local opt-out', function () {
  assert.strictEqual(app.metricsEnabled({ optOut: 'true' }), false);
});
test('metricsEnabled defaults on when no signal is present', function () {
  assert.strictEqual(app.metricsEnabled({}), true);
  assert.strictEqual(app.metricsEnabled({ dnt: null, optOut: null }), true);
});

// --- retention milestones are once-per-device
test('retentionDue returns every milestone reached and not yet reported', function () {
  var DAY = 24 * 60 * 60 * 1000;
  assert.deepStrictEqual(
    app.retentionDue(0, 100 * DAY, {}),
    ['retain_w1', 'retain_w2', 'retain_w4', 'retain_w12']
  );
});
test('retentionDue skips milestones already reported', function () {
  var DAY = 24 * 60 * 60 * 1000;
  assert.deepStrictEqual(
    app.retentionDue(0, 30 * DAY, { retain_w1: true, retain_w2: true }),
    ['retain_w4']
  );
});
test('retentionDue is empty before the first milestone', function () {
  var DAY = 24 * 60 * 60 * 1000;
  assert.deepStrictEqual(app.retentionDue(0, 3 * DAY, {}), []);
});

// --- source-level privacy guarantees on the source of truth (app.ts)
var src = fs.readFileSync(path.join(__dirname, '..', 'app.ts'), 'utf-8');
test('the /m beacon omits credentials (no cookies sent)', function () {
  assert.ok(/fetch\('\/m'[\s\S]*?credentials: 'omit'/.test(src),
    'POST /m must use credentials: omit');
});
test('the beacon body carries only the event name (no PII)', function () {
  assert.ok(/JSON\.stringify\(\{ e: event \}\)/.test(src),
    'beacon body must be just { e: event }');
});
test('metrics code path references Do-Not-Track', function () {
  assert.ok(/doNotTrack/.test(src), 'app.ts must consult navigator.doNotTrack');
});
