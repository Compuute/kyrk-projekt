/*
 * Member portal logic for the bilingual church site (sv + am).
 *
 * Exports (via global `window` in the browser, `module.exports` in Node):
 *   - loadContent(url): fetch + JSON parse (browser only)
 *   - pickLanguage(config, lang): extract text for one language from bilingual config
 *   - renderPage(content, lang): populate DOM elements
 *   - switchLanguage(lang): re-render without reload
 *   - detectLanguage(): pick default from navigator.language
 *   - setupLanguageSwitcher(content): wire up the language pill buttons
 *
 * The decision logic is pure so it can be unit-tested with Node's built-in
 * assert module — no framework, no build step.
 */

// ----------------------------------------------------------------- helpers

/**
 * Given a bilingual object like {"sv": "Hej", "am": "ሰላም"},
 * return the text for `lang`, falling back to "sv" if the key is missing.
 */
function _t(obj, lang) {
  if (!obj || typeof obj !== 'object') return '';
  if (typeof obj[lang] === 'string') return obj[lang];
  if (typeof obj.sv === 'string') return obj.sv;
  return '';
}

// ---------------------------------------------------------- pure functions

function pickLanguage(config, lang) {
  if (!config || typeof config !== 'object') {
    return {
      churchName: '',
      churchTagline: '',
      upcoming: [],
      announcements: [],
      links: {},
      footerPrivacy: ''
    };
  }
  var l = lang || 'sv';
  var church = config.church || {};
  var upcoming = (config.upcoming || []).map(function (item) {
    return {
      title: _t(item.title, l),
      date: item.date || '',
      time: item.time || '',
      description: _t(item.description, l)
    };
  });
  var announcements = (config.announcements || []).map(function (item) {
    return {
      title: _t(item.title, l),
      date: item.date || '',
      body: _t(item.body, l)
    };
  });
  var rawLinks = config.links || {};
  var links = {};
  Object.keys(rawLinks).forEach(function (key) {
    var entry = rawLinks[key];
    links[key] = {
      text: _t(entry, l),
      url: (entry && entry.url) || '#'
    };
  });
  var footer = config.footer || {};
  return {
    churchName: _t(church.name, l),
    churchTagline: _t(church.tagline, l),
    upcoming: upcoming,
    announcements: announcements,
    links: links,
    footerPrivacy: _t(footer.privacy, l)
  };
}

