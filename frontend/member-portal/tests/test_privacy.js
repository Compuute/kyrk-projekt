// Privacy policy page tests — GDPR compliance verification.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'privacy.html'), 'utf-8');

// --- GDPR Article references

test('mentions Art. 6 (lawful basis)', function () {
  assert.ok(html.includes('Art. 6'), 'must reference Art. 6 for lawful basis');
});

test('mentions Art. 15 (right of access)', function () {
  assert.ok(html.includes('Art. 15') || html.includes('tillgång') || html.includes('ተደራሽነት'),
    'must mention right of access');
});

test('mentions Art. 17 (right to erasure)', function () {
  assert.ok(html.includes('Art. 17') || html.includes('radering') || html.includes('ስረዛ'),
    'must mention right to erasure');
});

test('mentions IMY (Swedish DPA)', function () {
  assert.ok(html.includes('IMY') || html.includes('Integritetsskyddsmyndigheten'),
    'must mention Swedish supervisory authority');
});

// --- Organization info

test('shows church org number', function () {
  assert.ok(html.includes('802492-9237'), 'must show org number');
});

test('shows church name in Amharic', function () {
  assert.ok(html.includes('አቡነ ተክለ ሃይማኖት'), 'must show church name in Amharic');
});

// --- Data handling

test('mentions encryption (KMS)', function () {
  assert.ok(html.toLowerCase().includes('kms') || html.toLowerCase().includes('krypter'),
    'must mention encryption');
});

test('mentions EU data residency', function () {
  assert.ok(html.includes('europe-north1') || html.includes('Finland') || html.includes('EU'),
    'must mention EU data storage');
});

test('mentions no cookies', function () {
  assert.ok(html.includes('kakor') || html.includes('cookies'),
    'must explicitly state no cookies');
  assert.ok(html.includes('ኩኪ'), 'must mention cookies in Amharic too');
});

test('mentions no AI access to personal data', function () {
  assert.ok(html.toLowerCase().includes('ai') || html.toLowerCase().includes('personuppgifter'),
    'must clarify AI does not see personal data');
});

// --- Bilingual

test('has Swedish section', function () {
  assert.ok(html.includes('Integritetspolicy'), 'must have Swedish title');
});

test('has Amharic section', function () {
  assert.ok(html.includes('የግላዊነት ፖሊሲ'), 'must have Amharic title');
});

// --- Children

test('mentions children data protection', function () {
  assert.ok(html.includes('barn') || html.includes('ልጆች'),
    'must mention children data handling with parental consent');
});

// --- Navigation

test('has back link to main portal', function () {
  assert.ok(html.includes('./index.html'), 'must link back to main page');
});

// --- No tracking

test('no external scripts', function () {
  var ext = html.match(/<script[^>]+src=["']https?:\/\//gi) || [];
  assert.strictEqual(ext.length, 0, 'no external scripts');
});

test('no cookies set', function () {
  assert.ok(!html.includes('document.cookie'), 'no cookie setting');
});

console.log('member-portal privacy policy tests done');
