// Teaching library tests — data shape, bilingual rendering, privacy.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const SRC = path.join(__dirname, '..', 'churches');
const DIST = path.join(__dirname, '..', 'dist');

// --- Data shape (nacka)

const nacka = JSON.parse(fs.readFileSync(path.join(SRC, 'nacka', 'teachings.json'), 'utf-8'));

test('nacka teachings.json has categories and teachings', function () {
  assert.ok(nacka.categories && Object.keys(nacka.categories).length >= 3, 'needs categories');
  assert.ok(Array.isArray(nacka.teachings) && nacka.teachings.length > 0, 'needs teachings');
});

test('every teaching has id, date, category, bilingual title, amharic body', function () {
  nacka.teachings.forEach(function (t) {
    assert.ok(t.id && t.date && t.category, 'id/date/category required: ' + JSON.stringify(t.title));
    assert.ok(t.title && t.title.am && t.title.sv, 'bilingual title required for ' + t.id);
    assert.ok(t.body && t.body.am && t.body.am.length > 100, 'substantial Amharic body required for ' + t.id);
    assert.ok(nacka.categories[t.category], 'category must be defined: ' + t.category);
  });
});

test('no duplicate teaching ids', function () {
  var ids = nacka.teachings.map(function (t) { return t.id; });
  assert.strictEqual(new Set(ids).size, ids.length, 'duplicate ids found');
});

test('at least one fully translated (sv body) exemplar', function () {
  assert.ok(nacka.teachings.some(function (t) { return t.body.sv && t.body.sv.length > 100; }),
    'expected at least one Swedish-translated article');
});

test('stockholm teachings.json exists with array structure', function () {
  var s = JSON.parse(fs.readFileSync(path.join(SRC, 'stockholm', 'teachings.json'), 'utf-8'));
  assert.ok(Array.isArray(s.teachings), 'stockholm teachings must be an array');
});

// --- Rendered page (dist/library)

const html = fs.readFileSync(path.join(DIST, 'library', 'index.html'), 'utf-8');

test('library page renders teachings container + per-church fetch', function () {
  assert.ok(html.includes('id="teachings-root"'), 'missing teachings-root');
  assert.ok(html.includes('/churches/') && html.includes('teachings.json'), 'missing per-church teachings fetch');
});

test('library teaching section is bilingual', function () {
  assert.ok(html.includes('Undervisning'), 'missing Swedish heading');
  assert.ok(html.includes('ትምህርትና ጽሑፎች'), 'missing Amharic heading');
});

test('library page uses accessible native details (no external scripts)', function () {
  var externals = html.match(/<script[^>]+src=["']https?:\/\//gi) || [];
  assert.strictEqual(externals.length, 0, 'no external scripts');
  assert.ok(!html.includes('google-analytics') && !html.includes('document.cookie'), 'no tracking/cookies');
});

test('teachings.json is passthrough-served from churches/', function () {
  // Eleventy copies churches/ → dist/churches/, so the fetch path resolves.
  assert.ok(fs.existsSync(path.join(DIST, 'churches', 'nacka', 'teachings.json')),
    'dist/churches/nacka/teachings.json must exist after build');
});

console.log('member-portal teaching library tests done');
