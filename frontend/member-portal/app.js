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
  el('footer-privacy').textContent = view.footerPrivacy;

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

// Node exposure (for tests)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    pickLanguage: pickLanguage,
    renderPage: renderPage,
    switchLanguage: switchLanguage,
    detectLanguage: detectLanguage,
    _t: _t
  };
}
