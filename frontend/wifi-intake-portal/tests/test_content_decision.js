// Zero-dependency tests. Run: `node tests/test_content_decision.js`
const assert = require('assert');
const { decideContent, pickEventKey } = require('../content.js');

const fixture = {
  events: [
    { key: 'youth_tech_week', from: '2025-06-15', to: '2025-06-22' }
  ],
  languages: {
    sv: {
      base: {
        title: 'Välkommen',
        subtitle: 'Fri Wi-Fi',
        links: { member: '/intake', youth: '/unga', kids: '/barn', tech: '/tech', donate: '/ge' }
      },
      sections: {
        default: { title: 'Default SV', today: ['a', 'b'] },
        sunday: { title: 'Söndag', today: ['service'] },
        weekday: { title: 'Vardag', today: ['open'] },
        youth_tech_week: { title: 'Youth Tech', today: ['code'] }
      }
    },
    en: {
      base: { title: 'Welcome', subtitle: 'Free Wi-Fi', links: {} },
      sections: { default: { title: 'Default EN', today: [] } }
    }
  }
};

function test(name, fn) {
  try {
    fn();
    console.log('  ok   ' + name);
  } catch (e) {
    console.error('  FAIL ' + name);
    console.error('       ' + e.message);
    process.exitCode = 1;
  }
}

test('event window picks event key', function () {
  const d = new Date('2025-06-18T10:00:00Z');
  assert.strictEqual(pickEventKey(fixture, d), 'youth_tech_week');
});

test('sunday fallback', function () {
  const d = new Date('2025-06-08T10:00:00Z'); // 2025-06-08 is a Sunday
  assert.strictEqual(pickEventKey(fixture, d), 'sunday');
});

test('weekday fallback', function () {
  const d = new Date('2025-06-04T10:00:00Z'); // 2025-06-04 is a Wednesday
  assert.strictEqual(pickEventKey(fixture, d), 'weekday');
});

test('decideContent returns event content during event window', function () {
  const d = new Date('2025-06-18T10:00:00Z');
  const view = decideContent(fixture, { date: d, lang: 'sv' });
  assert.strictEqual(view.title, 'Youth Tech');
  assert.deepStrictEqual(view.today, ['code']);
  assert.strictEqual(view.links.member, '/intake');
});

test('decideContent falls back to english when requested', function () {
  const d = new Date('2025-06-04T10:00:00Z');
  const view = decideContent(fixture, { date: d, lang: 'en' });
  // English has no weekday section; falls back to `default` in sections.
  assert.strictEqual(view.title, 'Default EN');
});

test('decideContent never crashes on empty config', function () {
  const view = decideContent({}, { date: new Date(), lang: 'sv' });
  assert.strictEqual(typeof view.title, 'string');
  assert.ok(Array.isArray(view.today));
});

console.log('wifi-intake-portal content tests done');