function renderPage(content, lang) {
  if (typeof document === 'undefined') return; // Node safety

  var view = pickLanguage(content, lang);
  var l = lang || 'sv';

  // Set body data-lang for CSS font selection
  document.body.setAttribute('data-lang', l);

  var el = function (id) { return document.getElementById(id); };

  // Header
  el('church-name').textContent = view.churchName;
  el('church-tagline').textContent = view.churchTagline;

  // Section titles
  var upcomingTitle = l === 'am' ? 'የቀረቡ ዝግጅቶች' : 'Kommande aktiviteter';
  var announcementsTitle = l === 'am' ? 'ማስታወቂያዎች' : 'Meddelanden';
  el('upcoming-title').textContent = upcomingTitle;
  el('announcements-title').textContent = announcementsTitle;

  // Upcoming activities
  var upList = el('upcoming-list');
  upList.innerHTML = '';
  if (view.upcoming.length === 0) {
    var emptyDiv = document.createElement('div');
    emptyDiv.className = 'empty';
    emptyDiv.textContent = l === 'am' ? 'ምንም ዝግጅት የለም' : 'Inga kommande aktiviteter';
    upList.appendChild(emptyDiv);
  } else {
    view.upcoming.forEach(function (item) {
      var div = document.createElement('div');
      div.className = 'activity-item';
      var titleEl = document.createElement('div');
      titleEl.className = 'activity-title';
      titleEl.textContent = item.title;
      var metaEl = document.createElement('div');
      metaEl.className = 'activity-meta';
      metaEl.textContent = item.date + ' kl ' + item.time;
      var descEl = document.createElement('div');
      descEl.className = 'activity-desc';
      descEl.textContent = item.description;
      div.appendChild(titleEl);
      div.appendChild(metaEl);
      div.appendChild(descEl);
      upList.appendChild(div);
    });
  }

  // Announcements
  var annList = el('announcements-list');
  annList.innerHTML = '';
  if (view.announcements.length === 0) {
    var emptyAnn = document.createElement('div');
    emptyAnn.className = 'empty';
    emptyAnn.textContent = l === 'am' ? 'ምንም ማስታወቂያ የለም' : 'Inga meddelanden';
    annList.appendChild(emptyAnn);
  } else {
    view.announcements.forEach(function (item) {
      var div = document.createElement('div');
      div.className = 'announcement-item';
      var titleEl = document.createElement('div');
      titleEl.className = 'announcement-title';
      titleEl.textContent = item.title;
      var dateEl = document.createElement('div');
      dateEl.className = 'announcement-date';
      dateEl.textContent = item.date;
      var bodyEl = document.createElement('div');
      bodyEl.className = 'announcement-body';
      bodyEl.textContent = item.body;
      div.appendChild(titleEl);
      div.appendChild(dateEl);
      div.appendChild(bodyEl);
      annList.appendChild(div);
    });
  }

  // Quick links — render ALL links from content.json dynamically
  var linksContainer = el('quick-links');
  if (linksContainer) {
    linksContainer.innerHTML = '';
    Object.keys(view.links).forEach(function (key) {
      var link = view.links[key];
      if (!link || !link.text) return;
      var a = document.createElement('a');
      a.className = 'tile';
      a.id = 'link-' + key;
      a.href = link.url;
      a.textContent = link.text;
      linksContainer.appendChild(a);
    });
  }

  // Footer
  var footerEl = el('footer-privacy');
  if (footerEl) {
    var privacyUrl = (content.footer && content.footer.privacy_url) || './privacy';
    footerEl.innerHTML = '';
    footerEl.appendChild(document.createTextNode(view.footerPrivacy + ' '));
    var privacyLink = document.createElement('a');
    privacyLink.href = privacyUrl;
    privacyLink.textContent = l === 'am' ? 'ያንብቡ →' : 'Läs här →';
    privacyLink.style.color = 'inherit';
    privacyLink.style.textDecoration = 'underline';
    footerEl.appendChild(privacyLink);
  }

  // Update language pills
  var pills = document.querySelectorAll('.lang-pill');
  for (var i = 0; i < pills.length; i++) {
    pills[i].classList.toggle('active', pills[i].getAttribute('data-lang') === l);
  }
}

function switchLanguage(lang) {
  // _currentContent is set by setupLanguageSwitcher
  if (typeof window !== 'undefined' && window._memberPortalContent) {
    renderPage(window._memberPortalContent, lang);
  }
}

function detectLanguage() {
  if (typeof navigator === 'undefined') return 'sv';
  var navLang = (navigator.language || 'sv').toLowerCase();
  if (navLang.indexOf('am') === 0) return 'am';
  if (navLang.indexOf('sv') === 0) return 'sv';
  return 'sv';
}

function loadContent(url) {
  return fetch(url, { credentials: 'omit', cache: 'no-store' })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('bad config')); })
    .catch(function () { return {}; });
}

function setupLanguageSwitcher(content) {
  if (typeof window !== 'undefined') {
    window._memberPortalContent = content;
  }
  if (typeof document === 'undefined') return;
  var pills = document.querySelectorAll('.lang-pill');
  for (var i = 0; i < pills.length; i++) {
    pills[i].addEventListener('click', function () {
      var lang = this.getAttribute('data-lang');
      switchLanguage(lang);
    });
  }
}

// Browser exposure
if (typeof window !== 'undefined') {
  window.loadContent = loadContent;
  window.pickLanguage = pickLanguage;
  window.renderPage = renderPage;
  window.switchLanguage = switchLanguage;
  window.detectLanguage = detectLanguage;
  window.setupLanguageSwitcher = setupLanguageSwitcher;
}

