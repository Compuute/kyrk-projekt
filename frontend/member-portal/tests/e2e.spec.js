// E2E visual tests — runs in CI with a real browser (Playwright).
//
// Catches bugs that HTML-parsing tests miss:
// - Invisible elements (wrong CSS, opacity:0, display:none)
// - Overlapping elements
// - Forms that can't be submitted
// - Buttons that can't be clicked
// - Broken JavaScript interactions
//
// Run: npx playwright test tests/e2e.spec.js
// CI:  GitHub Actions installs browsers automatically

const { test, expect } = require('@playwright/test');

const BASE = process.env.BASE_URL || 'https://kyrka-portal.pages.dev';

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

// ============================================================
// 1. Every page loads without errors
// ============================================================

for (const page of PAGES) {
  test(`${page.name} (${page.path}) loads without JS errors`, async ({ page: p }) => {
    const errors = [];
    p.on('pageerror', err => errors.push(err.message));

    await p.goto(`${BASE}${page.path}`);
    await p.waitForLoadState('networkidle');

    expect(errors).toEqual([]);
  });
}

// ============================================================
// 2. Language switcher works
// ============================================================

test('language switcher toggles to Amharic', async ({ page }) => {
  await page.goto(`${BASE}/`);
  await page.waitForLoadState('networkidle');

  const amButton = page.locator('[data-lang="am"]');
  await expect(amButton).toBeVisible();
  await amButton.click();

  // Church name should now be in Amharic
  const heading = page.locator('h1');
  const text = await heading.textContent();
  expect(text).toContain('ኢትዮጵያ');
});

test('language switcher toggles back to Swedish', async ({ page }) => {
  await page.goto(`${BASE}/`);
  await page.locator('[data-lang="am"]').click();
  await page.locator('[data-lang="sv"]').click();

  const heading = page.locator('h1');
  const text = await heading.textContent();
  expect(text).toContain('Abune Tekle Haymanot');
});

// ============================================================
// 3. GDPR consent checkbox is VISIBLE and CLICKABLE
// ============================================================

test('intake: GDPR consent checkbox is visible', async ({ page }) => {
  await page.goto(`${BASE}/intake`);
  await page.waitForLoadState('networkidle');

  const consentRow = page.locator('.consent-row');
  await expect(consentRow).toBeVisible();

  const box = consentRow.locator('.consent-check, input[type="checkbox"]');
  await expect(box.first()).toBeVisible();
});

test('intake: GDPR consent checkbox can be clicked', async ({ page }) => {
  await page.goto(`${BASE}/intake`);

  const consentRow = page.locator('.consent-row');
  await consentRow.click();

  const checkbox = page.locator('#field-gdpr-consent');
  await expect(checkbox).toBeChecked();
});

test('intake: submit without consent shows error', async ({ page }) => {
  await page.goto(`${BASE}/intake`);

  await page.fill('#field-first-name', 'Test');
  await page.fill('#field-last-name', 'Person');
  await page.fill('#field-phone', '0701234567');

  await page.locator('[type="submit"]').click();

  const errorMsg = page.locator('#error-msg, .error-msg');
  const text = await errorMsg.textContent();
  expect(text.length).toBeGreaterThan(0);
});

// ============================================================
// 4. Intake form submission works
// ============================================================

test('intake: form submits with valid data', async ({ page }) => {
  await page.goto(`${BASE}/intake`);

  await page.fill('#field-first-name', 'Test');
  await page.fill('#field-last-name', 'Testsson');
  await page.fill('#field-phone', '0701234567');
  await page.fill('#field-email', 'test@test.se');

  // Click consent
  await page.locator('.consent-row').click();

  // Submit
  await page.locator('[type="submit"]').click();

  // Should show success message
  const success = page.locator('#success-msg');
  await expect(success).toBeVisible({ timeout: 5000 });
});

// ============================================================
// 5. Donation page — amount buttons work
// ============================================================

test('donate: amount buttons update Swish text', async ({ page }) => {
  await page.goto(`${BASE}/donate`);

  const btn500 = page.locator('button, .amount-btn').filter({ hasText: '500' });
  await btn500.click();

  const swishBtn = page.locator('.swish-btn, [class*="swish"]').first();
  const text = await swishBtn.textContent();
  expect(text).toContain('500');
});

// ============================================================
// 6. Navigation — back links work
// ============================================================

for (const pg of PAGES.filter(p => p.path !== '/')) {
  test(`${pg.name}: back link navigates to home`, async ({ page }) => {
    await page.goto(`${BASE}${pg.path}`);

    const backLink = page.locator('a[href="./"], a[href="./index.html"]').first();
    await expect(backLink).toBeVisible();
    await backLink.click();

    await page.waitForURL(`${BASE}/`);
  });
}

// ============================================================
// 7. All quick links on index are visible and clickable
// ============================================================

test('index: all 7+ quick link tiles are visible', async ({ page }) => {
  await page.goto(`${BASE}/`);
  await page.waitForLoadState('networkidle');

  const tiles = page.locator('#quick-links .tile, #quick-links a');
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
  await page.goto(`${BASE}/funeral`);

  for (const price of ['19 000', '28 000', '35 000', '70 000', '85 000', '100 000']) {
    const el = page.locator(`text=${price}`).first();
    await expect(el).toBeVisible();
  }
});

// ============================================================
// 9. Contact — phone links clickable
// ============================================================

test('contact: phone links are clickable', async ({ page }) => {
  await page.goto(`${BASE}/contact`);

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
    await page.goto(`${BASE}${pg.path}`);
    await page.waitForLoadState('networkidle');

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);

    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
  }
});

// ============================================================
// 11. Text readability — no invisible text
// ============================================================

test('privacy: text is readable (not invisible)', async ({ page }) => {
  await page.goto(`${BASE}/privacy`);

  const paragraphs = page.locator('.policy p');
  const count = await paragraphs.count();
  expect(count).toBeGreaterThan(0);

  for (let i = 0; i < Math.min(count, 5); i++) {
    await expect(paragraphs.nth(i)).toBeVisible();
    const color = await paragraphs.nth(i).evaluate(el => {
      return window.getComputedStyle(el).color;
    });
    // Should not be near-white on white (#ccc on #fff = bad)
    expect(color).not.toBe('rgb(204, 204, 204)');
  }
});
