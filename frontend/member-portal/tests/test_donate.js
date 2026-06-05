// Donation page tests — Swish integration, receipt info, bilingual, privacy.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'donate.html'), 'utf-8');

// --- Swish integration

test('donate page has Swish button', function () {
  assert.ok(html.includes('swish-btn'), 'missing Swish button');
  assert.ok(html.toLowerCase().includes('swish'), 'must mention Swish');
});

test('donate page has Swish deep link format', function () {
  assert.ok(html.includes('swish://payment'), 'must use swish:// deep link protocol');
});

test('donate page has preset amounts', function () {
  assert.ok(html.includes('data-amount="50"'), 'missing 50 kr');
  assert.ok(html.includes('data-amount="100"'), 'missing 100 kr');
  assert.ok(html.includes('data-amount="200"'), 'missing 200 kr');
  assert.ok(html.includes('data-amount="500"'), 'missing 500 kr');
  assert.ok(html.includes('data-amount="1000"'), 'missing 1000 kr');
});

test('donate page has custom amount input', function () {
  assert.ok(html.includes('custom-amount'), 'missing custom amount input');
  assert.ok(html.includes('type="number"'), 'custom amount should be number input');
});

// --- Receipt / tax info

test('donate page shows org number', function () {
  assert.ok(html.includes('802492-9237'), 'must show church org number for tax receipt');
});

test('donate page mentions gåvokvitto', function () {
  assert.ok(html.toLowerCase().includes('gåvokvitto') || html.toLowerCase().includes('kvitto'),
    'must mention receipt/gåvokvitto for tax deduction');
});

test('donate page mentions 200 kr threshold', function () {
  assert.ok(html.includes('200'), 'should mention the 200 kr tax deduction threshold');
});

// --- Alternative payment

test('donate page has bankgiro as alternative', function () {
  assert.ok(html.toLowerCase().includes('bankgiro'), 'must offer bankgiro as alternative');
});

// --- Bilingual

test('donate page has Amharic translations', function () {
  assert.ok(html.includes('ስጦታ ይስጡ'), 'missing Amharic donate title');
  assert.ok(html.includes('am'), 'must reference am language');
});

// --- Privacy

test('donate page has no cookies or tracking', function () {
  assert.ok(!html.includes('document.cookie'), 'no cookies');
  assert.ok(!html.includes('google-analytics'), 'no analytics');
  assert.ok(!html.includes('fbq'), 'no Facebook tracking');
});

test('donate page has no external scripts', function () {
  var externals = html.match(/<script[^>]+src=["']https?:\/\//gi) || [];
  assert.strictEqual(externals.length, 0, 'no external scripts');
});

// --- Navigation

test('donate page links back to main portal', function () {
  assert.ok(html.includes('href="/"') || html.includes("href='/'"),
    'must link back to main page');
});

// --- Church info

test('donate page shows church name', function () {
  assert.ok(html.includes('Abune Tekle Haymanot') || html.includes('Etiopiska'),
    'should show church name');
});

console.log('member-portal donation tests done');
