/*
 * Member portal logic for the bilingual church site (sv + am).
 *
 * SOURCE: app.ts — compiled to app.js by esbuild (see Makefile: make build-js).
 * Do NOT edit app.js directly — it is generated output.
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
 * assert module — no framework, no build step required for tests.
 */

// ─────────────────────────────────────────────────────────── Type contracts

/** Supported UI languages. Enforced at compile time — 'svenska' will not compile. */
type Lang = 'sv' | 'am';

/** A bilingual text field as stored in content.json. */
interface BilingualText {
  sv: string;
  am: string;
}

/** A bilingual link entry (text is bilingual, url is shared). */
interface BilingualLink extends BilingualText {
  url: string;
}

/** A single upcoming activity from content.json. */
interface Activity {
  title: BilingualText;
  date: string;
  time: string;
  description: BilingualText;
}

/** A single announcement from content.json. */
interface Announcement {
  title: BilingualText;
  date: string;
  body: BilingualText;
}

/** Footer block in content.json. */
interface FooterConfig {
  privacy: BilingualText;
  privacy_url?: string;
}

/** The full content.json schema for one church. */
interface ContentConfig {
  version?: string;
  church: {
    name: BilingualText;
    tagline: BilingualText;
  };
  upcoming: Activity[];
  announcements: Announcement[];
  links: Record<string, BilingualLink>;
  footer: FooterConfig;
  youtube_channel_id?: string;
}

/** Flattened single-language view used by renderPage(). */
interface PageView {
  churchName: string;
  churchTagline: string;
  upcoming: Array<{ title: string; date: string; time: string; description: string }>;
  announcements: Array<{ title: string; date: string; body: string }>;
  links: Record<string, { text: string; url: string }>;
  footerPrivacy: string;
}

/** A church entry from churches.json. */
interface Church {
  id: string;
  name: BilingualText;
  city: string;
  address?: string;
  phone?: string;
  email?: string;
  org_number?: string;
  coords?: { lat: number; lng: number };
}

// ─────────────────────────────────────────────────────────────────── helpers

/**
 * Given a bilingual object like {"sv": "Hej", "am": "ሰላም"},
 * return the text for `lang`, falling back to "sv" if the key is missing.
 */
function _t(obj: BilingualText | undefined, lang: Lang): string {
  if (!obj || typeof obj !== 'object') return '';
  if (typeof obj[lang] === 'string') return obj[lang];
  if (typeof obj.sv === 'string') return obj.sv;
  return '';
}

// ──────────────────────────────────────────────────────────── pure functions

function pickLanguage(config: Partial<ContentConfig> | null | undefined, lang: Lang): PageView {
  if (!config || typeof config !== 'object') {
    return { churchName: '', churchTagline: '', upcoming: [], announcements: [], links: {}, footerPrivacy: '' };
  }
  const l = lang || 'sv';
  const church = config.church ?? { name: { sv: '', am: '' }, tagline: { sv: '', am: '' } };
  const upcoming = (config.upcoming ?? []).map(item => ({
    title: _t(item.title, l),
    date: item.date ?? '',
    time: item.time ?? '',
    description: _t(item.description, l),
  }));
  const announcements = (config.announcements ?? []).map(item => ({
    title: _t(item.title, l),
    date: item.date ?? '',
    body: _t(item.body, l),
  }));
  const rawLinks = config.links ?? {};
  const links: Record<string, { text: string; url: string }> = {};
  Object.keys(rawLinks).forEach(key => {
    const entry = rawLinks[key];
    if (entry) {
      links[key] = { text: _t(entry, l), url: entry.url ?? '#' };
    }
  });
  const footer = config.footer ?? { privacy: { sv: '', am: '' } };
  return {
    churchName: _t(church.name, l),
    churchTagline: _t(church.tagline, l),
    upcoming,
    announcements,
    links,
    footerPrivacy: _t(footer.privacy, l),
  };
}