// --------------------------------------------------- shared form helpers

function validateName(name) {
  if (!name || name.trim().length < 2) return false;
  if (/\d/.test(name)) return false;
  return true;
}

function validatePhone(phone) {
  if (!phone) return false;
  var clean = phone.replace(/[-\s]/g, '');
  return /^(\+46|0)\d{7,10}$/.test(clean);
}

function validatePersonnummer(pnr) {
  if (!pnr) return true;
  var clean = pnr.replace(/[-\s]/g, '');
  if (clean.length === 12) clean = clean.substring(2);
  if (clean.length !== 10) return false;
  if (!/^\d{10}$/.test(clean)) return false;
  var sum = 0;
  for (var i = 0; i < 10; i++) {
    var d = parseInt(clean[i], 10);
    if (i % 2 === 0) d *= 2;
    if (d > 9) d -= 9;
    sum += d;
  }
  return sum % 10 === 0;
}

function toggleConsent(inputId, btnId, boxId) {
  var input = document.getElementById(inputId || 'field-gdpr-consent');
  var btn = document.getElementById(btnId || 'consent-btn');
  var box = document.getElementById(boxId || 'consent-box');
  if (input.value === 'true') {
    input.value = '';
    btn.classList.remove('checked');
    box.textContent = '';
  } else {
    input.value = 'true';
    btn.classList.add('checked');
    box.textContent = '✓';
  }
}

function buildSwishLink(swishNumber, amount, message) {
  if (!swishNumber || !amount) return '#';
  return 'swish://payment?data={"version":1,"payee":{"value":"' +
    swishNumber + '"},"amount":{"value":' + amount +
    '},"message":{"value":"' + (message || 'Betalning') + '","editable":false}}';
}

function setupLangPills() {
  var pills = document.querySelectorAll('.lang-pill');
  for (var i = 0; i < pills.length; i++) {
    pills[i].addEventListener('click', function () {
      var lang = this.getAttribute('data-lang');
      for (var j = 0; j < pills.length; j++) {
        pills[j].classList.toggle('active', pills[j].getAttribute('data-lang') === lang);
      }
      document.body.setAttribute('data-lang', lang);
    });
  }
}

function registerServiceWorker() {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('/sw.js').then(function (reg) {
    reg.addEventListener('updatefound', function () {
      var newWorker = reg.installing;
      if (!newWorker) return;
      newWorker.addEventListener('statechange', function () {
        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
          showUpdateBanner(reg);
        }
      });
    });
  }).catch(function () {});
}

function showUpdateBanner(reg) {
  if (typeof document === 'undefined') return;
  var banner = document.createElement('div');
  banner.setAttribute('role', 'alert');
  banner.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:#7C3AED;color:#fff;padding:14px 20px;text-align:center;font-size:15px;font-weight:600;z-index:9999;display:flex;justify-content:center;align-items:center;gap:12px;';
  banner.innerHTML = '<span>Ny version tillgänglig</span><button style="background:#fff;color:#7C3AED;border:none;border-radius:8px;padding:8px 16px;font-weight:700;cursor:pointer;" id="sw-update-btn">Uppdatera</button>';
  document.body.appendChild(banner);
  document.getElementById('sw-update-btn').addEventListener('click', function () {
    if (reg && reg.waiting) reg.waiting.postMessage({ type: 'SKIP_WAITING' });
    window.location.reload();
  });
}

function setupErrorMonitoring() {
  if (typeof window === 'undefined') return;
  window.addEventListener('error', function (e) {
    if (navigator.sendBeacon) {
      navigator.sendBeacon('https://membership-intake-479770870521.europe-north1.run.app/healthz', '');
    }
  });
}

// ------------------------------------------------ church selector

function getSelectedChurch() {
  if (typeof localStorage === 'undefined') return 'nacka';
  return localStorage.getItem('selectedChurch') || 'nacka';
}

function setSelectedChurch(churchId) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('selectedChurch', churchId);
  }
}

