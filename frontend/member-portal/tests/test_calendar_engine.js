// Zero-dependency tests. Run: `node tests/test_calendar_engine.js`
//
// Correctness strategy: the conversion math is cross-validated against the
// platform's ICU implementation (Intl, u-ca-ethiopic) — the same engine
// Chrome/Android ship — over thousands of sampled days, plus hand-verified
// golden dates. The engine's own arithmetic exists so the page works even
// where Intl calendar support is missing, but it is never allowed to
// disagree with ICU.
var assert = require('assert');
var cal = require('../calendar-engine.js');

var failures = 0;
function check(name, fn) {
  try { fn(); console.log('  ok  ' + name); }
  catch (e) { failures++; console.error('FAIL  ' + name + ' — ' + e.message); }
}

// --- Golden conversions (hand-verified against ICU and EOTC calendar) ----
check('2026-06-12 → Sene 5, 2018', function () {
  assert.deepStrictEqual(cal.toEthiopian(new Date(Date.UTC(2026, 5, 12))), { year: 2018, month: 10, day: 5 });
});
check('2025-09-11 → Meskerem 1, 2018 (nyår)', function () {
  assert.deepStrictEqual(cal.toEthiopian(new Date(Date.UTC(2025, 8, 11))), { year: 2018, month: 1, day: 1 });
});
check('2023-09-11 → Pagumen 6, 2015 (skottdag)', function () {
  assert.deepStrictEqual(cal.toEthiopian(new Date(Date.UTC(2023, 8, 11))), { year: 2015, month: 13, day: 6 });
});
check('2026-01-19 → Tirr 11, 2018 (Timkat)', function () {
  assert.deepStrictEqual(cal.toEthiopian(new Date(Date.UTC(2026, 0, 19))), { year: 2018, month: 5, day: 11 });
});
check('ethToGregorian: Meskerem 1, 2018 → 2025-09-11', function () {
  var d = cal.ethToGregorian(2018, 1, 1);
  assert.strictEqual(d.toISOString().slice(0, 10), '2025-09-11');
});
check('ethToGregorian: Pagumen 6, 2015 → 2023-09-11', function () {
  var d = cal.ethToGregorian(2015, 13, 6);
  assert.strictEqual(d.toISOString().slice(0, 10), '2023-09-11');
});

// --- Leap year rule: Pagume has 6 days when (year % 4) === 3 -------------
check('skottårsregel för Pagume', function () {
  assert.strictEqual(cal.daysInEthMonth(2015, 13), 6);
  assert.strictEqual(cal.daysInEthMonth(2016, 13), 5);
  assert.strictEqual(cal.daysInEthMonth(2017, 13), 5);
  assert.strictEqual(cal.daysInEthMonth(2018, 13), 5);
  assert.strictEqual(cal.daysInEthMonth(2019, 13), 6);
  assert.strictEqual(cal.daysInEthMonth(2018, 1), 30);
});

// --- Roundtrip property over ~11 years -----------------------------------
check('roundtrip gregoriansk→etiopisk→gregoriansk, varje dag 2020–2030', function () {
  var d = new Date(Date.UTC(2020, 0, 1));
  var end = new Date(Date.UTC(2030, 11, 31));
  while (d <= end) {
    var e = cal.toEthiopian(d);
    var back = cal.ethToGregorian(e.year, e.month, e.day);
    assert.strictEqual(back.toISOString().slice(0, 10), d.toISOString().slice(0, 10),
      'roundtrip misslyckades för ' + d.toISOString().slice(0, 10));
    d = new Date(d.getTime() + 86400000);
  }
});