function renderPage(content: Partial<ContentConfig> | null | undefined, lang: Lang): void {
  if (typeof document === 'undefined') return; // Node safety

  const view = pickLanguage(content, lang);
  const l = lang ?? 'sv';

  // Set body data-lang for CSS font selection
  document.body.setAttribute('data-lang', l);

  const el = (id: string): HTMLElement | null => document.getElementById(id);

  // Header
  const nameEl = el('church-name');
  if (nameEl) nameEl.textContent = view.churchName;
  const taglineEl = el('church-tagline');
  if (taglineEl) taglineEl.textContent = view.churchTagline;

  // Section titles
  const upcomingTitle = l === 'am' ? 'የቀረቡ ዝግጅቶች' : 'Kommande aktiviteter';
  const announcementsTitle = l === 'am' ? 'ማስታወቂያዎች' : 'Meddelanden';
  const upTitleEl = el('upcoming-title');
  if (upTitleEl) upTitleEl.textContent = upcomingTitle;
  const annTitleEl = el('announcements-title');
  if (annTitleEl) annTitleEl.textContent = announcementsTitle;

  // Upcoming activities
  const upList = el('upcoming-list');
  if (upList) {
    upList.innerHTML = '';
    if (view.upcoming.length === 0) {
      const emptyDiv = document.createElement('div');
      emptyDiv.className = 'empty';
      emptyDiv.textContent = l === 'am' ? 'ምንም ዝግጅት የለም' : 'Inga kommande aktiviteter';
      upList.appendChild(emptyDiv);
    } else {
      view.upcoming.forEach(item => {
        const div = document.createElement('div');
        div.className = 'activity-item';
        const titleEl = document.createElement('div');
        titleEl.className = 'activity-title';
        titleEl.textContent = item.title;
        const metaEl = document.createElement('div');
        metaEl.className = 'activity-meta';
        metaEl.textContent = item.date + ' kl ' + item.time;
        const descEl = document.createElement('div');
        descEl.className = 'activity-desc';
        descEl.textContent = item.description;
        div.appendChild(titleEl);
        div.appendChild(metaEl);
        div.appendChild(descEl);
        upList.appendChild(div);
      });
    }
  }

  // Announcements
  const annList = el('announcements-list');
  if (annList) {
    annList.innerHTML = '';
    if (view.announcements.length === 0) {
      const emptyAnn = document.createElement('div');
      emptyAnn.className = 'empty';
      emptyAnn.textContent = l === 'am' ? 'ምንም ማስታወቂያ የለም' : 'Inga meddelanden';
      annList.appendChild(emptyAnn);
    } else {
      view.announcements.forEach(item => {
        const div = document.createElement('div');
        div.className = 'announcement-item';
        const titleEl = document.createElement('div');
        titleEl.className = 'announcement-title';
        titleEl.textContent = item.title;
        const dateEl = document.createElement('div');
        dateEl.className = 'announcement-date';
        dateEl.textContent = item.date;
        const bodyEl = document.createElement('div');
        bodyEl.className = 'announcement-body';
        bodyEl.textContent = item.body;
        div.appendChild(titleEl);
        div.appendChild(dateEl);
        div.appendChild(bodyEl);
        annList.appendChild(div);
      });
    }
  }

  // Quick links — render ALL links from content.json dynamically
  const linksContainer = el('quick-links');
  if (linksContainer) {
    linksContainer.innerHTML = '';
    Object.keys(view.links).forEach(key => {
      const link = view.links[key];
      if (!link?.text) return;
      const a = document.createElement('a');
      a.className = 'tile';
      a.id = 'link-' + key;
      a.href = link.url;
      a.textContent = link.text;
      linksContainer.appendChild(a);
    });
  }

  // Footer
  const footerEl = el('footer-privacy');
  if (footerEl) {
    const privacyUrl = content?.footer?.privacy_url ?? './privacy';
    footerEl.innerHTML = '';
    footerEl.appendChild(document.createTextNode(view.footerPrivacy + ' '));
    const privacyLink = document.createElement('a');
    privacyLink.href = privacyUrl;
    privacyLink.textContent = l === 'am' ? 'ያንብቡ →' : 'Läs här →';
    privacyLink.style.color = 'inherit';
    privacyLink.style.textDecoration = 'underline';
    footerEl.appendChild(privacyLink);
  }

  // Update language pills
  const pills = document.querySelectorAll<HTMLElement>('.lang-pill');
  pills.forEach(pill => {
    pill.classList.toggle('active', pill.getAttribute('data-lang') === l);
  });
}

function switchLanguage(lang: Lang): void {
  if (typeof window !== 'undefined' && (window as any)._memberPortalContent) {
    renderPage((window as any)._memberPortalContent as ContentConfig, lang);
  }
}

function detectLanguage(): Lang {
  if (typeof navigator === 'undefined') return 'sv';
  const navLang = (navigator.language ?? 'sv').toLowerCase();
  if (navLang.startsWith('am')) return 'am';
  return 'sv';
}

function loadContent(url: string): Promise<Partial<ContentConfig>> {
  return fetch(url, { credentials: 'omit', cache: 'no-store' })
    .then(r => r.ok ? r.json() as Promise<ContentConfig> : Promise.reject(new Error('bad config')))
    .catch(() => ({} as Partial<ContentConfig>));
}

