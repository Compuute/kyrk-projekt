// Enforces feature-flag governance. Runs by make test.
// Two layers: (1) unit tests of the rules, (2) the REAL registry must pass
// today — so a stale/expired/malformed flag fails CI and forces cleanup.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { validateFlag, validateRegistry } = require('../flags-hygiene.js');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); fail++; process.exitCode = 1; }
}

const TODAY = '2026-06-12';
const ok = { enabled: false, rollout: 0, type: 'ops', owner: 'd', description: 'x' };

test('valid ops flag (no expires needed)', () => assert.deepStrictEqual(validateFlag('f', ok, TODAY), []));
test('missing type', () => assert.ok(validateFlag('f', { ...ok, type: undefined }, TODAY).some(e => /type must be/.test(e))));
test('bad type', () => assert.ok(validateFlag('f', { ...ok, type: 'foo' }, TODAY).some(e => /type must be/.test(e))));
test('missing owner', () => assert.ok(validateFlag('f', { ...ok, owner: '' }, TODAY).some(e => /owner/.test(e))));
test('missing description', () => assert.ok(validateFlag('f', { ...ok, description: '' }, TODAY).some(e => /description/.test(e))));
test('enabled must be boolean', () => assert.ok(validateFlag('f', { ...ok, enabled: 'yes' }, TODAY).some(e => /boolean/.test(e))));
test('rollout out of range', () => assert.ok(validateFlag('f', { ...ok, rollout: 150 }, TODAY).some(e => /rollout/.test(e))));
test('release flag without expires fails', () =>
  assert.ok(validateFlag('f', { ...ok, type: 'release' }, TODAY).some(e => /must set 'expires'/.test(e))));
test('release flag with future expires is valid', () =>
  assert.deepStrictEqual(validateFlag('f', { ...ok, type: 'release', expires: '2026-12-31' }, TODAY), []));
test('EXPIRED release flag fails (forces cleanup)', () =>
  assert.ok(validateFlag('f', { ...ok, type: 'release', expires: '2026-01-01' }, TODAY).some(e => /EXPIRED/.test(e))));
test('expires on boundary (== today) is not yet expired', () =>
  assert.deepStrictEqual(validateFlag('f', { ...ok, type: 'release', expires: TODAY }, TODAY), []));
test('malformed expires date', () =>
  assert.ok(validateFlag('f', { ...ok, type: 'release', expires: '2026/12/31' }, TODAY).some(e => /YYYY-MM-DD/.test(e))));

// --- (2) the real registry must be clean as of today ---
test('REAL flags.json passes hygiene today', () => {
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'flags.json'), 'utf-8'));
  const today = new Date().toISOString().slice(0, 10);
  const errors = validateRegistry(cfg, today);
  assert.deepStrictEqual(errors, [], 'flags.json hygiene errors:\n' + errors.join('\n'));
});

// --- orphan detection (advisory, non-failing): a flag in the registry that no
//     code references is probably dead. Warn so it gets noticed, do not block. ---
(() => {
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'flags.json'), 'utf-8'));
  const srcDirs = [path.join(__dirname, '..', 'src'), path.join(__dirname, '..', 'app.ts')];
  let haystack = '';
  for (const d of srcDirs) {
    try {
      const stat = fs.statSync(d);
      if (stat.isFile()) haystack += fs.readFileSync(d, 'utf-8');
      else for (const f of fs.readdirSync(d, { recursive: true })) {
        const fp = path.join(d, f);
        try { if (fs.statSync(fp).isFile()) haystack += fs.readFileSync(fp, 'utf-8'); } catch (_) {}
      }
    } catch (_) {}
  }
  for (const name of Object.keys((cfg.flags) || {})) {
    if (name.startsWith('example-')) continue; // template placeholder, exempt
    if (!haystack.includes(name)) console.warn(`  warn  flag "${name}" is not referenced in code — dead flag?`);
  }
})();

console.log(`\nfeature-flag hygiene tests done: ${pass} passed, ${fail} failed`);
