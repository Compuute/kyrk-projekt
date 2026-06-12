// Unit tests for the feature-flag evaluation core (flags-eval.js).
// Run: node tests/test_flags.js
const assert = require('assert');
const { parseBucket, pickBucket, evaluateFlags } = require('../flags-eval.js');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); fail++; process.exitCode = 1; }
}

// --- parseBucket ---
test('parseBucket: reads ab cookie', () => assert.strictEqual(parseBucket('ab=42'), 42));
test('parseBucket: among other cookies', () =>
  assert.strictEqual(parseBucket('selected_language=sv; ab=7; selected_church=nacka'), 7));
test('parseBucket: missing -> null', () => assert.strictEqual(parseBucket('selected_language=sv'), null));
test('parseBucket: empty -> null', () => assert.strictEqual(parseBucket(''), null));
test('parseBucket: out of range -> null (no 3-digit match)', () => assert.strictEqual(parseBucket('ab=100'), null));
test('parseBucket: 0 is valid', () => assert.strictEqual(parseBucket('ab=0'), 0));
test('parseBucket: 99 is valid', () => assert.strictEqual(parseBucket('ab=99'), 99));

// --- pickBucket ---
test('pickBucket: deterministic with injected random', () =>
  assert.strictEqual(pickBucket(() => 0.5), 50));
test('pickBucket: floor (0.999 -> 99)', () => assert.strictEqual(pickBucket(() => 0.999), 99));
test('pickBucket: 0 -> 0', () => assert.strictEqual(pickBucket(() => 0), 0));
test('pickBucket: always 0-99 over many draws', () => {
  for (let i = 0; i < 1000; i++) { const b = pickBucket(); assert.ok(b >= 0 && b <= 99 && Number.isInteger(b)); }
});

// --- evaluateFlags ---
const cfg = { flags: {
  off:    { enabled: false, rollout: 100 },  // kill switch wins over rollout
  none:   { enabled: true,  rollout: 0 },    // enabled but 0% -> off for all
  all:    { enabled: true,  rollout: 100 },  // 100% -> on for all
  canary: { enabled: true,  rollout: 25 },   // on iff bucket < 25
} };
test('evaluateFlags: kill switch off for everyone', () => {
  assert.strictEqual(evaluateFlags(cfg, 0).off, false);
  assert.strictEqual(evaluateFlags(cfg, 99).off, false);
});
test('evaluateFlags: 0% rollout off for everyone', () => assert.strictEqual(evaluateFlags(cfg, 0).none, false));
test('evaluateFlags: 100% rollout on for everyone', () => {
  assert.strictEqual(evaluateFlags(cfg, 0).all, true);
  assert.strictEqual(evaluateFlags(cfg, 99).all, true);
});
test('evaluateFlags: canary boundary (bucket < rollout)', () => {
  assert.strictEqual(evaluateFlags(cfg, 24).canary, true);   // inside
  assert.strictEqual(evaluateFlags(cfg, 25).canary, false);  // edge is OUT
  assert.strictEqual(evaluateFlags(cfg, 80).canary, false);  // outside
});
test('evaluateFlags: empty/garbage config -> {}', () => {
  assert.deepStrictEqual(evaluateFlags(null, 10), {});
  assert.deepStrictEqual(evaluateFlags({}, 10), {});
});
test('evaluateFlags: missing rollout treated as 0', () =>
  assert.strictEqual(evaluateFlags({ flags: { x: { enabled: true } } }, 50).x, false));

console.log(`\nfeature-flag tests done: ${pass} passed, ${fail} failed`);
