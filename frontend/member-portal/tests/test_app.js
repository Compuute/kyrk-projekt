// Zero-dependency tests. Run: `node tests/test_app.js`
var assert = require('assert');
var app = require('../app.js');

var pickLanguage = app.pickLanguage;
var _t = app._t;

var fixture = {
  church: {
    name: {"sv": "Sankt Johannes", "am": "ቅዱስ ዮሐንስ"},
    tagline: {"sv": "Välkommen hem", "am": "እንኳን ወደ ቤትዎ ደህና መጡ"}
  },
  upcoming: [
    {
      title: {"sv": "Söndagsgudstjänst", "am": "የእሁድ ቅዳሴ"},
      date: "2025-06-08",
      time: "11:00",
      description: {"sv": "Gudstjänst med nattvard.", "am": "ቅዳሴ ከቁርባን ገር።"}
    },
    {
      title: {"sv": "Workshop"},
      date: "2025-06-12",
      time: "16:00",
      description: {"sv": "Kodning."}
    }
  ],
  announcements: [
    {
      title: {"sv": "Nytt bidrag!", "am": "አዲስ ድጋፍ!"},
      body: {"sv": "200 000 SEK beviljat.", "am": "የተፈቀደ ድጋፍ።"},
      date: "2025-06-01"
    }
  ],
  links: {
    member: {"sv": "Bli medlem", "am": "አባል ይሁኑ", url: "/intake"},
    donate: {"sv": "Ge en gåva", "am": "ስጦታ ይስጡ", url: "/donate"},
    telegram: {"sv": "Telegram", "am": "በቴሌግራም", url: "https://t.me/kyrka_kanal"},
    youth: {"sv": "Ungdom", "am": "የወጣቶች", url: "/youth"}
  },
  footer: {
    privacy: {
      "sv": "Inga kakor.",
      "am": "ኩኪዎችን አይጠቀምም።"
    }
  }
};

var passed = 0;
var failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log('  ok   ' + name);
    passed++;
  } catch (e) {
    console.error('  FAIL ' + name);
    console.error('       ' + e.message);
    failed++;
    process.exitCode = 1;
  }
}

// ---- pickLanguage tests ----

test('pickLanguage returns Swedish text for lang=sv', function () {
  var view = pickLanguage(fixture, 'sv');
  assert.strictEqual(view.churchName, 'Sankt Johannes');
  assert.strictEqual(view.churchTagline, 'Välkommen hem');
  assert.strictEqual(view.upcoming[0].title, 'Söndagsgudstjänst');
  assert.strictEqual(view.announcements[0].title, 'Nytt bidrag!');
  assert.strictEqual(view.links.member.text, 'Bli medlem');
  assert.strictEqual(view.links.member.url, '/intake');
  assert.strictEqual(view.footerPrivacy, 'Inga kakor.');
});

test('pickLanguage returns Amharic text for lang=am', function () {
  var view = pickLanguage(fixture, 'am');
  assert.strictEqual(view.churchName, 'ቅዱስ ዮሐንስ');
  assert.strictEqual(view.upcoming[0].title, 'የእሁድ ቅዳሴ');
  assert.strictEqual(view.links.member.text, 'አባል ይሁኑ');
  assert.strictEqual(view.footerPrivacy, 'ኩኪዎችን አይጠቀምም።');
});

test('pickLanguage falls back to sv for unknown language', function () {
  var view = pickLanguage(fixture, 'de');
  assert.strictEqual(view.churchName, 'Sankt Johannes');
  assert.strictEqual(view.upcoming[0].title, 'Söndagsgudstjänst');
  assert.strictEqual(view.footerPrivacy, 'Inga kakor.');
});

test('pickLanguage falls back to sv when am key is missing', function () {
  var view = pickLanguage(fixture, 'am');
  // Second upcoming item has no am text for title and description
  assert.strictEqual(view.upcoming[1].title, 'Workshop');
  assert.strictEqual(view.upcoming[1].description, 'Kodning.');
});

test('pickLanguage handles empty upcoming array', function () {
  var config = {
    church: { name: {"sv": "Test"} },
    upcoming: [],
    announcements: [],
    links: {},
    footer: { privacy: {"sv": "Ok"} }
  };
  var view = pickLanguage(config, 'sv');
  assert.deepStrictEqual(view.upcoming, []);
  assert.strictEqual(view.churchName, 'Test');
});

test('pickLanguage never crashes on empty config', function () {
  var view = pickLanguage({}, 'sv');
  assert.strictEqual(view.churchName, '');
  assert.deepStrictEqual(view.upcoming, []);
  assert.deepStrictEqual(view.announcements, []);
});

test('pickLanguage never crashes on null config', function () {
  var view = pickLanguage(null, 'sv');
  assert.strictEqual(view.churchName, '');
  assert.deepStrictEqual(view.upcoming, []);
});

test('pickLanguage defaults to sv when lang is undefined', function () {
  var view = pickLanguage(fixture);
  assert.strictEqual(view.churchName, 'Sankt Johannes');
});

// ---- _t helper tests ----

test('_t returns correct language', function () {
  assert.strictEqual(_t({"sv": "Hej", "am": "Selam"}, 'sv'), 'Hej');
  assert.strictEqual(_t({"sv": "Hej", "am": "Selam"}, 'am'), 'Selam');
});

test('_t falls back to sv for missing lang', function () {
  assert.strictEqual(_t({"sv": "Hej"}, 'am'), 'Hej');
});

test('_t returns empty string for null/undefined', function () {
  assert.strictEqual(_t(null, 'sv'), '');
  assert.strictEqual(_t(undefined, 'sv'), '');
});

// ---- renderPage / switchLanguage ----
// These require a DOM, so we test the pure-function path via pickLanguage.
// The switchLanguage function uses window._memberPortalContent which only
// exists in a browser context. We verify it doesn't crash in Node.

test('renderPage does not crash in Node (no document)', function () {
  // Should simply return without error
  app.renderPage(fixture, 'sv');
  assert.ok(true);
});

test('switchLanguage does not crash in Node (no window._memberPortalContent)', function () {
  app.switchLanguage('am');
  assert.ok(true);
});

// ---- Summary ----
console.log('\nmember-portal tests done: ' + passed + ' passed, ' + failed + ' failed');
