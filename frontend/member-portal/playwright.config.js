// E2E tests run against a local build of the site (dist/), never against
// production: a PR must be judged on its own changes, and prod drift must
// not fail unrelated PRs. The webServer block below builds the site from
// the repo root and serves dist/ with Cloudflare-Pages-like URL semantics
// (tests/serve-dist.js).
//
// Override with BASE_URL to point the suite somewhere else manually, e.g.
//   BASE_URL=https://kyrka-portal.pages.dev npx playwright test
const LOCAL_URL = 'http://127.0.0.1:4173';

const path = require('path');

module.exports = {
  testDir: './tests',
  testMatch: 'e2e.spec.js',
  timeout: 30000,
  // Explicit paths: this package has no own package.json, so Playwright
  // would otherwise resolve output dirs against the repo root. These must
  // match the artifact paths in .github/workflows/frontend-e2e.yml.
  outputDir: path.join(__dirname, 'test-results'),
  use: {
    baseURL: process.env.BASE_URL || LOCAL_URL,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    // The site registers a service worker; requests that pass through it
    // bypass page.route(), which would let the intake test reach the real
    // membership API. Blocking SWs keeps API stubbing reliable.
    serviceWorkers: 'block',
  },
  webServer: {
    command: 'cd ../.. && npx @11ty/eleventy --quiet && node frontend/member-portal/tests/serve-dist.js',
    url: LOCAL_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
  projects: [
    { name: 'Mobile', use: { viewport: { width: 375, height: 812 } } },
    { name: 'Desktop', use: { viewport: { width: 1440, height: 900 } } },
  ],
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: path.join(__dirname, 'playwright-report') }],
  ],
};
