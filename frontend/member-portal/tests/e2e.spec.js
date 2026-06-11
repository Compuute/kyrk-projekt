// E2E visual tests — runs in CI with a real browser (Playwright).
//
// Catches bugs that HTML-parsing tests miss:
// - Invisible elements (wrong CSS, opacity:0, display:none)
// - Overlapping elements
// - Forms that can't be submitted
// - Buttons that can't be clicked
// - Broken JavaScript interactions
//
// Runs against a locally built dist/ (see playwright.config.js webServer),
// never against production. The Cloudflare Pages Functions middleware
// (language-prefix redirects, KV config injection) is NOT exercised here —
// these tests cover the static site + client-side JS only.
//
// Run: npx playwright test tests/e2e.spec.js
// CI:  GitHub Actions builds the site and runs this suite

const { test, expect } = require('@playwright/test');

const PAGES = [
  { path: '/', name: 'Startsida' },
  { path: '/intake', name: 'Bli medlem' },
  { path: '/donate', name: 'Donation' },
  { path: '/live', name: 'Livestream' },
  { path: '/funeral', name: 'Begravning' },
  { path: '/about', name: 'Om oss' },
  { path: '/contact', name: 'Kontakt' },
  { path: '/privacy', name: 'Integritetspolicy' },
];

// The intake form POSTs to the membership API on Cloud Run. Tests must
// never write to the real backend, so the API is stubbed per test.
const INTAKE_API = /membership-intake-[^/]*\.run\.app\/intake/;

function stubIntakeApi(page, status = 202) {
  return page.route(INTAKE_API, (route) =>
    route.fulfill({
      status,
      contentType: 'application/json',
      headers: { 'access-control-allow-origin': '*' },
      body: '{}',
    })
  );
}

// ============================================================
// 1. Every page loads without errors
// ============================================================

for (const page of PAGES) {
  test(`${page.name} (${page.path}) loads without JS errors`, async ({ page: p }) => {
    const errors = [];
    p.on('pageerror', (err) => errors.push(err.message));

    await p.goto(page.path);
    await p.waitForLoadState('networkidle');

    expect(errors).toEqual([]);
  });
}

// ============================================================
// 2. Language switcher works
// ============================================================

test('language switcher toggles to Amharic', async ({ page }) => {
  await page.goto('/');
  // Wait for the church content to render before switching language
  await expect(page.locator('#church-name')).not.toBeEmpty();

  const amButton = page.locator('.lang-pill[data-lang="am"]');
  await expect(amButton).toBeVisible();
  await amButton.click();

  // Church name should now be in Amharic
  await expect(page.locator('h1#church-name')).toContainText('ኢትዮጵያ');
});

test('language switcher toggles back to Swedish', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#church-name')).not.toBeEmpty();

  await page.locator('.lang-pill[data-lang="am"]').click();
  await expect(page.locator('h1#church-name')).toContainText('ኢትዮጵያ');

  await page.locator('.lang-pill[data-lang="sv"]').click();
  await expect(page.locator('h1#church-name')).toContainText('Abune Tekle Haymanot');
});

// ============================================================
// 3. GDPR consent is VISIBLE and CLICKABLE
//    (the consent control is a button + hidden input, not a checkbox:
//     #consent-btn toggles #field-gdpr-consent between "" and "true")
// ============================================================

test('intake: GDPR consent button is visible', async ({ page }) => {
  await page.goto('/intake');
  await page.waitForLoadState('networkidle');

  await expect(page.locator('.gdpr-box')).toBeVisible();
  await expect(page.locator('#consent-btn')).toBeVisible();
  await expect(page.locator('#consent-box')).toBeVisible();
});

test('intake: GDPR consent can be toggled', async ({ page }) => {
  await page.goto('/intake');

  const consentBtn = page.locator('#consent-btn');
  await consentBtn.click();

  await expect(page.locator('#field-gdpr-consent')).toHaveValue('true');
  await expect(page.locator('#consent-box')).toHaveText('✓');

  // Toggles back off
  await consentBtn.click();
  await expect(page.locator('#field-gdpr-consent')).toHaveValue('');
});

test('intake: submit without consent shows error', async ({ page }) => {
  await page.goto('/intake');

  await page.fill('#field-first-name', 'Test');
  await page.fill('#field-last-name', 'Person');
  await page.fill('#field-phone', '0701234567');

  await page.locator('[type="submit"]').click();

  const errorMsg = page.locator('#error-msg');
  await expect(errorMsg).toBeVisible();
  await expect(errorMsg).toContainText('samtycke');
});

