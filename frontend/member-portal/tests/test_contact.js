// Contact page tests — church contact cards populated from churches.json.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..', 'dist');
const html = fs.readFileSync(path.join(ROOT, 'contact', 'index.html'), 'utf-8');

// --- Static structure

test('contact page has all contact card elements', function () {
  ['contact-address', 'contact-phone', 'contact-email', 'contact-org',
   'phone-card', 'email-card', 'org-card'].forEach(function (id) {
    assert.ok(html.includes('id="' + id + '"'), 'missing element #' + id);
  });
});

test('contact page has init script that loads churches.json', function () {
  assert.ok(html.includes('./churches.json'),
    'contact page must fetch ./churches.json');
  assert.ok(html.includes('getSelectedChurch'),
    'contact page must look up the selected church via getSelectedChurch()');
});

// --- Functional: run the inline init script against a stub DOM

function extractContactScript() {
  var blocks = html.match(/<script>([\s\S]*?)<\/script>/g) || [];
  var block = blocks.find(function (b) { return b.includes('renderContactInfo'); });
  assert.ok(block, 'contact page must have an inline script defining renderContactInfo');
  return block.replace(/<\/?script>/g, '');
}

function makeStubDocument() {
  var els = {};
  ['contact-address', 'contact-phone', 'contact-email', 'contact-org',
   'phone-card', 'email-card', 'org-card'].forEach(function (id) {
    els[id] = {
      id: id,
      textContent: '',
      style: { display: id.endsWith('-card') ? 'none' : '' },
      children: [],
      appendChild: function (child) { this.children.push(child); }
    };
  });
  return {
    _els: els,
    getElementById: function (id) { return els[id] || null; },
    createElement: function (tag) { return { tagName: tag, href: '', textContent: '' }; }
  };
}

function runContactScript(churches, selectedId) {
  var doc = makeStubDocument();
  var ctx = {
    document: doc,
    window: {},
    getSelectedChurch: function () { return selectedId; },
    fetch: function () {
      return Promise.resolve({
        ok: true,
        json: function () { return Promise.resolve({ churches: churches }); }
      });
    }
  };
  vm.createContext(ctx);
  vm.runInContext(extractContactScript(), ctx);
  // let the fetch/json promise chain settle
  return new Promise(function (resolve) { setImmediate(function () { setImmediate(function () { resolve(doc); }); }); });
}

(async function () {
  var full = {
    id: 'stockholm',
    name: { sv: 'Medhane Alem', am: 'መድኃኔ ዓለም' },
    city: 'Stockholm',
    address: 'Pålsbodagränd 3, Hägsätra, Stockholm',
    org_number: '802492-9237',
    phone: '+46 8 724 60 76',
    email: 'test@example.com'
  };
  var sparse = {
    id: 'goteborg',
    name: { sv: 'Kidist Selassie', am: 'ቅድስት ሥላሴ' },
    city: 'Göteborg',
    address: 'Göteborg',
    org_number: '',
    phone: '',
    email: ''
  };

  var doc = await runContactScript([full, sparse], 'stockholm');

  test('address is populated for selected church', function () {
    assert.strictEqual(doc._els['contact-address'].textContent, full.address);
  });

  test('phone card is shown with clickable tel: link (no spaces in href)', function () {
    assert.notStrictEqual(doc._els['phone-card'].style.display, 'none', 'phone-card must be shown');
    var link = doc._els['contact-phone'].children[0];
    assert.ok(link, 'contact-phone must contain a link element');
    assert.strictEqual(link.href, 'tel:+46872460 76'.replace(/\s/g, ''), 'tel: href must strip spaces');
    assert.strictEqual(link.textContent, full.phone, 'link text must show the formatted number');
  });

  test('email card is shown when email exists', function () {
    assert.notStrictEqual(doc._els['email-card'].style.display, 'none', 'email-card must be shown');
    var link = doc._els['contact-email'].children[0];
    assert.ok(link, 'contact-email must contain a link element');
    assert.strictEqual(link.href, 'mailto:' + full.email);
    assert.strictEqual(link.textContent, full.email);
  });

  test('org card is shown when org_number exists', function () {
    assert.notStrictEqual(doc._els['org-card'].style.display, 'none', 'org-card must be shown');
    assert.ok(doc._els['contact-org'].textContent.includes(full.org_number));
  });

  var docSparse = await runContactScript([full, sparse], 'goteborg');

  test('cards without data stay hidden', function () {
    assert.strictEqual(docSparse._els['phone-card'].style.display, 'none', 'phone-card must stay hidden');
    assert.strictEqual(docSparse._els['email-card'].style.display, 'none', 'email-card must stay hidden');
    assert.strictEqual(docSparse._els['org-card'].style.display, 'none', 'org-card must stay hidden');
  });

  test('address is still populated for church with sparse data', function () {
    assert.strictEqual(docSparse._els['contact-address'].textContent, sparse.address);
  });

  var docUnknown = await runContactScript([full, sparse], 'finns-inte');

  test('unknown church id replaces Laddar... with a fallback message', function () {
    var text = docUnknown._els['contact-address'].textContent;
    assert.ok(text && text !== 'Laddar...', 'must not be stuck on Laddar...');
  });

  console.log('contact page tests done');
})();
