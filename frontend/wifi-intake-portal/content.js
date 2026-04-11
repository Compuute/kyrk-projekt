/*
 * Content decision logic for the Wi-Fi portal.
 *
 * Exports (via global `window` in the browser, `module.exports` in Node):
 *   - decideContent(config, context): pure function — returns the view model
 *   - renderContent(view): DOM renderer (browser only)
 *   - loadContent(url): fetch + JSON parse (browser only)
 *
 * The decision logic is pure so it can be unit-tested with Node's built-in
 * assert module — no framework, no build step.
 */

function decideContent(config, context) {
  // Defensive defaults so a broken config never crashes the page.
  var lang = (context && context.lang) || 'sv';
  var date = (context && context.date) || new Date();
  var weekday = date.getDay(); // 0 = Sunday
  var byLang = (config && config.languages && config.languages[lang]) || {};
  var base = byLang.base || {};
  var sections = byLang.sections || {};

  var eventKey = pickEventKey(config, date);
  var eventContent = (sections[eventKey]) || sections['default'] || {};

  return {
    lang: lang,
    title: eventContent.title || base.title || 'Välkommen',
    subtitle: eventContent.subtitle || base.subtitle || '',
    today: eventContent.today || [],
    links: {
      member: base.links && base.links.member || '#',
      youth: base.links && base.links.youth || '#',
      kids: base.links && base.links.kids || '#',
      tech: base.links && base.links.tech || '#',
      donate: base.links && base.links.donate || '#'
    },
    weekday: weekday
  };
}

function pickEventKey(config, date) {
  // A config may declare `events: [{ key, from, to }]` windows. First match wins.
  var iso = date.toISOString().slice(0, 10);
  var events = (config && config.events) || [];
  for (var i = 0; i < events.length; i++) {
    var e = events[i];
    if (e.from <= iso && iso <= e.to) return e.key;
  }
  // Fallback: weekday-based default ("sunday" on day 0, else "weekday")
  return date.getDay() === 0 ? 'sunday' : 'weekday';
}

function renderContent(view) {
  var el = function (id) { return document.getElementById(id); };
  el('hero-title').textContent = view.title;
  el('hero-subtitle').textContent = view.subtitle;
  var list = el('today-list');
  list.innerHTML = '';
  (view.today || []).forEach(function (item) {
    var li = document.createElement('li');
    li.textContent = item;
    list.appendChild(li);
  });
  el('link-member').href = view.links.member;
  el('link-youth').href = view.links.youth;
  el('link-kids').href = view.links.kids;
  el('link-tech').href = view.links.tech;
  el('link-donate').href = view.links.donate;
}

function loadContent(url) {
  return fetch(url, { credentials: 'omit', cache: 'no-store' })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('bad config')); })
    .catch(function () { return (typeof window !== 'undefined' && window.DEFAULT_CONTENT) || {}; });
}

// Browser exposure
if (typeof window !== 'undefined') {
  window.decideContent = decideContent;
  window.renderContent = renderContent;
  window.loadContent = loadContent;
  window.DEFAULT_CONTENT = {
    languages: {
      sv: {
        base: { title: 'Välkommen', subtitle: 'Fri Wi-Fi', links: {} },
        sections: { default: { today: [] } }
      }
    }
  };
}

// Node exposure (for tests)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { decideContent: decideContent, pickEventKey: pickEventKey };
}