function setupLanguageSwitcher(content: Partial<ContentConfig>): void {
  if (typeof window !== 'undefined') {
    (window as any)._memberPortalContent = content;
  }
  if (typeof document === 'undefined') return;
  const pills = document.querySelectorAll<HTMLElement>('.lang-pill');
  pills.forEach(pill => {
    pill.addEventListener('click', function (this: HTMLElement) {
      const lang = this.getAttribute('data-lang') as Lang | null;
      if (lang === 'sv' || lang === 'am') switchLanguage(lang);
    });
  });
}

// Browser exposure
if (typeof window !== 'undefined') {
  (window as any).loadContent = loadContent;
  (window as any).pickLanguage = pickLanguage;
  (window as any).renderPage = renderPage;
  (window as any).switchLanguage = switchLanguage;
  (window as any).detectLanguage = detectLanguage;
  (window as any).setupLanguageSwitcher = setupLanguageSwitcher;
}

// ──────────────────────────────────────────────────── shared form helpers

function validateName(name: string): boolean {
  if (!name || name.trim().length < 2) return false;
  if (/\d/.test(name)) return false;
  return true;
}

function validatePhone(phone: string): boolean {
  if (!phone) return false;
  const clean = phone.replace(/[-\s]/g, '');
  return /^(\+46|0)\d{7,10}$/.test(clean);
}

function validatePersonnummer(pnr: string): boolean {
  if (!pnr) return true;
  let clean = pnr.replace(/[-\s]/g, '');
  if (clean.length === 12) clean = clean.substring(2);
  if (clean.length !== 10) return false;
  if (!/^\d{10}$/.test(clean)) return false;
  let sum = 0;
  for (let i = 0; i < 10; i++) {
    let d = parseInt(clean[i] ?? '0', 10);
    if (i % 2 === 0) d *= 2;
    if (d > 9) d -= 9;
    sum += d;
  }
  return sum % 10 === 0;
}

function toggleConsent(inputId?: string, btnId?: string, boxId?: string): void {
  const input = document.getElementById(inputId ?? 'field-gdpr-consent') as HTMLInputElement | null;
  const btn   = document.getElementById(btnId   ?? 'consent-btn');
  const box   = document.getElementById(boxId   ?? 'consent-box');
  if (!input || !btn || !box) return;
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

function buildSwishLink(swishNumber: string, amount: number, message?: string): string {
  if (!swishNumber || !amount) return '#';
  return 'swish://payment?data={"version":1,"payee":{"value":"' +
    swishNumber + '"},"amount":{"value":' + amount +
    '},"message":{"value":"' + (message ?? 'Betalning') + '","editable":false}}';
}

function setupLangPills(): void {
  const pills = document.querySelectorAll<HTMLElement>('.lang-pill');
  pills.forEach(pill => {
    pill.addEventListener('click', function (this: HTMLElement) {
      const lang = this.getAttribute('data-lang') as Lang | null;
      if (!lang) return;
      pills.forEach(p => p.classList.toggle('active', p.getAttribute('data-lang') === lang));
      document.body.setAttribute('data-lang', lang);
      applyLanguage(lang as Lang);
    });
  });
}

function applyLanguage(lang: Lang): void {
  document.querySelectorAll<HTMLElement>('.sv').forEach(el => { el.style.display = lang === 'sv' ? '' : 'none'; });
  document.querySelectorAll<HTMLElement>('.am').forEach(el => { el.style.display = lang === 'am' ? '' : 'none'; });
}

function registerServiceWorker(): void {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('/sw.js').then(reg => {
    reg.addEventListener('updatefound', () => {
      const newWorker = reg.installing;
      if (!newWorker) return;
      newWorker.addEventListener('statechange', () => {
        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
          showUpdateBanner(reg);
        }
      });
    });
  }).catch(() => {});
}

function showUpdateBanner(reg: ServiceWorkerRegistration): void {
  if (typeof document === 'undefined') return;
  const banner = document.createElement('div');
  banner.setAttribute('role', 'alert');
  banner.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:#7C3AED;color:#fff;padding:14px 20px;text-align:center;font-size:15px;font-weight:600;z-index:9999;display:flex;justify-content:center;align-items:center;gap:12px;';
  banner.innerHTML = '<span>Ny version tillgänglig</span><button style="background:#fff;color:#7C3AED;border:none;border-radius:8px;padding:8px 16px;font-weight:700;cursor:pointer;" id="sw-update-btn">Uppdatera</button>';
  document.body.appendChild(banner);
  document.getElementById('sw-update-btn')?.addEventListener('click', () => {
    reg.waiting?.postMessage({ type: 'SKIP_WAITING' });
    window.location.reload();
  });
}