// --- Cross-validation against ICU (the data-driven correctness proof) ----
check('matchar ICU/Intl för var 7:e dag 1950–2100', function () {
  var probe = new Intl.DateTimeFormat('en-u-ca-ethiopic', { year: 'numeric', month: 'numeric', day: 'numeric' });
  var sample = probe.formatToParts(new Date(Date.UTC(2026, 5, 12)));
  var hasEthiopic = sample.some(function (p) { return p.type === 'year' && p.value === '2018'; });
  if (!hasEthiopic) { console.log('      (ICU saknar ethiopic här — hoppar över)'); return; }
  var d = new Date(Date.UTC(1950, 0, 1));
  var end = new Date(Date.UTC(2100, 11, 31));
  var n = 0;
  while (d <= end) {
    var parts = {};
    probe.formatToParts(d).forEach(function (p) { parts[p.type] = p.value; });
    var mine = cal.toEthiopian(d);
    assert.strictEqual(mine.year + '-' + mine.month + '-' + mine.day,
      parseInt(parts.year, 10) + '-' + parseInt(parts.month, 10) + '-' + parseInt(parts.day, 10),
      'avviker från ICU för ' + d.toISOString().slice(0, 10));
    n++;
    d = new Date(d.getTime() + 7 * 86400000);
  }
  assert.ok(n > 7000, 'för få jämförelsepunkter: ' + n);
});

// --- Formatting -----------------------------------------------------------
check('formatEthiopianDate am/sv', function () {
  var d = new Date(Date.UTC(2026, 5, 12));
  assert.strictEqual(cal.formatEthiopianDate(d, 'am'), 'ሰኔ 5, 2018 ዓ.ም.');
  assert.strictEqual(cal.formatEthiopianDate(d, 'sv'), 'Sene 5, 2018 E.C.');
});

// --- Svensk computus + röda dagar ----------------------------------------
check('påskdagen 2024–2030 (Lag 1989:253-underlag)', function () {
  var golden = { 2024: '03-31', 2025: '04-20', 2026: '04-05', 2027: '03-28', 2028: '04-16', 2029: '04-01', 2030: '04-21' };
  Object.keys(golden).forEach(function (y) {
    var e = cal.computeEaster(parseInt(y, 10));
    assert.strictEqual(e.toISOString().slice(5, 10), golden[y], 'påsk ' + y);
  });
});
check('svenska röda dagar 2026', function () {
  var red = cal.swedishRedDays(2026);
  function has(mmdd) { return red.some(function (h) { return h.date === '2026-' + mmdd; }); }
  assert.ok(has('01-01'), 'Nyårsdagen');
  assert.ok(has('01-06'), 'Trettondedag jul');
  assert.ok(has('04-03'), 'Långfredagen');
  assert.ok(has('04-06'), 'Annandag påsk');
  assert.ok(has('05-14'), 'Kristi himmelsfärdsdag');
  assert.ok(has('05-24'), 'Pingstdagen');
  assert.ok(has('06-06'), 'Nationaldagen');
  assert.ok(has('06-20'), 'Midsommardagen');
  assert.ok(has('10-31'), 'Alla helgons dag');
  assert.ok(has('12-25'), 'Juldagen');
  red.forEach(function (h) { assert.ok(h.name && h.name.sv && h.name.am, 'tvåspråkigt namn saknas: ' + h.date); });
});

// --- Högtidsdata ----------------------------------------------------------
check('etiopisk-ortodoxa högtider: struktur och nyckeldatum', function () {
  assert.ok(cal.HOLIDAYS.ethiopianFixed.length >= 24, 'minst 24 fasta högtider, fick ' + cal.HOLIDAYS.ethiopianFixed.length);
  assert.strictEqual(cal.HOLIDAYS.monthlySaints.length, 11, '11 månatliga helgondagar');
  cal.HOLIDAYS.ethiopianFixed.forEach(function (h) {
    assert.ok(h.month >= 1 && h.month <= 13 && h.day >= 1 && h.day <= 30, 'ogiltigt datum');
    assert.ok(h.name.sv && h.name.am, 'tvåspråkigt namn saknas: ' + h.name.sv);
  });
  function fixed(m, d) { return cal.HOLIDAYS.ethiopianFixed.some(function (h) { return h.month === m && h.day === d; }); }
  assert.ok(fixed(1, 1), 'Enkutatash Meskerem 1');
  assert.ok(fixed(1, 17), 'Meskel Meskerem 17');
  assert.ok(fixed(4, 29), 'Gena Tahsas 29');
  assert.ok(fixed(5, 11), 'Timkat Tirr 11');
  assert.ok(fixed(12, 16), 'Filseta Nehase 16');
  assert.ok(cal.HOLIDAYS.monthlySaints.some(function (s) { return s.day === 24; }), 'Tekle Haymanot dag 24');
});
check('holidaysForEthMonth slår ihop fasta + helgondagar', function () {
  var tirr = cal.holidaysForEthMonth(2018, 5);
  assert.ok(tirr.some(function (h) { return h.day === 11 && /timkat/i.test(h.name.sv); }), 'Timkat i Tirr');
  assert.ok(tirr.some(function (h) { return h.day === 24; }), 'helgondag 24 i varje månad');
});

