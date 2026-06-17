// Utbildning-hubben: config-driven rendering + Stockholm Fredagsskola till
// separat org (inte kyrkan). Verifierar byggd HTML + Stockholm-config.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'dist', 'education', 'index.html'), 'utf-8');

// --- Sidan är config-driven, inte hårdkodad

test('education page renders from church config (edu-list container)', function () {
  assert.ok(html.includes('id="edu-list"'), 'missing edu-list container');
  assert.ok(html.includes('getContentUrl()'), 'must read per-church config');
});

test('education page has an empty state for churches without programs', function () {
  assert.ok(html.includes('id="edu-empty"'), 'missing empty state');
});

test('education page reuses the Swish deep-link pattern', function () {
  assert.ok(html.includes('buildSwishLink'), 'should reuse buildSwishLink');
  assert.ok(html.includes('qrcodegen'), 'should offer Swish QR on desktop');
});

test('education page is bilingual (sv + am spans)', function () {
  assert.ok(html.includes('ለልጆች') || html.includes('ትምህርት'), 'missing Amharic');
});

// --- Nav-länken visas bara för kyrkor med utbildning (multi-tenant)

test('nav link starts hidden and is config-gated', function () {
  const home = fs.readFileSync(path.join(ROOT, 'dist', 'index.html'), 'utf-8');
  assert.ok(home.includes('id="nav-utbildning"'), 'missing nav link');
  assert.ok(home.includes('display:none'), 'nav link must start hidden until config confirms');
});

// --- Stockholm-config: Fredagsskola till SEPARAT org, inte kyrkan

test('Stockholm config has Fredagsskola paying the separate org', function () {
  const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'churches', 'stockholm', 'content.json'), 'utf-8'));
  assert.ok(Array.isArray(cfg.education) && cfg.education.length, 'missing education array');
  const f = cfg.education[0];
  assert.equal(f.payment.org_number, '802407-2673', 'must pay the separate childrens-activity org');
  assert.equal(f.payment.swish, '1234140950');
  assert.equal(f.payment.plusgiro, '851832-6');
  const amounts = f.payment.tiers.map(function (t) { return t.amount; });
  assert.deepEqual(amounts, [100, 200, 300], 'tiers 1/2/3+ children = 100/200/300');
});

test('Nacka has no education (per-church; nav stays hidden there)', function () {
  const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'churches', 'nacka', 'content.json'), 'utf-8'));
  assert.ok(!cfg.education || cfg.education.length === 0, 'Nacka should not have Fredagsskola');
});

// --- Swish-meddelande: kort referens, inte den långa instruktionen

test('swish message is a short reference, not the long instruction', function () {
  assert.ok(html.includes('pay.swish_message || actTitle'),
    'must use short swish_message/title, not message_instruction, for the prefilled message');
  assert.ok(html.includes('.slice(0, 50)'), 'must cap the swish message length');
  const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'churches', 'stockholm', 'content.json'), 'utf-8'));
  assert.ok((cfg.education[0].payment.swish_message || '').length <= 50, 'config swish_message ≤ 50');
});

// --- Publik barnanmälan: gate:ad, minimal data (GDPR Art. 8)

test('registration form is gated on registration_enabled + group_id', function () {
  assert.ok(html.includes('a.registration_enabled === true && a.group_id'),
    'form must only render when explicitly enabled AND linked to a group');
});

test('registration is OFF by default in Stockholm config (go-live gate)', function () {
  const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'churches', 'stockholm', 'content.json'), 'utf-8'));
  assert.strictEqual(cfg.education[0].registration_enabled, false,
    'must stay disabled until go-live (#156/#118)');
});

test('registration collects minimal child data — NO personnummer/phone', function () {
  assert.ok(html.includes('reg-child-first') && html.includes('reg-child-last'), 'child name fields');
  assert.ok(html.includes('reg-birth-year'), 'birth year (for age band)');
  assert.ok(html.includes('reg-guardian'), 'guardian name');
  assert.ok(html.includes('reg-consent'), 'guardian consent checkbox');
  // GDPR data minimization for minors — no INPUT field for these (a code
  // comment documenting "INGET personnummer" is fine; an input is not).
  assert.ok(!/placeholder="[^"]*ersonnummer/i.test(html), 'no personnummer input');
  assert.ok(!html.includes('reg-pnr') && !html.includes('reg-personnummer'), 'no personnummer field');
  assert.ok(!/placeholder="[^"]*elefon/i.test(html) && !html.includes('reg-phone'), 'no phone input');
});

test('registration captures guardian consent + timestamp and is a pending (202) flow', function () {
  assert.ok(html.includes('guardian_consent') && html.includes('consent_timestamp'),
    'must send consent + timestamp (audit trail)');
  assert.ok(html.includes('r.status === 202'), 'pending → staff approves (mirrors intake)');
  assert.ok(html.includes('granskas av församlingen'), 'must tell parent it is reviewed before enrollment');
});

console.log('member-portal education tests done');