function setupErrorMonitoring(): void {
  if (typeof window === 'undefined') return;
  window.addEventListener('error', () => {
    navigator.sendBeacon?.('https://membership-intake-479770870521.europe-north1.run.app/healthz', '');
  });
}

// ──────────────────────────────────────────────────────── church selector

function getSelectedChurch(): string {
  if (typeof localStorage === 'undefined') return 'nacka';
  return localStorage.getItem('selectedChurch') ?? 'nacka';
}

function setSelectedChurch(churchId: string): void {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('selectedChurch', churchId);
  }
}

function getContentUrl(): string {
  const church = getSelectedChurch();
  return './churches/' + church + '/content.json';
}

function loadChurchContent(callback: (data: Partial<ContentConfig>) => void): void {
  const url = getContentUrl();
  fetch(url, { credentials: 'omit', cache: 'no-store' })
    .then(r => {
      if (r.ok) return r.json() as Promise<ContentConfig>;
      return fetch('./content.json', { credentials: 'omit', cache: 'no-store' })
        .then(r2 => r2.ok ? r2.json() as Promise<ContentConfig> : {} as ContentConfig);
    })
    .then(data => callback(data))
    .catch(() => callback({}));
}

function initChurchSelector(): void {
  if (typeof document === 'undefined') return;

  const bar   = document.getElementById('church-bar');
  const modal = document.getElementById('church-modal');
  if (!bar || !modal) return;

  bar.addEventListener('click', () => modal.classList.add('open'));

  modal.querySelector<HTMLElement>('.church-modal-close')
    ?.addEventListener('click', () => modal.classList.remove('open'));

  modal.addEventListener('click', (e: Event) => {
    if (e.target === modal) modal.classList.remove('open');
  });

  fetch('./churches.json', { credentials: 'omit' })
    .then(r => r.ok ? r.json() as Promise<{ churches: Church[] }> : { churches: [] })
    .then(data => {
      const churches: Church[] = data.churches ?? [];
      const list    = modal.querySelector<HTMLElement>('.church-list');
      const search  = modal.querySelector<HTMLInputElement>('.church-search');
      const lang    = (document.body.getAttribute('data-lang') ?? 'sv') as Lang;
      const selected = getSelectedChurch();

      function renderList(filter: string): void {
        if (!list) return;
        list.innerHTML = '';
        const filtered = filter
          ? churches.filter(c =>
              (c.name.sv ?? '').toLowerCase().includes(filter.toLowerCase()) ||
              (c.name.am ?? '').includes(filter) ||
              (c.city ?? '').toLowerCase().includes(filter.toLowerCase()))
          : churches;
        filtered.forEach(c => {
          const item = document.createElement('div');
          item.className = 'church-list-item';
          item.innerHTML =
            '<div><div class="church-item-name">' + _t(c.name, lang) + '</div>' +
            '<div class="church-item-city">' + c.city + '</div></div>' +
            '<button class="church-item-select">' + (lang === 'am' ? 'ምረጥ' : 'Välj') + '</button>';
          item.addEventListener('click', () => { if (modal) showChurchDetail(c, modal, lang); });
          list.appendChild(item);
        });
      }

      renderList('');
      search?.addEventListener('input', function (this: HTMLInputElement) { renderList(this.value); });

      const current = churches.find(c => c.id === selected);
      if (current) {
        const nameEl = bar.querySelector<HTMLElement>('.church-bar-name');
        if (nameEl) nameEl.textContent = _t(current.name, lang) + ' — ' + current.city;
      }

      const locateBtn = modal.querySelector<HTMLElement>('.church-locate-btn');
      if (locateBtn && 'geolocation' in navigator) {
        locateBtn.addEventListener('click', () => {
          navigator.geolocation.getCurrentPosition(pos => {
            const { latitude: lat, longitude: lng } = pos.coords;
            churches.sort((a, b) => {
              const da = Math.pow((a.coords?.lat ?? 0) - lat, 2) + Math.pow((a.coords?.lng ?? 0) - lng, 2);
              const db = Math.pow((b.coords?.lat ?? 0) - lat, 2) + Math.pow((b.coords?.lng ?? 0) - lng, 2);
              return da - db;
            });
            renderList('');
          });
        });
      }
    })
    .catch(() => {});
}