// --- Månadsgrid ------------------------------------------------------------
check('buildMonthGrid: Sene 2018 har 30 celler + rätt idag-flagga', function () {
  var grid = cal.buildMonthGrid(2018, 10, new Date(Date.UTC(2026, 5, 12)));
  assert.strictEqual(grid.cells.length, 30);
  var today = grid.cells.filter(function (c) { return c.isToday; });
  assert.strictEqual(today.length, 1);
  assert.strictEqual(today[0].eth.day, 5);
  assert.ok(grid.headerGreg.indexOf('jun') !== -1 || grid.headerGreg.indexOf('Jun') !== -1, 'gregoriansk period i header');
});

// --- "Idag" följer besökarens lokala klocka, inte UTC --------------------
check('localCivilDate: lokala datumet vinner över UTC-datumet', function () {
  var cp = require('child_process');
  // 22:30 UTC den 12 juni = 13 juni lokalt i UTC+14, fortfarande 12 juni i UTC-10
  var script = "var c=require('./calendar-engine.js');" +
    "process.stdout.write(c.localCivilDate(new Date(Date.UTC(2026,5,12,22,30))).toISOString().slice(0,10));";
  var ahead = cp.execSync(process.execPath + " -e \"" + script + "\"",
    { cwd: __dirname + '/..', env: Object.assign({}, process.env, { TZ: 'Etc/GMT-14' }) }).toString();
  var behind = cp.execSync(process.execPath + " -e \"" + script + "\"",
    { cwd: __dirname + '/..', env: Object.assign({}, process.env, { TZ: 'Etc/GMT+10' }) }).toString();
  assert.strictEqual(ahead, '2026-06-13', 'UTC+14 ska se den 13:e');
  assert.strictEqual(behind, '2026-06-12', 'UTC-10 ska se den 12:e');
});
check('buildMonthGrid default markerar samma dag som localCivilDate', function () {
  var t = cal.toEthiopian(cal.localCivilDate());
  var g = cal.buildMonthGrid(t.year, t.month);
  var today = g.cells.filter(function (c2) { return c2.isToday; });
  assert.strictEqual(today.length, 1, 'exakt en idag-cell');
  assert.strictEqual(today[0].eth.day, t.day, 'idag-cellen ska vara besökarens lokala dag');
});

// --- Världskalender-tabellen (data via ICU) -------------------------------
check('worldCalendarsToday: minst 8 system, rätt år för fast datum', function () {
  var d = new Date(Date.UTC(2026, 5, 12));
  var rows = cal.worldCalendarsToday(d, 'sv');
  assert.ok(rows.length >= 8, 'minst 8 kalendrar, fick ' + rows.length);
  function row(ca) { return rows.filter(function (r) { return r.ca === ca; })[0]; }
  assert.ok(/2026/.test(row('gregory').formatted), 'gregorianska 2026');
  assert.ok(/2018/.test(row('ethiopic').formatted), 'etiopiska 2018');
  assert.ok(/7518/.test(row('ethioaa').formatted), 'Amete Alem 7518');
  var am = cal.worldCalendarsToday(d, 'am');
  assert.ok(/[\u1200-\u137F]/.test(am.filter(function (r) { return r.ca === 'ethiopic'; })[0].formatted),
    'amharisk variant formateras med etiopisk skrift');
});

