"use strict";
function _t(obj, lang) {
  if (!obj || typeof obj !== "object") return "";
  if (typeof obj[lang] === "string") return obj[lang];
  if (typeof obj.sv === "string") return obj.sv;
  return "";
}
function pickLanguage(config, lang) {
  if (!config || typeof config !== "object") {
    return { churchName: "", churchTagline: "", upcoming: [], announcements: [], links: {}, footerPrivacy: "" };
  }
  const l = lang || "sv";
  const church = config.church ?? { name: { sv: "", am: "" }, tagline: { sv: "", am: "" } };
  const upcoming = (config.upcoming ?? []).map((item) => ({
    title: _t(item.title, l),
    date: item.date ?? "",
    time: item.time ?? "",
    description: _t(item.description, l)
  }));
  const announcements = (config.announcements ?? []).map((item) => ({
    title: _t(item.title, l),
    date: item.date ?? "",
    body: _t(item.body, l)
  }));
  const rawLinks = config.links ?? {};
  const links = {};
  Object.keys(rawLinks).forEach((key) => {
    const entry = rawLinks[key];
    if (entry) {
      links[key] = { text: _t(entry, l), url: entry.url ?? "#" };
    }
  });
  const footer = config.footer ?? { privacy: { sv: "", am: "" } };
  return {
    churchName: _t(church.name, l),
    churchTagline: _t(church.tagline, l),
    upcoming,
    announcements,
    links,
    footerPrivacy: _t(footer.privacy, l)
  };
}
function renderPage(content, lang) {
  if (typeof document === "undefined") return;
  const view = pickLanguage(content, lang);
  const l = lang ?? "sv";
  document.body.setAttribute("data-lang", l);
  const el = (id) => document.getElementById(id);
  const nameEl = el("church-name");
  if (nameEl) nameEl.textContent = view.churchName;
  const taglineEl = el("church-tagline");
  if (taglineEl) taglineEl.textContent = view.churchTagline;
  const upcomingTitle = l === "am" ? "\u12E8\u1240\u1228\u1261 \u12DD\u130D\u1305\u1276\u127D" : "Kommande aktiviteter";
  const announcementsTitle = l === "am" ? "\u121B\u1235\u1273\u12C8\u1242\u12EB\u12CE\u127D" : "Meddelanden";
  const upTitleEl = el("upcoming-title");
  if (upTitleEl) upTitleEl.textContent = upcomingTitle;
  const annTitleEl = el("announcements-title");
  if (annTitleEl) annTitleEl.textContent = announcementsTitle;
  const upList = el("upcoming-list");
  if (upList) {
    upList.innerHTML = "";
    if (view.upcoming.length === 0) {
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "empty";
      emptyDiv.textContent = l === "am" ? "\u121D\u1295\u121D \u12DD\u130D\u1305\u1275 \u12E8\u1208\u121D" : "Inga kommande aktiviteter";
      upList.appendChild(emptyDiv);
    } else {
      view.upcoming.forEach((item) => {
        const div = document.createElement("div");
        div.className = "activity-item";
        const titleEl = document.createElement("div");
        titleEl.className = "activity-title";
        titleEl.textContent = item.title;
        const metaEl = document.createElement("div");
        metaEl.className = "activity-meta";
        metaEl.textContent = item.date + " kl " + item.time;
        const descEl = document.createElement("div");
        descEl.className = "activity-desc";
        descEl.textContent = item.description;
        div.appendChild(titleEl);
        div.appendChild(metaEl);
        div.appendChild(descEl);
        upList.appendChild(div);
      });
    }
  }
  const annList = el("announcements-list");
  if (annList) {
    annList.innerHTML = "";
    if (view.announcements.length === 0) {
      const emptyAnn = document.createElement("div");
      emptyAnn.className = "empty";
      emptyAnn.textContent = l === "am" ? "\u121D\u1295\u121D \u121B\u1235\u1273\u12C8\u1242\u12EB \u12E8\u1208\u121D" : "Inga meddelanden";
      annList.appendChild(emptyAnn);
    } else {
      view.announcements.forEach((item) => {
        const div = document.createElement("div");
        div.className = "announcement-item";
        const titleEl = document.createElement("div");
        titleEl.className = "announcement-title";
        titleEl.textContent = item.title;
        const dateEl = document.createElement("div");
        dateEl.className = "announcement-date";
        dateEl.textContent = item.date;
        const bodyEl = document.createElement("div");
        bodyEl.className = "announcement-body";
        bodyEl.textContent = item.body;
        div.appendChild(titleEl);
        div.appendChild(dateEl);
        div.appendChild(bodyEl);
        annList.appendChild(div);
      });
    }
  }
  const linksContainer = el("quick-links");
  if (linksContainer) {
    linksContainer.innerHTML = "";
    Object.keys(view.links).forEach((key) => {
      const link = view.links[key];
      if (!link?.text) return;
      const a = document.createElement("a");
      a.className = "tile";
      a.id = "link-" + key;
      a.href = link.url;
      a.textContent = link.text;
      linksContainer.appendChild(a);
    });
  }
  const footerEl = el("footer-privacy");
  if (footerEl) {
    const privacyUrl = content?.footer?.privacy_url ?? "./privacy";
    footerEl.innerHTML = "";
    footerEl.appendChild(document.createTextNode(view.footerPrivacy + " "));
    const privacyLink = document.createElement("a");
    privacyLink.href = privacyUrl;
    privacyLink.textContent = l === "am" ? "\u12EB\u1295\u1265\u1261 \u2192" : "L\xE4s h\xE4r \u2192";
    privacyLink.style.color = "inherit";
    privacyLink.style.textDecoration = "underline";
    footerEl.appendChild(privacyLink);
  }
  const pills = document.querySelectorAll(".lang-pill");
  pills.forEach((pill) => {
    pill.classList.toggle("active", pill.getAttribute("data-lang") === l);
  });
}
function switchLanguage(lang) {
  if (typeof window !== "undefined" && window._memberPortalContent) {
    renderPage(window._memberPortalContent, lang);
  }
}
function detectLanguage() {
  if (typeof navigator === "undefined") return "sv";
  const navLang = (navigator.language ?? "sv").toLowerCase();
  if (navLang.startsWith("am")) return "am";
  return "sv";
}
function loadContent(url) {
  return fetch(url, { credentials: "omit", cache: "no-store" }).then((r) => r.ok ? r.json() : Promise.reject(new Error("bad config"))).catch(() => ({}));
}
function setupLanguageSwitcher(content) {
  if (typeof window !== "undefined") {
    window._memberPortalContent = content;
  }
  if (typeof document === "undefined") return;
  const pills = document.querySelectorAll(".lang-pill");
  pills.forEach((pill) => {
    pill.addEventListener("click", function() {
      const lang = this.getAttribute("data-lang");
      if (lang === "sv" || lang === "am") switchLanguage(lang);
    });
  });
}
if (typeof window !== "undefined") {
  window.loadContent = loadContent;
  window.pickLanguage = pickLanguage;
  window.renderPage = renderPage;
  window.switchLanguage = switchLanguage;
  window.detectLanguage = detectLanguage;
  window.setupLanguageSwitcher = setupLanguageSwitcher;
}
function validateName(name) {
  if (!name || name.trim().length < 2) return false;
  if (/\d/.test(name)) return false;
  return true;
}
function validatePhone(phone) {
  if (!phone) return false;
  const clean = phone.replace(/[-\s]/g, "");
  return /^(\+46|0)\d{7,10}$/.test(clean);
}
function validatePersonnummer(pnr) {
  if (!pnr) return true;
  let clean = pnr.replace(/[-\s]/g, "");
  if (clean.length === 12) clean = clean.substring(2);
  if (clean.length !== 10) return false;
  if (!/^\d{10}$/.test(clean)) return false;
  let sum = 0;
  for (let i = 0; i < 10; i++) {
    let d = parseInt(clean[i] ?? "0", 10);
    if (i % 2 === 0) d *= 2;
    if (d > 9) d -= 9;
    sum += d;
  }
  return sum % 10 === 0;
}
function toggleConsent(inputId, btnId, boxId) {
  const input = document.getElementById(inputId ?? "field-gdpr-consent");
  const btn = document.getElementById(btnId ?? "consent-btn");
  const box = document.getElementById(boxId ?? "consent-box");
  if (!input || !btn || !box) return;
  if (input.value === "true") {
    input.value = "";
    btn.classList.remove("checked");
    box.textContent = "";
  } else {
    input.value = "true";
    btn.classList.add("checked");
    box.textContent = "\u2713";
  }
}
function buildSwishLink(swishNumber, amount, message) {
  if (!swishNumber || !amount) return "#";
  const msg = (message ?? "Betalning").slice(0, 50);
  const data = JSON.stringify({
    version: 1,
    payee: { value: swishNumber },
    amount: { value: amount },
    message: { value: msg, editable: false }
  });
  return "swish://payment?data=" + encodeURIComponent(data);
}
function renderSwishQr(swishNumber, amount, message, container) {
  if (!container) return;
  const make = window.qrcode;
  if (typeof make !== "function" || !swishNumber || !amount) {
    container.innerHTML = "";
    return;
  }
  const data = "C" + swishNumber + ";" + amount + ";" + (message || "Betalning") + ";0";
  try {
    const qr = make(0, "M");
    qr.addData(data);
    qr.make();
    const img = document.createElement("img");
    img.src = qr.createDataURL(6, 8);
    img.alt = "Swish QR-kod \u2014 skanna med Swish-appen / Swish QR";
    img.width = 168;
    img.height = 168;
    img.style.display = "block";
    container.innerHTML = "";
    container.appendChild(img);
  } catch (_e) {
    container.innerHTML = "";
  }
}
function setupLangPills() {
  const pills = document.querySelectorAll(".lang-pill");
  pills.forEach((pill) => {
    pill.addEventListener("click", function() {
      const lang = this.getAttribute("data-lang");
      if (!lang) return;
      if (typeof document !== "undefined") {
        document.cookie = "selected_language=" + encodeURIComponent(lang) + "; path=/; max-age=31536000; SameSite=Lax";
      }
      if (typeof window !== "undefined") {
        const path = window.location.pathname;
        const isPrefixed = path.startsWith("/sv/") || path.startsWith("/am/") || path === "/sv" || path === "/am";
        if (isPrefixed) {
          const targetPrefix = "/" + lang;
          const currentPrefix = path.startsWith("/sv") ? "/sv" : "/am";
          const rest = path.substring(currentPrefix.length);
          window.location.href = targetPrefix + (rest || "/");
          return;
        }
      }
      pills.forEach((p) => p.classList.toggle("active", p.getAttribute("data-lang") === lang));
      document.body.setAttribute("data-lang", lang);
      applyLanguage(lang);
    });
  });
}
function applyLanguage(lang) {
  document.querySelectorAll(".sv").forEach((el) => {
    el.style.display = lang === "sv" ? "" : "none";
  });
  document.querySelectorAll(".am").forEach((el) => {
    el.style.display = lang === "am" ? "" : "none";
  });
}
function registerServiceWorker() {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  navigator.serviceWorker.register("/sw.js").then((reg) => {
    reg.addEventListener("updatefound", () => {
      const newWorker = reg.installing;
      if (!newWorker) return;
      newWorker.addEventListener("statechange", () => {
        if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
          showUpdateBanner(reg);
        }
      });
    });
  }).catch(() => {
  });
}
function showUpdateBanner(reg) {
  if (typeof document === "undefined") return;
  const banner = document.createElement("div");
  banner.setAttribute("role", "alert");
  banner.style.cssText = "position:fixed;bottom:0;left:0;right:0;background:#7C3AED;color:#fff;padding:14px 20px;text-align:center;font-size:15px;font-weight:600;z-index:9999;display:flex;justify-content:center;align-items:center;gap:12px;";
  banner.innerHTML = '<span>Ny version tillg\xE4nglig</span><button style="background:#fff;color:#7C3AED;border:none;border-radius:8px;padding:8px 16px;font-weight:700;cursor:pointer;" id="sw-update-btn">Uppdatera</button>';
  document.body.appendChild(banner);
  document.getElementById("sw-update-btn")?.addEventListener("click", () => {
    reg.waiting?.postMessage({ type: "SKIP_WAITING" });
    window.location.reload();
  });
}
function setupErrorMonitoring() {
  if (typeof window === "undefined") return;
  window.addEventListener("error", () => {
    const base = window.API_BASE_URL || "https://api.kyrka.compuute.net";
    navigator.sendBeacon?.(base + "/healthz", "");
  });
}
function getSelectedChurch() {
  if (typeof localStorage === "undefined" || typeof localStorage.getItem !== "function") return "nacka";
  return localStorage.getItem("selectedChurch") ?? "nacka";
}
function setSelectedChurch(churchId) {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("selectedChurch", churchId);
  }
  if (typeof document !== "undefined") {
    document.cookie = "selected_church=" + encodeURIComponent(churchId) + "; path=/; max-age=31536000; SameSite=Lax";
  }
}
function getContentUrl() {
  const church = getSelectedChurch();
  return "/churches/" + church + "/content.json";
}
function loadChurchContent(callback) {
  if (typeof window !== "undefined" && window.__KYRK_CONFIG__) {
    callback(window.__KYRK_CONFIG__);
    return;
  }
  const url = getContentUrl();
  fetch(url, { credentials: "omit", cache: "no-store" }).then((r) => {
    if (r.ok) return r.json();
    return fetch("/content.json", { credentials: "omit", cache: "no-store" }).then((r2) => r2.ok ? r2.json() : {});
  }).then((data) => callback(data)).catch(() => callback({}));
}
function initChurchSelector() {
  if (typeof document === "undefined") return;
  const bar = document.getElementById("church-bar");
  const modal = document.getElementById("church-modal");
  if (!bar || !modal) return;
  bar.addEventListener("click", () => modal.classList.add("open"));
  modal.querySelector(".church-modal-close")?.addEventListener("click", () => modal.classList.remove("open"));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("open");
  });
  fetch("/churches.json", { credentials: "omit" }).then((r) => r.ok ? r.json() : { churches: [] }).then((data) => {
    const churches = data.churches ?? [];
    const list = modal.querySelector(".church-list");
    const search = modal.querySelector(".church-search");
    const lang = document.body.getAttribute("data-lang") ?? "sv";
    const selected = getSelectedChurch();
    function renderList(filter) {
      if (!list) return;
      list.innerHTML = "";
      const filtered = filter ? churches.filter((c) => (c.name.sv ?? "").toLowerCase().includes(filter.toLowerCase()) || (c.name.am ?? "").includes(filter) || (c.city ?? "").toLowerCase().includes(filter.toLowerCase())) : churches;
      filtered.forEach((c) => {
        const item = document.createElement("div");
        item.className = "church-list-item";
        item.innerHTML = '<div><div class="church-item-name">' + _t(c.name, lang) + '</div><div class="church-item-city">' + c.city + '</div></div><button class="church-item-select">' + (lang === "am" ? "\u121D\u1228\u1325" : "V\xE4lj") + "</button>";
        item.addEventListener("click", () => {
          if (modal) showChurchDetail(c, modal, lang);
        });
        list.appendChild(item);
      });
    }
    renderList("");
    search?.addEventListener("input", function() {
      renderList(this.value);
    });
    const current = churches.find((c) => c.id === selected);
    if (current) {
      const nameEl = bar.querySelector(".church-bar-name");
      if (nameEl) nameEl.textContent = _t(current.name, lang) + " \u2014 " + current.city;
    }
    const locateBtn = modal.querySelector(".church-locate-btn");
    if (locateBtn && "geolocation" in navigator) {
      locateBtn.addEventListener("click", () => {
        navigator.geolocation.getCurrentPosition((pos) => {
          const { latitude: lat, longitude: lng } = pos.coords;
          churches.sort((a, b) => {
            const da = Math.pow((a.coords?.lat ?? 0) - lat, 2) + Math.pow((a.coords?.lng ?? 0) - lng, 2);
            const db = Math.pow((b.coords?.lat ?? 0) - lat, 2) + Math.pow((b.coords?.lng ?? 0) - lng, 2);
            return da - db;
          });
          renderList("");
        });
      });
    }
  }).catch(() => {
  });
}
function applyChurchToPage(church, lang) {
  if (typeof document === "undefined" || !church) return;
  const name = _t(church.name, lang);
  const titleEl = document.querySelector("title");
  if (titleEl && name) {
    const parts = titleEl.textContent?.split("\u2014") ?? [];
    if (parts.length > 1) titleEl.textContent = (parts[0] ?? "").trim() + " \u2014 " + name;
  }
  const footerName = document.getElementById("footer-church-name");
  if (footerName) footerName.innerHTML = name;
  const footerOrg = document.getElementById("footer-org");
  if (footerOrg && church.org_number) footerOrg.textContent = "Org.nr: " + church.org_number;
  const footerPhone = document.getElementById("footer-phone");
  if (footerPhone && church.phone) {
    footerPhone.href = "tel:" + church.phone.replace(/\s/g, "");
    footerPhone.textContent = church.phone;
  }
}
function initChurchData() {
  if (typeof document === "undefined") return;
  const churchId = getSelectedChurch();
  if (!document.cookie.includes("selected_church=")) {
    document.cookie = "selected_church=" + encodeURIComponent(churchId) + "; path=/; max-age=31536000; SameSite=Lax";
  }
  fetch("/churches.json", { credentials: "omit" }).then((r) => r.ok ? r.json() : { churches: [] }).then((data) => {
    const church = (data.churches ?? []).find((c) => c.id === churchId);
    if (church) {
      const lang = document.body.getAttribute("data-lang") ?? "sv";
      applyChurchToPage(church, lang);
    }
  }).catch(() => {
  });
}
function showChurchDetail(church, modal, lang) {
  const inner = modal.querySelector(".church-modal-inner");
  if (!inner) return;
  const name = _t(church.name, lang);
  inner.innerHTML = `<button class="church-modal-close" onclick="this.closest('.church-modal').classList.remove('open')">St\xE4ng &#x2715;</button><h2>` + name + '</h2><div style="margin:16px 0">' + (church.address ? "<p><strong>" + (lang === "am" ? "\u12A0\u12F5\u122B\u123B:" : "Bes\xF6ksadress:") + "</strong><br/>" + church.address + "</p>" : "") + (church.phone ? '<p style="margin-top:12px"><strong>' + (lang === "am" ? "\u1235\u120D\u12AD:" : "Telefon:") + "</strong><br/>" + church.phone + "</p>" : "") + (church.email ? '<p style="margin-top:12px"><strong>' + (lang === "am" ? "\u12A2\u121C\u12ED\u120D:" : "E-post:") + "</strong><br/>" + church.email + "</p>" : "") + (church.org_number ? '<p style="margin-top:12px;font-size:13px;color:var(--muted)">Org.nr: ' + church.org_number + "</p>" : "") + '</div><button class="church-locate-btn" id="select-church-btn" style="margin-top:16px">' + (lang === "am" ? "\u12ED\u1205\u1295\u1295 \u1264\u1270 \u12AD\u122D\u1235\u1272\u12EB\u1295 \u12ED\u121D\u1228\u1321" : "V\xE4lj denna kyrka") + '</button><button style="display:block;width:100%;padding:12px;margin-top:8px;background:none;border:1px solid var(--border);border-radius:10px;color:var(--fg);cursor:pointer;font-size:14px" onclick="window.location.reload()">' + (lang === "am" ? "\u1270\u1218\u1208\u1235" : "Tillbaka till listan") + "</button>";
  document.getElementById("select-church-btn")?.addEventListener("click", () => {
    setSelectedChurch(church.id);
    const churchIdField = document.getElementById("field-church-id");
    if (churchIdField) churchIdField.value = church.id;
    window.location.reload();
  });
}
if (typeof window !== "undefined") {
  window.API_BASE_URL = "https://api.kyrka.compuute.net";
  window.validateName = validateName;
  window.validatePhone = validatePhone;
  window.validatePersonnummer = validatePersonnummer;
  window.toggleConsent = toggleConsent;
  window.buildSwishLink = buildSwishLink;
  window.renderSwishQr = renderSwishQr;
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
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    pickLanguage,
    renderPage,
    switchLanguage,
    detectLanguage,
    _t,
    validateName,
    validatePhone,
    validatePersonnummer,
    buildSwishLink,
    getContentUrl
  };
}