function getContentUrl() {
  var church = getSelectedChurch();
  return './churches/' + church + '/content.json';
}

function loadChurchContent(callback) {
  var url = getContentUrl();
  fetch(url, { credentials: 'omit', cache: 'no-store' })
    .then(function (r) {
      if (r.ok) return r.json();
      return fetch('./content.json', { credentials: 'omit', cache: 'no-store' })
        .then(function (r2) { return r2.ok ? r2.json() : {}; });
    })
    .then(function (data) { callback(data); })
    .catch(function () { callback({}); });
}

function initChurchSelector() {
  if (typeof document === 'undefined') return;

  var bar = document.getElementById('church-bar');
  var modal = document.getElementById('church-modal');
  if (!bar || !modal) return;

  bar.addEventListener('click', function () { modal.classList.add('open'); });

  var closeBtn = modal.querySelector('.church-modal-close');
  if (closeBtn) closeBtn.addEventListener('click', function () { modal.classList.remove('open'); });

  modal.addEventListener('click', function (e) {
    if (e.target === modal) modal.classList.remove('open');
  });

  fetch('./churches.json', { credentials: 'omit' })
    .then(function (r) { return r.ok ? r.json() : { churches: [] }; })
    .then(function (data) {
      var churches = data.churches || [];
      var list = modal.querySelector('.church-list');
      var search = modal.querySelector('.church-search');
      var lang = document.body.getAttribute('data-lang') || 'sv';
      var selected = getSelectedChurch();

      function renderList(filter) {
        list.innerHTML = '';
        var filtered = churches.filter(function (c) {
          if (!filter) return true;
          var q = filter.toLowerCase();
          return (c.name.sv || '').toLowerCase().indexOf(q) >= 0 ||
                 (c.name.am || '').indexOf(q) >= 0 ||
                 (c.city || '').toLowerCase().indexOf(q) >= 0;
        });
        filtered.forEach(function (c) {
          var item = document.createElement('div');
          item.className = 'church-list-item';
          item.innerHTML = '<div><div class="church-item-name">' + _t(c.name, lang) + '</div>' +
            '<div class="church-item-city">' + c.city + '</div></div>' +
            '<button class="church-item-select">' + (lang === 'am' ? 'ምረጥ' : 'Välj') + '</button>';
          item.addEventListener('click', function () {
            showChurchDetail(c, modal, lang);
          });
          list.appendChild(item);
        });
      }

      renderList('');
      if (search) {
        search.addEventListener('input', function () { renderList(this.value); });
      }

      var current = churches.find(function (c) { return c.id === selected; });
      if (current) {
        var nameEl = bar.querySelector('.church-bar-name');
        if (nameEl) nameEl.textContent = _t(current.name, lang) + ' — ' + current.city;
      }

      var locateBtn = modal.querySelector('.church-locate-btn');
      if (locateBtn && navigator.geolocation) {
        locateBtn.addEventListener('click', function () {
          navigator.geolocation.getCurrentPosition(function (pos) {
            var lat = pos.coords.latitude;
            var lng = pos.coords.longitude;
            churches.sort(function (a, b) {
              var da = Math.pow(a.coords.lat - lat, 2) + Math.pow(a.coords.lng - lng, 2);
              var db = Math.pow(b.coords.lat - lat, 2) + Math.pow(b.coords.lng - lng, 2);
              return da - db;
            });
            renderList('');
          });
        });
      }
    })
    .catch(function () {});
}

function applyChurchToPage(church, lang) {
  if (typeof document === 'undefined' || !church) return;
  var name = _t(church.name, lang);

  // Page title
  var titleEl = document.querySelector('title');
  if (titleEl && name) {
    var parts = titleEl.textContent.split('—');
    if (parts.length > 1) titleEl.textContent = parts[0].trim() + ' — ' + name;
  }

  // Footer church name
  var footerName = document.getElementById('footer-church-name');
  if (footerName) footerName.innerHTML = name;

  // Footer org number
  var footerOrg = document.getElementById('footer-org');
  if (footerOrg && church.org_number) footerOrg.textContent = 'Org.nr: ' + church.org_number;

  // Footer phone
  var footerPhone = document.getElementById('footer-phone');
  if (footerPhone && church.phone) {
    footerPhone.href = 'tel:' + church.phone.replace(/\s/g, '');
    footerPhone.textContent = church.phone;
  }
}

