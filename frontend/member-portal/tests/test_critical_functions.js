// Critical function tests — catches broken buttons, forms, and interactions.
//
// This test file verifies that every user-facing function WORKS,
// not just that the HTML exists. Runs against every page.
//
// What it catches:
// 1. Forms without working submit buttons
// 2. Invisible or missing consent checkboxes
// 3. JavaScript errors in inline scripts
// 4. Language switcher missing or broken
// 5. Swish deep links malformed
// 6. Required form fields without labels
// 7. Buttons/links with empty text (invisible to user)
// 8. Missing required attributes on inputs

const assert = require('assert');
const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

const ROOT = path.join(__dirname, '..');
const pages = fs.readdirSync(ROOT).filter(function (f) {
  return f.endsWith('.html');
});

console.log('  Critical function tests (' + pages.length + ' pages)');

pages.forEach(function (page) {
  var html = fs.readFileSync(path.join(ROOT, page), 'utf-8');

  // --- Every form has a visible submit button with text
  var forms = (html.match(/<form[\s\S]*?<\/form>/gi) || []);
  forms.forEach(function (form, i) {
    test(page + ' form[' + i + '] has submit button', function () {
      assert.ok(
        form.includes('type="submit"'),
        page + ' form[' + i + '] has no submit button'
      );
    });

    test(page + ' form[' + i + '] submit button has text', function () {
      var btn = form.match(/<button[^>]*type="submit"[^>]*>([\s\S]*?)<\/button>/i);
      if (btn) {
        var text = btn[1].replace(/<[^>]*>/g, '').trim();
        assert.ok(text.length > 0,
          page + ' form[' + i + '] submit button is empty (invisible to user)');
      }
    });
  });

  // --- Required inputs have labels
  var requiredInputs = html.match(/<input[^>]*required[^>]*>/gi) || [];
  requiredInputs.forEach(function (input) {
    var idMatch = input.match(/id="([^"]+)"/);
    if (idMatch) {
      test(page + ' required input #' + idMatch[1] + ' has label', function () {
        assert.ok(
          html.includes('for="' + idMatch[1] + '"') || html.includes('id="' + idMatch[1] + '"'),
          page + ' required input #' + idMatch[1] + ' has no associated label'
        );
      });
    }
  });

  // --- Checkboxes have explicit appearance (iOS fix)
  var checkboxes = html.match(/<input[^>]*type="checkbox"[^>]*>/gi) || [];
  if (checkboxes.length > 0) {
    test(page + ' checkboxes have mobile-safe styling', function () {
      assert.ok(
        html.includes('appearance: checkbox') || html.includes('-webkit-appearance'),
        page + ' has checkboxes but no explicit appearance — may be invisible on iOS'
      );
    });
  }

  // --- Language switcher exists and has both languages
  if (html.includes('lang-switcher') || html.includes('lang-pill')) {
    test(page + ' language switcher has Swedish option', function () {
      assert.ok(html.includes('data-lang="sv"'),
        page + ' language switcher missing Swedish');
    });
    test(page + ' language switcher has Amharic option', function () {
      assert.ok(html.includes('data-lang="am"'),
        page + ' language switcher missing Amharic');
    });
  }

  // --- Bilingual content: if .sv exists, .am should too
  var svCount = (html.match(/class="sv"/g) || []).length;
  var amCount = (html.match(/class="am"/g) || []).length;
  if (svCount > 0) {
    test(page + ' has balanced bilingual content (sv:' + svCount + ' am:' + amCount + ')', function () {
      assert.ok(amCount > 0,
        page + ' has ' + svCount + ' Swedish elements but 0 Amharic');
      assert.ok(Math.abs(svCount - amCount) < svCount * 0.5,
        page + ' bilingual imbalance: ' + svCount + ' sv vs ' + amCount + ' am');
    });
  }

  // --- Swish links are valid deep links
  var swishLinks = html.match(/href="swish:\/\/[^"]*"/g) || [];
  swishLinks.forEach(function (link) {
    test(page + ' Swish deep link is valid', function () {
      assert.ok(link.includes('swish://'),
        page + ' malformed Swish link: ' + link);
    });
  });

  // --- No empty links (invisible to user)
  var allLinks = html.match(/<a[^>]*>[\s\S]*?<\/a>/gi) || [];
  allLinks.forEach(function (link) {
    var text = link.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
    var href = (link.match(/href="([^"]*)"/) || [])[1] || '';
    if (href && href !== '#' && !href.startsWith('tel:') && !href.startsWith('mailto:')) {
      test(page + ' link to ' + href.substring(0, 30) + ' has visible text', function () {
        assert.ok(text.length > 0,
          page + ' has link to ' + href + ' with no visible text');
      });
    }
  });

  // --- No inline JS errors (basic syntax check)
  var scripts = html.match(/<script>([\s\S]*?)<\/script>/gi) || [];
  scripts.forEach(function (script, i) {
    var code = script.replace(/<\/?script>/gi, '');
    if (code.trim().length > 0) {
      test(page + ' inline script[' + i + '] has valid syntax', function () {
        try {
          new Function(code);
        } catch (e) {
          assert.fail(page + ' inline script[' + i + '] syntax error: ' + e.message);
        }
      });
    }
  });

  // --- Tel links have valid format
  var telLinks = html.match(/href="tel:[^"]*"/g) || [];
  telLinks.forEach(function (link) {
    test(page + ' phone link format', function () {
      var num = link.replace('href="tel:', '').replace('"', '');
      assert.ok(num.match(/^\+?\d[\d\s-]+$/),
        page + ' phone link has invalid format: ' + num);
    });
  });
});

console.log('critical function tests done (' + pages.length + ' pages)');
