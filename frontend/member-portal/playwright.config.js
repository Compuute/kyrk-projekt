module.exports = {
  testDir: './tests',
  testMatch: 'e2e.spec.js',
  timeout: 30000,
  use: {
    baseURL: process.env.BASE_URL || 'https://kyrka-portal.pages.dev',
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'Mobile', use: { viewport: { width: 375, height: 812 } } },
    { name: 'Desktop', use: { viewport: { width: 1440, height: 900 } } },
  ],
  reporter: [['list'], ['html', { open: 'never' }]],
};