function initChurchData() {
  if (typeof document === 'undefined') return;
  var churchId = getSelectedChurch();
  fetch('./churches.json', { credentials: 'omit' })
    .then(function (r) { return r.ok ? r.json() : { churches: [] }; })
    .then(function (data) {
      var church = (data.churches || []).find(function (c) { return c.id === churchId; });
      if (church) {
        var lang = document.body.getAttribute('data-lang') || 'sv';
        applyChurchToPage(church, lang);
      }
    })
    .catch(function () {});
}

function showChurchDetail(church, modal, lang) {
  var inner = modal.querySelector('.church-modal-inner');
  var name = _t(church.name, lang);
  inner.innerHTML =
    '<button class="church-modal-close" onclick="this.closest(\'.church-modal\').classList.remove(\'open\')">Stäng &#x2715;</button>' +
    '<h2>' + name + '</h2>' +
    '<div style="margin:16px 0">' +
      (church.address ? '<p><strong>' + (lang === 'am' ? 'አድራሻ:' : 'Besöksadress:') + '</strong><br/>' + church.address + '</p>' : '') +
      (church.phone ? '<p style="margin-top:12px"><strong>' + (lang === 'am' ? 'ስልክ:' : 'Telefon:') + '</strong><br/>' + church.phone + '</p>' : '') +
      (church.email ? '<p style="margin-top:12px"><strong>' + (lang === 'am' ? 'ኢሜይል:' : 'E-post:') + '</strong><br/>' + church.email + '</p>' : '') +
      (church.org_number ? '<p style="margin-top:12px;font-size:13px;color:var(--muted)">Org.nr: ' + church.org_number + '</p>' : '') +
    '</div>' +
    '<button class="church-locate-btn" id="select-church-btn" style="margin-top:16px">' +
      (lang === 'am' ? 'ይህንን ቤተ ክርስቲያን ይምረጡ' : 'Välj denna kyrka') +
    '</button>' +
    '<button style="display:block;width:100%;padding:12px;margin-top:8px;background:none;border:1px solid var(--border);border-radius:10px;color:var(--fg);cursor:pointer;font-size:14px" onclick="window.location.reload()">' +
      (lang === 'am' ? 'ተመለስ' : 'Tillbaka till listan') +
    '</button>';
  document.getElementById('select-church-btn').addEventListener('click', function () {
    setSelectedChurch(church.id);
    var churchIdField = document.getElementById('field-church-id');
    if (churchIdField) churchIdField.value = church.id;
    window.location.reload();
  });
}

if (typeof window !== 'undefined') {
  window.validateName = validateName;
  window.validatePhone = validatePhone;
  window.validatePersonnummer = validatePersonnummer;
  window.toggleConsent = toggleConsent;
  window.buildSwishLink = buildSwishLink;
  window.setupLangPills = setupLangPills;
  window.registerServiceWorker = registerServiceWorker;
  window.initChurchSelector = initChurchSelector;
  window.initChurchData = initChurchData;
  window.applyChurchToPage = applyChurchToPage;
  window.getSelectedChurch = getSelectedChurch;
  window.getContentUrl = getContentUrl;
  window.loadChurchContent = loadChurchContent;
  setupErrorMonitoring();
}

// Node exposure (for tests)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    pickLanguage: pickLanguage,
    renderPage: renderPage,
    switchLanguage: switchLanguage,
    detectLanguage: detectLanguage,
    _t: _t,
    validateName: validateName,
    validatePhone: validatePhone,
    validatePersonnummer: validatePersonnummer,
    buildSwishLink: buildSwishLink
  };
}