function applyChurchToPage(church: Church, lang: Lang): void {
  if (typeof document === 'undefined' || !church) return;
  const name = _t(church.name, lang);

  const titleEl = document.querySelector('title');
  if (titleEl && name) {
    const parts = titleEl.textContent?.split('—') ?? [];
    if (parts.length > 1) titleEl.textContent = (parts[0] ?? '').trim() + ' — ' + name;
  }

  const footerName = document.getElementById('footer-church-name');
  if (footerName) footerName.innerHTML = name;

  const footerOrg = document.getElementById('footer-org');
  if (footerOrg && church.org_number) footerOrg.textContent = 'Org.nr: ' + church.org_number;

  const footerPhone = document.getElementById('footer-phone') as HTMLAnchorElement | null;
  if (footerPhone && church.phone) {
    footerPhone.href = 'tel:' + church.phone.replace(/\s/g, '');
    footerPhone.textContent = church.phone;
  }
}

function initChurchData(): void {
  if (typeof document === 'undefined') return;
  const churchId = getSelectedChurch();
  fetch('./churches.json', { credentials: 'omit' })
    .then(r => r.ok ? r.json() as Promise<{ churches: Church[] }> : { churches: [] })
    .then(data => {
      const church = (data.churches ?? []).find(c => c.id === churchId);
      if (church) {
        const lang = (document.body.getAttribute('data-lang') ?? 'sv') as Lang;
        applyChurchToPage(church, lang);
      }
    })
    .catch(() => {});
}

function showChurchDetail(church: Church, modal: HTMLElement, lang: Lang): void {
  const inner = modal.querySelector<HTMLElement>('.church-modal-inner');
  if (!inner) return;
  const name = _t(church.name, lang);
  inner.innerHTML =
    '<button class="church-modal-close" onclick="this.closest(\'.church-modal\').classList.remove(\'open\')">Stäng &#x2715;</button>' +
    '<h2>' + name + '</h2>' +
    '<div style="margin:16px 0">' +
      (church.address ? '<p><strong>' + (lang === 'am' ? 'አድራሻ:' : 'Besöksadress:') + '</strong><br/>' + church.address + '</p>' : '') +
      (church.phone   ? '<p style="margin-top:12px"><strong>' + (lang === 'am' ? 'ስልክ:' : 'Telefon:') + '</strong><br/>' + church.phone + '</p>' : '') +
      (church.email   ? '<p style="margin-top:12px"><strong>' + (lang === 'am' ? 'ኢሜይል:' : 'E-post:') + '</strong><br/>' + church.email + '</p>' : '') +
      (church.org_number ? '<p style="margin-top:12px;font-size:13px;color:var(--muted)">Org.nr: ' + church.org_number + '</p>' : '') +
    '</div>' +
    '<button class="church-locate-btn" id="select-church-btn" style="margin-top:16px">' +
      (lang === 'am' ? 'ይህንን ቤተ ክርስቲያን ይምረጡ' : 'Välj denna kyrka') +
    '</button>' +
    '<button style="display:block;width:100%;padding:12px;margin-top:8px;background:none;border:1px solid var(--border);border-radius:10px;color:var(--fg);cursor:pointer;font-size:14px" onclick="window.location.reload()">' +
      (lang === 'am' ? 'ተመለስ' : 'Tillbaka till listan') +
    '</button>';
  document.getElementById('select-church-btn')?.addEventListener('click', () => {
    setSelectedChurch(church.id);
    const churchIdField = document.getElementById('field-church-id') as HTMLInputElement | null;
    if (churchIdField) churchIdField.value = church.id;
    window.location.reload();
  });
}

// Browser exposure
if (typeof window !== 'undefined') {
  (window as any).validateName          = validateName;
  (window as any).validatePhone         = validatePhone;
  (window as any).validatePersonnummer  = validatePersonnummer;
  (window as any).toggleConsent         = toggleConsent;
  (window as any).buildSwishLink        = buildSwishLink;
  (window as any).setupLangPills        = setupLangPills;
  (window as any).registerServiceWorker = registerServiceWorker;
  (window as any).initChurchSelector    = initChurchSelector;
  (window as any).initChurchData        = initChurchData;
  (window as any).applyChurchToPage     = applyChurchToPage;
  (window as any).getSelectedChurch     = getSelectedChurch;
  (window as any).getContentUrl         = getContentUrl;
  (window as any).loadChurchContent     = loadChurchContent;
  setupErrorMonitoring();
}

// Node exposure (for tests — they import the compiled app.js, not app.ts)
if (typeof module !== 'undefined' && (module as any).exports) {
  (module as any).exports = {
    pickLanguage,
    renderPage,
    switchLanguage,
    detectLanguage,
    _t,
    validateName,
    validatePhone,
    validatePersonnummer,
    buildSwishLink,
  };
}
