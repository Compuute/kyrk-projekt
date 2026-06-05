// Intake form tests — form fields, GDPR, bilingual, privacy.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'intake.html'), 'utf-8');

// --- Required form fields

test('intake has first_name field', function () {
  assert.ok(html.includes('name="first_name"'), 'missing first_name field');
});

test('intake has last_name field', function () {
  assert.ok(html.includes('name="last_name"'), 'missing last_name field');
});

test('intake has phone field', function () {
  assert.ok(html.includes('name="phone"'), 'missing phone field');
});

test('intake has email field', function () {
  assert.ok(html.includes('name="email"'), 'missing email field');
});

test('intake has personal_number field', function () {
  assert.ok(html.includes('name="personal_number"'), 'missing personal_number field');
});

// --- GDPR

test('intake has GDPR consent checkbox', function () {
  assert.ok(html.includes('name="gdpr_consent"'), 'missing gdpr_consent field');
  assert.ok(html.includes('type="checkbox"'), 'gdpr_consent should be checkbox');
});

test('intake has GDPR consent text in Swedish', function () {
  assert.ok(html.includes('GDPR'), 'must mention GDPR');
  assert.ok(html.includes('samtycker'), 'must have Swedish consent text');
});

test('intake has GDPR consent text in Amharic', function () {
  assert.ok(html.includes('ፈቃድ'), 'must have Amharic GDPR text');
});

// --- Bilingual

test('intake has bilingual text', function () {
  // Swedish
  assert.ok(html.includes('Bli medlem'), 'missing Swedish title');
  assert.ok(html.includes('Förnamn'), 'missing Swedish first name label');
  // Amharic
  assert.ok(html.includes('አባል ይሁኑ'), 'missing Amharic title');
  assert.ok(html.includes('ስም'), 'missing Amharic first name label');
});

test('intake has bilingual success message', function () {
  assert.ok(html.includes('Tack! Din ansökan behandlas.'), 'missing Swedish success message');
  assert.ok(html.includes('አመሰግናለሁ! ማመልከቻዎ በሂደት ላይ ነው።'), 'missing Amharic success message');
});

// --- Hidden fields

test('intake has source hidden field', function () {
  assert.ok(html.includes('name="source"'), 'missing source hidden field');
  assert.ok(html.includes('type="hidden"'), 'source should be hidden');
});

test('intake has church_id hidden field', function () {
  assert.ok(html.includes('name="church_id"'), 'missing church_id hidden field');
});

// --- Privacy

test('intake has no external scripts', function () {
  var externals = html.match(/<script[^>]+src=["']https?:\/\//gi) || [];
  assert.strictEqual(externals.length, 0, 'no external scripts');
});

test('intake has no cookies', function () {
  assert.ok(!html.includes('document.cookie'), 'no cookies');
  assert.ok(!html.includes('google-analytics'), 'no analytics');
  assert.ok(!html.includes('fbq'), 'no Facebook tracking');
});

// --- Navigation

test('intake links back to main portal', function () {
  assert.ok(html.includes('href="/"'), 'must link back to main page');
});

// --- Language switcher

test('intake has language switcher', function () {
  assert.ok(html.includes('lang-switcher'), 'missing language switcher');
  assert.ok(html.includes('data-lang="sv"'), 'missing Swedish pill');
  assert.ok(html.includes('data-lang="am"'), 'missing Amharic pill');
});

// --- sw.js caches intake.html

test('service worker caches intake.html', function () {
  var sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf-8');
  assert.ok(sw.includes('intake.html'), 'sw.js must cache intake.html');
});

// --- content.json links to intake.html

test('content.json member link points to intake.html', function () {
  var content = JSON.parse(fs.readFileSync(path.join(ROOT, 'content.json'), 'utf-8'));
  assert.strictEqual(content.links.member.url, '/intake.html', 'member link should point to /intake.html');
});

console.log('member-portal intake form tests done');