// ============================================================
// 4. Intake form submission works (API stubbed — never hits prod)
// ============================================================

test('intake: form submits with valid data', async ({ page }) => {
  await stubIntakeApi(page);
  await page.goto('/intake');

  await page.fill('#field-first-name', 'Test');
  await page.fill('#field-last-name', 'Testsson');
  await page.fill('#field-phone', '0701234567');
  await page.fill('#field-email', 'test@test.se');

  await page.locator('#consent-btn').click();
  await page.locator('[type="submit"]').click();

  // Should show success message
  await expect(page.locator('#success-msg')).toBeVisible({ timeout: 5000 });
});

// ============================================================
// 5. Donation page — amount buttons work
// ============================================================

test('donate: amount buttons update Swish text', async ({ page }) => {
  await page.goto('/donate');
  await page.waitForLoadState('networkidle');

  const btn500 = page.locator('.amount-btn').filter({ hasText: '500' });
  await btn500.click();

  const swishBtn = page.locator('#swish-btn');
  await expect(swishBtn).toContainText('500');
});

// ============================================================
// 6. Navigation — back links work
// ============================================================

for (const pg of PAGES.filter((p) => p.path !== '/')) {
  test(`${pg.name}: back link navigates to home`, async ({ page }) => {
    await page.goto(pg.path);

    const backLink = page.locator('a[href="./"], a[href="./index.html"]').first();
    await expect(backLink).toBeVisible();
    await backLink.click();

    await page.waitForURL((url) => url.pathname === '/');
  });
}

// ============================================================
// 7. All quick links on index are visible and clickable
// ============================================================

test('index: all 7+ quick link tiles are visible', async ({ page }) => {
  await page.goto('/');
  const tiles = page.locator('#quick-links .tile, #quick-links a');
  await expect(tiles.first()).toBeVisible();

  const count = await tiles.count();
  expect(count).toBeGreaterThanOrEqual(7);

  for (let i = 0; i < count; i++) {
    await expect(tiles.nth(i)).toBeVisible();
    const text = await tiles.nth(i).textContent();
    expect(text.trim().length).toBeGreaterThan(0);
  }
});

// ============================================================
// 8. Funeral page — all 6 prices visible
// ============================================================

test('funeral: all 6 package prices visible', async ({ page }) => {
  await page.goto('/funeral');

  for (const price of ['19 000', '28 000', '35 000', '70 000', '85 000', '100 000']) {
    const el = page.locator(`text=${price}`).first();
    await expect(el).toBeVisible();
  }
});

// ============================================================
// 9. Contact — phone link clickable when the church has a phone number
//    (the default church, nacka, has no phone in churches.json — the
//     footer tel: link only renders for churches that have one)
// ============================================================

test('contact: phone link is clickable for a church with a phone', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('selectedChurch', 'stockholm');
  });
  await page.goto('/contact');

  const footerPhone = page.locator('#footer-phone');
  await expect(footerPhone).toHaveAttribute('href', /^tel:\+?\d+$/);
  await expect(footerPhone).toBeVisible();

  // Any other tel: links on the page must be visible too
  const telLinks = page.locator('a[href^="tel:"]');
  const count = await telLinks.count();
  expect(count).toBeGreaterThanOrEqual(1);
  for (let i = 0; i < count; i++) {
    await expect(telLinks.nth(i)).toBeVisible();
  }
});

// ============================================================
// 10. Mobile viewport — no horizontal scroll
// ============================================================

test('mobile: no horizontal scroll on any page', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 }); // iPhone SE

  for (const pg of PAGES) {
    await page.goto(pg.path);
    await page.waitForLoadState('networkidle');

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);

    expect(scrollWidth, `${pg.path} overflows horizontally`).toBeLessThanOrEqual(clientWidth + 1);
  }
});

// ============================================================
// 11. Text readability — no invisible text
// ============================================================

test('privacy: text is readable (not invisible)', async ({ page }) => {
  await page.goto('/privacy');

  const paragraphs = page.locator('.policy p');
  const count = await paragraphs.count();
  expect(count).toBeGreaterThan(0);

  for (let i = 0; i < Math.min(count, 5); i++) {
    await expect(paragraphs.nth(i)).toBeVisible();
    const color = await paragraphs.nth(i).evaluate((el) => {
      return window.getComputedStyle(el).color;
    });
    // Should not be near-white on white (#ccc on #fff = bad)
    expect(color).not.toBe('rgb(204, 204, 204)');
  }
});