// --- Fas 1: beskrivningar, fastenedräkning, kommande högtider --------------
check('alla högtider, helgon, röda dagar och fastor har sv+am-beskrivning', function () {
  cal.HOLIDAYS.ethiopianFixed.forEach(function (h) {
    assert.ok(h.desc && h.desc.sv && h.desc.am, 'desc saknas: ' + h.name.sv);
  });
  cal.HOLIDAYS.monthlySaints.forEach(function (h) {
    assert.ok(h.desc && h.desc.sv && h.desc.am, 'desc saknas: ' + h.name.sv);
  });
  cal.swedishRedDays(2026).forEach(function (h) {
    assert.ok(h.desc && h.desc.sv && h.desc.am, 'desc saknas: ' + h.name.sv);
  });
  cal.HOLIDAYS.fasting.forEach(function (f) {
    assert.ok(f.desc && f.desc.sv && f.desc.am, 'desc saknas: ' + f.name.sv);
  });
  assert.ok(cal.HOLIDAYS.weeklyFastNote.sv && cal.HOLIDAYS.weeklyFastNote.am, 'veckonot saknas');
});
check('detaljpanelens data: griden bär högtidens beskrivning till cellen', function () {
  // Sene (månad 10) dag 12 = Sene Mikael (fast högtid med desc)
  var hols = cal.holidaysForEthMonth(2018, 10);
  var mikael = hols.filter(function (h) { return h.day === 12; })[0];
  assert.ok(mikael, 'Sene Mikael ska finnas dag 12');
  assert.ok(mikael.desc && mikael.desc.sv, 'feast-desc ska bäras genom griden, inte tappas');
  // helgondag (dag 24, Tekle Haymanot) ska också bära desc
  var saint = hols.filter(function (h) { return h.day === 24; })[0];
  assert.ok(saint.desc && saint.desc.sv, 'saint-desc ska bäras genom griden');
  // svensk röd dag via buildMonthGrid — midsommar i Sene 2018
  var grid = cal.buildMonthGrid(2018, 10, new Date(Date.UTC(2026, 5, 12)));
  var redCells = [];
  grid.cells.forEach(function (c) { c.holidays.forEach(function (h) { if (h.type === 'swedish') redCells.push(h); }); });
  assert.ok(redCells.length > 0, 'minst en svensk röd dag i Sene');
  assert.ok(redCells[0].desc && redCells[0].desc.sv, 'swedish-desc ska bäras genom griden');
});
check('currentOrNextFast: 2026-06-12 → Filseta börjar om 56 dagar, 16 dagar lång', function () {
  var f = cal.currentOrNextFast(new Date(Date.UTC(2026, 5, 12)));
  assert.strictEqual(f.status, 'upcoming');
  assert.ok(/Filseta/.test(f.name.sv), 'nästa fasta ska vara Filseta, fick ' + f.name.sv);
  assert.strictEqual(f.startsInDays, 56, 'Nehase 1 2018 = 7 aug 2026');
  assert.strictEqual(f.lengthDays, 16);
});
check('currentOrNextFast: mitt i Filseta → pågår med rätt nedräkning', function () {
  var f = cal.currentOrNextFast(new Date(Date.UTC(2026, 7, 10)));
  assert.strictEqual(f.status, 'ongoing');
  assert.ok(/Filseta/.test(f.name.sv));
  assert.strictEqual(f.endsInDays, 12, 'slutar Nehase 16 = 22 aug 2026');
});
check('upcomingHolidays: 2026-06-12 → Sene Mikael om 7 dagar, midsommar med', function () {
  var u = cal.upcomingHolidays(new Date(Date.UTC(2026, 5, 12)), 5);
  assert.strictEqual(u.length, 5);
  assert.ok(/Mikael/.test(u[0].name.sv), 'först: Sene Mikael, fick ' + u[0].name.sv);
  assert.strictEqual(u[0].daysUntil, 7);
  assert.ok(u.some(function (h) { return /Midsommardagen/.test(h.name.sv); }), 'midsommar ska vara med');
  u.forEach(function (h) { assert.ok(h.desc && h.desc.sv, 'desc saknas i kommande: ' + h.name.sv); });
});

console.log(failures === 0 ? '\nAlla kalendertester gröna.' : '\n' + failures + ' test FAILADE.');
process.exit(failures === 0 ? 0 : 1);
