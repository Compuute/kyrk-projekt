var assert = require('assert');
var fs = require('fs');
var path = require('path');

var ROOT = path.join(__dirname, '..');
var pages = fs.readdirSync(ROOT).filter(function (f) { return f.endsWith('.html'); });
var passed = 0;
var failed = 0;

function ok(condition, msg) {
  if (condition) { console.log('  ok   ' + msg); passed++; }
  else { console.log('  FAIL ' + msg); failed++; }
}

// --- Every page has consistent navigation ---
pages.forEach(function (page) {
  var html = fs.readFileSync(path.join(ROOT, page), 'utf8');

  ok(html.indexOf('church-bar') > 0, page + ' has church-bar');
  ok(html.indexOf('site-nav') > 0, page + ' has site-nav');
  ok(html.indexOf('initChurchSelector') > 0, page + ' calls initChurchSelector');
  ok(html.indexOf('app.js') > 0, page + ' loads app.js');
});

// --- Navigation links exist on all pages ---
var navLinks = ['./intake', './donate', './live', './calendar', './faq'];
var indexHtml = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
navLinks.forEach(function (link) {
  ok(indexHtml.indexOf('href="' + link + '"') > 0, 'index.html nav has link to ' + link);
});

// --- Dropdown "Fler tjänster" exists ---
ok(indexHtml.indexOf('nav-dropdown') > 0, 'index.html has dropdown menu');
ok(indexHtml.indexOf('Fler tjänster') > 0, 'index.html dropdown says "Fler tjänster"');

// --- Dropdown contains all service pages ---
var serviceLinks = ['./funeral', './baptism', './tezkar', './library', './support', './venue'];
serviceLinks.forEach(function (link) {
  ok(indexHtml.indexOf('href="' + link + '"') > 0, 'dropdown has link to ' + link);
});

// --- Service pages exist ---
serviceLinks.forEach(function (link) {
  var file = link.replace('./', '') + '.html';
  ok(fs.existsSync(path.join(ROOT, file)), file + ' exists');
});

// --- Each service page has bilingual content (sv + am) ---
var serviceFiles = ['baptism.html', 'tezkar.html', 'library.html', 'support.html', 'venue.html'];
serviceFiles.forEach(function (file) {
  var html = fs.readFileSync(path.join(ROOT, file), 'utf8');
  var hasAmharic = /[ሀ-፿]/.test(html);
  ok(hasAmharic, file + ' has Amharic content');
  ok(html.indexOf('lang-pill') > 0, file + ' has language switcher');
});

// --- FAQ page has accordion ---
var faqHtml = fs.readFileSync(path.join(ROOT, 'faq.html'), 'utf8');
ok(faqHtml.indexOf('faq-item') > 0, 'faq.html has accordion items');
ok(/class="am"/.test(faqHtml), 'faq.html has Amharic question spans');
ok(faqHtml.indexOf('faq-q') > 0, 'faq.html has clickable questions');
ok(faqHtml.indexOf('faq-a') > 0, 'faq.html has answer sections');
var faqCount = (faqHtml.match(/class="faq-item"/g) || []).length;
ok(faqCount >= 8, 'faq.html has at least 8 FAQ items (found ' + faqCount + ')');

// --- Calendar page loads events ---
var calHtml = fs.readFileSync(path.join(ROOT, 'calendar.html'), 'utf8');
ok(calHtml.indexOf('getContentUrl') > 0 || calHtml.indexOf('content.json') > 0, 'calendar.html loads church content');
ok(calHtml.indexOf('cal-list') > 0, 'calendar.html has event list container');
ok(calHtml.indexOf('schedule-title') > 0, 'calendar.html has weekly schedule');

// --- Church selector ---
var appJs = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf8');
ok(appJs.indexOf('initChurchSelector') > 0, 'app.js has initChurchSelector function');
ok(appJs.indexOf('applyLanguage') > 0, 'app.js has applyLanguage function');
ok(appJs.indexOf('.sv') > 0 && appJs.indexOf('.am') > 0, 'app.js toggles .sv and .am elements');
ok(appJs.indexOf('churches.json') > 0, 'app.js loads churches.json');
ok(appJs.indexOf('selectedChurch') > 0, 'app.js tracks selected church');
ok(appJs.indexOf('geolocation') > 0, 'app.js supports geolocation');

// --- Churches.json is valid ---
var churches = JSON.parse(fs.readFileSync(path.join(ROOT, 'churches.json'), 'utf8'));
ok(churches.churches.length >= 9, 'churches.json has at least 9 churches');
churches.churches.forEach(function (c) {
  ok(c.id && c.name && c.name.sv && c.name.am && c.city, 'church ' + c.id + ' has required fields');
});

// --- Swish desktop fallback ---
var donateHtml = fs.readFileSync(path.join(ROOT, 'donate.html'), 'utf8');
ok(donateHtml.indexOf('isMobile') > 0, 'donate.html has mobile detection');
ok(donateHtml.indexOf('alert(') > 0, 'donate.html shows alert on desktop');

// --- No deprecated meta tags ---
pages.forEach(function (page) {
  var html = fs.readFileSync(path.join(ROOT, page), 'utf8');
  ok(html.indexOf('apple-mobile-web-app-capable') === -1, page + ' has no deprecated apple-mobile-web-app-capable');
});

// --- CSS has nav styles ---
var css = fs.readFileSync(path.join(ROOT, 'styles.css'), 'utf8');
ok(css.indexOf('.site-nav') > 0, 'styles.css has .site-nav');
ok(css.indexOf('.church-bar') > 0, 'styles.css has .church-bar');
ok(css.indexOf('.nav-dropdown') > 0, 'styles.css has .nav-dropdown');
ok(css.indexOf('.nav-dropdown-menu') > 0, 'styles.css has .nav-dropdown-menu');

console.log('\nnavigation tests done: ' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) process.exit(1);
