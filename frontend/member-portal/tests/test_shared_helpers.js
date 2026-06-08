var assert = require('assert');
var fs = require('fs');
var path = require('path');
var app = require('../app.js');

var root = path.join(__dirname, '..');
var intakeHtml = fs.readFileSync(path.join(root, 'intake.html'), 'utf8');
var donateHtml = fs.readFileSync(path.join(root, 'donate.html'), 'utf8');
var stylesCSS = fs.readFileSync(path.join(root, 'styles.css'), 'utf8');

var passed = 0;
var failed = 0;

function ok(condition, msg) {
  if (condition) { console.log('  ok   ' + msg); passed++; }
  else { console.log('  FAIL ' + msg); failed++; }
}

// --- validateName ---
ok(app.validateName('Daniel') === true, 'validateName: valid name');
ok(app.validateName('Ab') === true, 'validateName: 2 chars ok');
ok(app.validateName('D') === false, 'validateName: 1 char too short');
ok(app.validateName('') === false, 'validateName: empty');
ok(app.validateName('Test123') === false, 'validateName: rejects digits');
ok(app.validateName('   ') === false, 'validateName: whitespace only');
ok(app.validateName('Abebe Kebede') === true, 'validateName: allows spaces');

// --- validatePhone ---
ok(app.validatePhone('0701234567') === true, 'validatePhone: Swedish mobile');
ok(app.validatePhone('+46701234567') === true, 'validatePhone: E.164 format');
ok(app.validatePhone('070-123 45 67') === true, 'validatePhone: with dashes/spaces');
ok(app.validatePhone('123') === false, 'validatePhone: too short');
ok(app.validatePhone('') === false, 'validatePhone: empty');
ok(app.validatePhone('abc') === false, 'validatePhone: letters');

// --- validatePersonnummer ---
ok(app.validatePersonnummer('') === true, 'validatePersonnummer: empty ok (optional)');
ok(app.validatePersonnummer('000') === false, 'validatePersonnummer: too short');
ok(app.validatePersonnummer('abcdefghij') === false, 'validatePersonnummer: letters rejected');

// --- buildSwishLink ---
var link1 = app.buildSwishLink('1234567890', 200, 'Medlemsavgift');
ok(link1.indexOf('swish://payment') === 0, 'buildSwishLink: starts with swish://payment');
ok(link1.indexOf('"1234567890"') > 0, 'buildSwishLink: contains payee number');
ok(link1.indexOf(':200') > 0 || link1.indexOf(':200,') > 0, 'buildSwishLink: contains amount 200');
ok(link1.indexOf('Medlemsavgift') > 0, 'buildSwishLink: contains message');

var link2 = app.buildSwishLink('9876543210', 500, 'Familj');
ok(link2.indexOf('9876543210') > 0, 'buildSwishLink: different number works');
ok(link2.indexOf(':500') > 0 || link2.indexOf(':500,') > 0, 'buildSwishLink: 500 kr works');

ok(app.buildSwishLink('', 200, 'test') === '#', 'buildSwishLink: no number returns #');
ok(app.buildSwishLink('123', 0, 'test') === '#', 'buildSwishLink: zero amount returns #');
ok(app.buildSwishLink(null, 200, 'test') === '#', 'buildSwishLink: null number returns #');

// --- intake.html uses app.js (not inline duplicates) ---
ok(intakeHtml.indexOf('<script src="app.js"></script>') > 0, 'intake.html loads app.js');
ok((intakeHtml.match(/function validateName/g) || []).length === 0, 'intake.html: no duplicate validateName');
ok((intakeHtml.match(/function validatePhone/g) || []).length === 0, 'intake.html: no duplicate validatePhone');
ok((intakeHtml.match(/function validatePersonnummer/g) || []).length === 0, 'intake.html: no duplicate validatePersonnummer');
ok(intakeHtml.indexOf('onclick="toggleConsent()"') > 0, 'intake.html: consent calls shared toggleConsent');
ok(intakeHtml.indexOf('buildSwishLink(') > 0, 'intake.html: uses shared buildSwishLink');

// --- donate.html uses app.js ---
ok(donateHtml.indexOf('<script src="app.js"></script>') > 0, 'donate.html loads app.js');
ok(donateHtml.indexOf('buildSwishLink(') > 0, 'donate.html: uses shared buildSwishLink');

// --- styles.css has all shared classes ---
ok(stylesCSS.indexOf('.form-card') > 0, 'styles.css: has .form-card');
ok(stylesCSS.indexOf('.form-group') > 0, 'styles.css: has .form-group');
ok(stylesCSS.indexOf('.consent-btn') > 0, 'styles.css: has .consent-btn');
ok(stylesCSS.indexOf('.consent-box') > 0, 'styles.css: has .consent-box');
ok(stylesCSS.indexOf('.submit-btn') > 0, 'styles.css: has .submit-btn');
ok(stylesCSS.indexOf('.error-msg') > 0, 'styles.css: has .error-msg');
ok(stylesCSS.indexOf('.success-msg') > 0, 'styles.css: has .success-msg');
ok(stylesCSS.indexOf('.membership-type') > 0, 'styles.css: has .membership-type');
ok(stylesCSS.indexOf('.type-btn') > 0, 'styles.css: has .type-btn');
ok(stylesCSS.indexOf('.family-section') > 0, 'styles.css: has .family-section');
ok(stylesCSS.indexOf('.fee-summary') > 0, 'styles.css: has .fee-summary');
ok(stylesCSS.indexOf('.gdpr-box') > 0, 'styles.css: has .gdpr-box');
ok(stylesCSS.indexOf('.donate-card') > 0, 'styles.css: has .donate-card');
ok(stylesCSS.indexOf('.amount-grid') > 0, 'styles.css: has .amount-grid');
ok(stylesCSS.indexOf('.amount-btn') > 0, 'styles.css: has .amount-btn');
ok(stylesCSS.indexOf('.swish-btn') > 0, 'styles.css: has .swish-btn');
ok(stylesCSS.indexOf('.back-link') > 0, 'styles.css: has .back-link');
ok(stylesCSS.indexOf('.policy') > 0, 'styles.css: has .policy (privacy)');

console.log('\nshared helpers tests done: ' + passed + ' passed, ' + failed + ' failed');
if (failed > 0) process.exit(1);
