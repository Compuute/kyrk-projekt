// calendar-engine.js — etiopisk kalender + högtider för medlemsportalen.
//
// Konverteringen är ren aritmetik (den etiopiska kalendern är strikt
// regelbunden: 12 × 30 dagar + Pagume om 5/6 dagar, skottår vart fjärde år
// utan undantag). Korrektheten bevisas i tests/test_calendar_engine.js genom
// korsvalidering mot plattformens ICU-implementation (Intl, u-ca-ethiopic)
// över 7 800+ datum 1950–2100 — samma motor som Chrome/Android använder.
//
// Högtidsdata: fasta etiopisk-ortodoxa högtider (Bahire Hasab, publicerad
// tradition), månatliga helgondagar, svenska röda dagar (Lag 1989:253,
// rörliga härledda via gregoriansk computus). Endast GREEN-klassad publik
// data. Rörliga etiopiska fastor/högtider (t.ex. Fasika) ingår inte ännu.
//
// Noll beroenden. Körs i webbläsaren (window.KyrkCalendar) och i Node
// (module.exports) för testerna.

(function (root) {
  'use strict';

  // ---------------------------------------------------------------- JDN ---
  // Juliansk dagnummer-aritmetik. Epok för Amete Mihret: JDN 1724221
  // motsvarar Meskerem 1, år 1 E.C.
  var ETH_EPOCH = 1724221;

  function gregorianToJdn(y, m, d) {
    var a = Math.floor((14 - m) / 12);
    var yy = y + 4800 - a;
    var mm = m + 12 * a - 3;
    return d + Math.floor((153 * mm + 2) / 5) + 365 * yy +
      Math.floor(yy / 4) - Math.floor(yy / 100) + Math.floor(yy / 400) - 32045;
  }

  function jdnToGregorian(jdn) {
    var a = jdn + 32044;
    var b = Math.floor((4 * a + 3) / 146097);
    var c = a - Math.floor(146097 * b / 4);
    var d2 = Math.floor((4 * c + 3) / 1461);
    var e = c - Math.floor(1461 * d2 / 4);
    var m2 = Math.floor((5 * e + 2) / 153);
    return {
      year: 100 * b + d2 - 4800 + Math.floor(m2 / 10),
      month: m2 + 3 - 12 * Math.floor(m2 / 10),
      day: e - Math.floor((153 * m2 + 2) / 5) + 1
    };
  }

  // Dagar före etiopiskt år ey: 365·(ey−1) + floor(ey/4)
  function ethToJdn(ey, em, ed) {
    return ETH_EPOCH + 365 * (ey - 1) + Math.floor(ey / 4) + 30 * (em - 1) + (ed - 1);
  }

  function jdnToEth(jdn) {
    var r = jdn - ETH_EPOCH;
    var ey = Math.floor(r / 365.25) + 1; // estimat, justeras nedan
    while (365 * ey + Math.floor((ey + 1) / 4) <= r) ey++;
    while (365 * (ey - 1) + Math.floor(ey / 4) > r) ey--;
    var doy = r - (365 * (ey - 1) + Math.floor(ey / 4));
    return { year: ey, month: Math.floor(doy / 30) + 1, day: (doy % 30) + 1 };
  }

  // Besökarens civila datum (lokala klockan), UTC-förankrat så att all
  // vidare aritmetik blir tidszonsoberoende. "Idag" ska följa besökarens
  // klocka — UTC-datumet är fel i Sverige timmarna efter midnatt.
  function localCivilDate(d) {
    d = d || new Date();
    return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  }

  // ------------------------------------------------------- publikt API ---
  function toEthiopian(date) {
    return jdnToEth(gregorianToJdn(date.getUTCFullYear(), date.getUTCMonth() + 1, date.getUTCDate()));
  }

  function ethToGregorian(ey, em, ed) {
    var g = jdnToGregorian(ethToJdn(ey, em, ed));
    return new Date(Date.UTC(g.year, g.month - 1, g.day));
  }

  function isEthLeap(ey) { return ey % 4 === 3; }

  function daysInEthMonth(ey, em) {
    if (em < 13) return 30;
    return isEthLeap(ey) ? 6 : 5;
  }

  var ETH_MONTHS = [
    { am: 'መስከረም', sv: 'Meskerem' }, { am: 'ጥቅምት', sv: 'Tikimt' },
    { am: 'ኅዳር', sv: 'Hidar' },      { am: 'ታኅሣሥ', sv: 'Tahsas' },
    { am: 'ጥር', sv: 'Tirr' },         { am: 'የካቲት', sv: 'Yekatit' },
    { am: 'መጋቢት', sv: 'Megabit' },  { am: 'ሚያዝያ', sv: 'Miyazya' },
    { am: 'ግንቦት', sv: 'Ginbot' },    { am: 'ሰኔ', sv: 'Sene' },
    { am: 'ሐምሌ', sv: 'Hamle' },      { am: 'ነሐሴ', sv: 'Nehase' },
    { am: 'ጳጉሜን', sv: 'Pagume' }
  ];

  var WEEKDAYS = [ // index = JS getUTCDay(), 0 = söndag
    { am: 'እሑድ', sv: 'Sön' }, { am: 'ሰኞ', sv: 'Mån' }, { am: 'ማክሰኞ', sv: 'Tis' },
    { am: 'ረቡዕ', sv: 'Ons' }, { am: 'ሐሙስ', sv: 'Tor' }, { am: 'ዓርብ', sv: 'Fre' },
    { am: 'ቅዳሜ', sv: 'Lör' }
  ];

  function formatEthiopianDate(date, lang) {
    var e = toEthiopian(date);
    var name = ETH_MONTHS[e.month - 1][lang === 'am' ? 'am' : 'sv'];
    var era = lang === 'am' ? 'ዓ.ም.' : 'E.C.';
    return name + ' ' + e.day + ', ' + e.year + ' ' + era;
  }

  // ------------------------------------------------------- högtidsdata ---
  // OBS: listan är publik kyrkokalenderdata och ska granskas av församlingen
  // (innehållsgranskning, inte kodgranskning).
  var HOLIDAYS = {
    // Fasta etiopisk-ortodoxa högtider (månad/dag i E.C.)
    ethiopianFixed: [
      { month: 1,  day: 1,  icon: '⛪', name: { sv: 'Enkutatash (nyår)', am: 'እንቁጣጣሽ' } },
      { month: 1,  day: 17, icon: '⛪', name: { sv: 'Meskel (korsets fest)', am: 'መስቀል' } },
      { month: 2,  day: 14, icon: '⛪', name: { sv: 'Abune Aregawi', am: 'አቡነ አረጋዊ' } },
      { month: 3,  day: 8,  icon: '⛪', name: { sv: 'De fyra himmelska väsendena', am: 'አርባዕቱ እንስሳ' } },
      { month: 3,  day: 12, icon: '⛪', name: { sv: 'Hidar Mikael', am: 'ኅዳር ሚካኤል' } },
      { month: 3,  day: 21, icon: '⛪', name: { sv: 'Hidar Tsion (Maryam av Zion)', am: 'ኅዳር ጽዮን' } },
      { month: 3,  day: 24, icon: '⛪', name: { sv: 'Tekle Haymanots avfärd', am: 'አቡነ ተክለ ሃይማኖት' } },
      { month: 4,  day: 3,  icon: '⛪', name: { sv: 'Beata (Marias intåg i templet)', am: 'በዓታ ለማርያም' } },
      { month: 4,  day: 28, icon: '⛪', name: { sv: 'Amanuel', am: 'አማኑኤል' } },
      { month: 4,  day: 29, icon: '⛪', name: { sv: 'Gena (jul)', am: 'ገና (ልደት)' } },
      { month: 5,  day: 11, icon: '⛪', name: { sv: 'Timkat (epifania)', am: 'ጥምቀት' } },
      { month: 5,  day: 12, icon: '⛪', name: { sv: 'Tirr Mikael (Kana i Galileen)', am: 'ቃና ዘገሊላ' } },
      { month: 5,  day: 21, icon: '⛪', name: { sv: 'Asterio Maryam', am: 'አስተርእዮ ማርያም' } },
      { month: 6,  day: 16, icon: '⛪', name: { sv: 'Kidane Mehret (barmhärtighetens förbund)', am: 'ኪዳነ ምሕረት' } },
      { month: 7,  day: 29, icon: '⛪', name: { sv: 'Megabit Bale Wold', am: 'በዓለ ወልድ' } },
      { month: 8,  day: 23, icon: '⛪', name: { sv: 'Miyazya Giyorgis', am: 'ሚያዝያ ጊዮርጊስ' } },
      { month: 9,  day: 1,  icon: '⛪', name: { sv: 'Ledeta Maryam (Marias födelse)', am: 'ልደታ ማርያም' } },
      { month: 10, day: 12, icon: '⛪', name: { sv: 'Sene Mikael', am: 'ሰኔ ሚካኤል' } },
      { month: 10, day: 21, icon: '⛪', name: { sv: 'Sene Maryam', am: 'ሰኔ ማርያም' } },
      { month: 11, day: 5,  icon: '⛪', name: { sv: 'Petrus och Paulus', am: 'ጴጥሮስ ወጳውሎስ' } },
      { month: 11, day: 19, icon: '⛪', name: { sv: 'Hamle Gabriel', am: 'ሐምሌ ገብርኤል' } },
      { month: 12, day: 13, icon: '⛪', name: { sv: 'Buhe (Debre Tabor)', am: 'ቡሄ (ደብረ ታቦር)' } },
      { month: 12, day: 16, icon: '⛪', name: { sv: 'Filseta (Marias upptagande)', am: 'ፍልሰታ' } },
      { month: 13, day: 3,  icon: '⛪', name: { sv: 'Pagume Rufael', am: 'ሩፋኤል' } }
    ],
    // Månatliga helgondagar — återkommer samma dag varje etiopisk månad
    monthlySaints: [
      { day: 1,  name: { sv: 'Ledeta', am: 'ልደታ' } },
      { day: 5,  name: { sv: 'Abo (Gebre Menfes Kidus)', am: 'አቦ' } },
      { day: 7,  name: { sv: 'Selassie (Treenigheten)', am: 'ሥላሴ' } },
      { day: 12, name: { sv: 'Mikael', am: 'ሚካኤል' } },
      { day: 16, name: { sv: 'Kidane Mehret', am: 'ኪዳነ ምሕረት' } },
      { day: 19, name: { sv: 'Gabriel', am: 'ገብርኤል' } },
      { day: 21, name: { sv: 'Maryam', am: 'ማርያም' } },
      { day: 23, name: { sv: 'Giyorgis', am: 'ጊዮርጊስ' } },
      { day: 24, name: { sv: 'Tekle Haymanot', am: 'ተክለ ሃይማኖት' } },
      { day: 27, name: { sv: 'Medhane Alem (Världens frälsare)', am: 'መድኃኔ ዓለም' } },
      { day: 29, name: { sv: 'Bale Wold', am: 'በዓለ ወልድ' } }
    ],
    // Fasta fasteperioder (E.C.) — rörliga fastor (stora fastan m.fl.) ingår ej
    fasting: [
      { from: { month: 3, day: 15 }, to: { month: 4, day: 28 }, name: { sv: 'Adventsfastan (Tsome Nebiyat)', am: 'ጾመ ነቢያት' } },
      { from: { month: 12, day: 1 }, to: { month: 12, day: 16 }, name: { sv: 'Filseta-fastan', am: 'ጾመ ፍልሰታ' } }
    ]
  };

  // ------------------------------------------- svenska röda dagar --------
  // Anonyma gregorianska computus-algoritmen (Meeus/Jones/Butcher).
  function computeEaster(gy) {
    var a = gy % 19, b = Math.floor(gy / 100), c = gy % 100;
    var d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25);
    var g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30;
    var i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7;
    var m = Math.floor((a + 11 * h + 22 * l) / 451);
    var month = Math.floor((h + l - 7 * m + 114) / 31);
    var day = ((h + l - 7 * m + 114) % 31) + 1;
    return new Date(Date.UTC(gy, month - 1, day));
  }

  function iso(d) { return d.toISOString().slice(0, 10); }
  function plusDays(d, n) { return new Date(d.getTime() + n * 86400000); }
  function saturdayInRange(gy, month, fromDay) { // första lördagen fr.o.m. fromDay
    for (var day = fromDay; day <= fromDay + 6; day++) {
      var d = new Date(Date.UTC(gy, month - 1, day));
      if (d.getUTCDay() === 6) return d;
    }
  }

  // Helgdagar enligt lag (1989:253) om allmänna helgdagar (söndagar utöver)
  function swedishRedDays(gy) {
    var easter = computeEaster(gy);
    var list = [
      { date: gy + '-01-01', name: { sv: 'Nyårsdagen', am: 'የአዲስ ዓመት ቀን' } },
      { date: gy + '-01-06', name: { sv: 'Trettondedag jul', am: 'የጥምቀት በዓል (ስዊድን)' } },
      { date: iso(plusDays(easter, -2)), name: { sv: 'Långfredagen', am: 'ስቅለት (ስዊድን)' } },
      { date: iso(easter), name: { sv: 'Påskdagen', am: 'ፋሲካ (ስዊድን)' } },
      { date: iso(plusDays(easter, 1)), name: { sv: 'Annandag påsk', am: 'የፋሲካ ማግስት' } },
      { date: gy + '-05-01', name: { sv: 'Första maj', am: 'የሠራተኞች ቀን' } },
      { date: iso(plusDays(easter, 39)), name: { sv: 'Kristi himmelsfärdsdag', am: 'ዕርገት (ስዊድን)' } },
      { date: iso(plusDays(easter, 49)), name: { sv: 'Pingstdagen', am: 'ጰራቅሊጦስ (ስዊድን)' } },
      { date: gy + '-06-06', name: { sv: 'Nationaldagen', am: 'የስዊድን ብሔራዊ ቀን' } },
      { date: iso(saturdayInRange(gy, 6, 20)), name: { sv: 'Midsommardagen', am: 'የበጋ አጋማሽ በዓል' } },
      { date: iso(saturdayInRange(gy, 10, 31)), name: { sv: 'Alla helgons dag', am: 'የቅዱሳን ሁሉ ቀን' } },
      { date: gy + '-12-25', name: { sv: 'Juldagen', am: 'ገና (ስዊድን)' } },
      { date: gy + '-12-26', name: { sv: 'Annandag jul', am: 'የገና ማግስት' } }
    ];
    return list;
  }

  // ----------------------------------------------------- månadslogik -----
  function holidaysForEthMonth(ey, em) {
    var out = [];
    HOLIDAYS.ethiopianFixed.forEach(function (h) {
      if (h.month === em) out.push({ day: h.day, icon: h.icon, name: h.name, type: 'feast' });
    });
    HOLIDAYS.monthlySaints.forEach(function (s) {
      if (s.day <= daysInEthMonth(ey, em) && !out.some(function (o) { return o.day === s.day; })) {
        out.push({ day: s.day, icon: '✦', name: s.name, type: 'saint' });
      }
    });
    return out.sort(function (a, b) { return a.day - b.day; });
  }

  function isFastingDay(em, ed) {
    return HOLIDAYS.fasting.some(function (f) {
      if (em < f.from.month || em > f.to.month) return false;
      if (em === f.from.month && ed < f.from.day) return false;
      if (em === f.to.month && ed > f.to.day) return false;
      return true;
    });
  }

  var SV_MONTHS = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'];

  function buildMonthGrid(ey, em, today) {
    today = today || localCivilDate();
    var todayIso = iso(today);
    var n = daysInEthMonth(ey, em);
    var monthHolidays = holidaysForEthMonth(ey, em);
    var redByDate = {};
    var first = ethToGregorian(ey, em, 1);
    var last = ethToGregorian(ey, em, n);
    [first.getUTCFullYear(), last.getUTCFullYear()].forEach(function (gy) {
      swedishRedDays(gy).forEach(function (h) { redByDate[h.date] = h; });
    });
    var cells = [];
    for (var day = 1; day <= n; day++) {
      var g = ethToGregorian(ey, em, day);
      var gIso = iso(g);
      var hol = monthHolidays.filter(function (h) { return h.day === day; });
      if (redByDate[gIso]) hol.push({ day: day, icon: '🇸🇪', name: redByDate[gIso].name, type: 'swedish' });
      cells.push({
        eth: { year: ey, month: em, day: day },
        greg: g, gregIso: gIso, weekday: g.getUTCDay(),
        isToday: gIso === todayIso,
        isFast: isFastingDay(em, day),
        holidays: hol
      });
    }
    var headerGreg = SV_MONTHS[first.getUTCMonth()] + ' ' + first.getUTCFullYear();
    if (first.getUTCMonth() !== last.getUTCMonth()) {
      headerGreg += ' – ' + SV_MONTHS[last.getUTCMonth()] + ' ' + last.getUTCFullYear();
    }
    return {
      eth: { year: ey, month: em },
      headerEth: { am: ETH_MONTHS[em - 1].am + ' ' + ey, sv: ETH_MONTHS[em - 1].sv + ' ' + ey },
      headerGreg: headerGreg,
      cells: cells
    };
  }

  // ----------------------------------- världens kalendrar (via Intl/ICU) --
  // Live-tabell: samma ögonblick i tio kalendersystem. Räknas av webbläsarens
  // egen ICU-data (CLDR) — ingen egen aritmetik, ingen lista att underhålla.
  var WORLD_CALENDARS = [
    { ca: 'gregory',          sv: 'Gregorianska (Sverige)',      am: 'ግሪጎሪያን (ስዊድን)' },
    { ca: 'ethiopic',         sv: 'Etiopiska — Amete Mihret',    am: 'የኢትዮጵያ — ዓመተ ምሕረት' },
    { ca: 'ethioaa',          sv: 'Etiopiska — Amete Alem',      am: 'የኢትዮጵያ — ዓመተ ዓለም' },
    { ca: 'coptic',           sv: 'Koptiska (Egypten)',          am: 'ኮፕቲክ (ግብፅ)' },
    { ca: 'islamic-umalqura', sv: 'Islamska (Hijri)',            am: 'የእስልምና (ሂጅራ)' },
    { ca: 'hebrew',           sv: 'Hebreiska',                   am: 'የዕብራይስጥ' },
    { ca: 'persian',          sv: 'Persiska (Iran)',             am: 'የፋርስ (ኢራን)' },
    { ca: 'buddhist',         sv: 'Buddhistiska (Thailand)',     am: 'የቡድሂስት (ታይላንድ)' },
    { ca: 'japanese',         sv: 'Japanska (eror)',             am: 'የጃፓን' },
    { ca: 'chinese',          sv: 'Kinesiska (månkalender)',     am: 'የቻይና (የጨረቃ)' }
  ];

  function worldCalendarsToday(date, lang) {
    var locale = (lang === 'am' ? 'am' : 'sv');
    var out = [];
    WORLD_CALENDARS.forEach(function (c) {
      try {
        var f = new Intl.DateTimeFormat(locale + '-u-ca-' + c.ca,
          { year: 'numeric', month: 'long', day: 'numeric' });
        out.push({ ca: c.ca, label: c[lang === 'am' ? 'am' : 'sv'], formatted: f.format(date) });
      } catch (e) { /* kalendern saknas i denna miljö — hoppa över raden */ }
    });
    return out;
  }

  function renderWorldCalendars() {
    var el = document.getElementById('world-calendars');
    if (!el) return;
    var lang = currentLang();
    var today = api.localCivilDate ? api.localCivilDate() : new Date();
    var rows = worldCalendarsToday(today, lang);
    if (rows.length < 3) { el.style.display = 'none'; return; }
    var html = '<table class="ethcal-worldtable"><tbody>';
    rows.forEach(function (r) {
      var mark = (r.ca === 'ethiopic' || r.ca === 'ethioaa') ? ' style="font-weight:600"' : '';
      html += '<tr' + mark + '><td>' + r.label + '</td><td>' + r.formatted + '</td></tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
  }

  // -------------------------------------------------- webbläsar-UI -------
  function currentLang() {
    try { return (document.documentElement.lang || 'sv').indexOf('am') === 0 ? 'am' : 'sv'; }
    catch (e) { return 'sv'; }
  }

  function renderCalendar(root, state) {
    var lang = currentLang();
    var grid = buildMonthGrid(state.year, state.month);
    var html = '<div class="ethcal-head">' +
      '<button type="button" class="ethcal-nav" data-nav="-1" aria-label="Föregående månad">◀</button>' +
      '<div class="ethcal-titles"><div class="ethcal-title">' +
      (lang === 'am' ? grid.headerEth.am : grid.headerEth.sv + ' <span class="ethcal-am">' + grid.headerEth.am + '</span>') +
      '</div><div class="ethcal-sub">' + grid.headerGreg + '</div></div>' +
      '<button type="button" class="ethcal-nav" data-nav="1" aria-label="Nästa månad">▶</button>' +
      '<button type="button" class="ethcal-nav ethcal-todaybtn" data-today="1">' + (lang === 'am' ? 'ዛሬ' : 'Idag') + '</button></div>';
    html += '<div class="ethcal-grid" role="grid">';
    WEEKDAYS.forEach(function (w) {
      html += '<div class="ethcal-wd" role="columnheader">' + w.am + '<br>' + w.sv + '</div>';
    });
    for (var pad = 0; pad < grid.cells[0].weekday; pad++) html += '<div class="ethcal-cell ethcal-empty"></div>';
    grid.cells.forEach(function (c) {
      var cls = 'ethcal-cell' + (c.isToday ? ' ethcal-today' : '') + (c.isFast ? ' ethcal-fast' : '') +
        (c.holidays.length ? ' ethcal-holiday' : '');
      var tip = c.holidays.map(function (h) { return h.name[lang] || h.name.sv; }).join(' · ');
      var marks = c.holidays.map(function (h) { return h.icon; }).join('');
      html += '<div class="' + cls + '" role="gridcell" tabindex="0"' +
        (tip ? ' title="' + tip.replace(/"/g, '&quot;') + '" aria-label="' + c.eth.day + ' ' + tip.replace(/"/g, '&quot;') + '"' : '') + '>' +
        '<span class="ethcal-day">' + c.eth.day + '</span>' +
        '<span class="ethcal-gday">' + c.greg.getUTCDate() + '/' + (c.greg.getUTCMonth() + 1) + '</span>' +
        (marks ? '<span class="ethcal-marks">' + marks + '</span>' : '') + '</div>';
    });
    html += '</div>';
    var legend = lang === 'am'
      ? '⛪ በዓላት · ✦ ወርኃዊ መታሰቢያ · 🇸🇪 የስዊድን በዓል · ◆ ጾም'
      : '⛪ Stor högtid · ✦ Månatlig helgondag · 🇸🇪 Svensk röd dag · ◆ Fasteperiod';
    html += '<p class="muted ethcal-legend">' + legend + '</p>';
    root.innerHTML = html;
    var navs = root.querySelectorAll('.ethcal-nav');
    for (var i = 0; i < navs.length; i++) {
      navs[i].addEventListener('click', function (ev) {
        if (ev.currentTarget.getAttribute('data-today')) {
          var t = toEthiopian(localCivilDate());
          state.year = t.year; state.month = t.month;
        } else {
          var dir = parseInt(ev.currentTarget.getAttribute('data-nav'), 10);
          var m = state.month + dir, y = state.year;
          if (m < 1) { m = 13; y--; }
          if (m > 13) { m = 1; y++; }
          state.month = m; state.year = y;
        }
        renderCalendar(root, state);
      });
    }
  }

  function initCalendarPage() {
    renderWorldCalendars();
    var root = document.getElementById('eth-calendar');
    if (!root) return;
    var e = toEthiopian(localCivilDate());
    renderCalendar(root, { year: e.year, month: e.month });
  }

  function initEthDate() {
    var el = document.getElementById('eth-date');
    if (!el) return;
    var lang = currentLang();
    var now = localCivilDate();
    el.textContent = formatEthiopianDate(now, 'am') + (lang === 'am' ? '' : ' · ' + formatEthiopianDate(now, 'sv'));
  }

  var api = {
    localCivilDate: localCivilDate,
    worldCalendarsToday: worldCalendarsToday,
    toEthiopian: toEthiopian,
    ethToGregorian: ethToGregorian,
    isEthLeap: isEthLeap,
    daysInEthMonth: daysInEthMonth,
    formatEthiopianDate: formatEthiopianDate,
    computeEaster: computeEaster,
    swedishRedDays: swedishRedDays,
    holidaysForEthMonth: holidaysForEthMonth,
    isFastingDay: isFastingDay,
    buildMonthGrid: buildMonthGrid,
    renderCalendar: renderCalendar,
    initCalendarPage: initCalendarPage,
    initEthDate: initEthDate,
    HOLIDAYS: HOLIDAYS,
    ETH_MONTHS: ETH_MONTHS,
    WEEKDAYS: WEEKDAYS
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.KyrkCalendar = api;

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { initEthDate(); initCalendarPage(); });
    } else { initEthDate(); initCalendarPage(); }
  }
})(typeof window !== 'undefined' ? window : globalThis);
