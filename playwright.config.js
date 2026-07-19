// Playwright config for the draft editor (docsync/editor/edit.html), the
// single-file app assessed in docs/primer/LIBRARIES.md — recommendation #1
// there was to formalize the ad-hoc /tmp Playwright harness into the repo.
// Dev-only: nothing here ships to users.
const { defineConfig, devices } = require('@playwright/test');

const PORT = process.env.PRIMER_TEST_PORT || 8199;

module.exports = defineConfig({
  testDir: 'tests/editor',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // Pyodide (~30MB, cdn.jsdelivr.net) boots once per test — generous timeouts.
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [['github'], ['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://localhost:${PORT}/primer/`,
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'python3 report2027/tools/serve.py',
    url: `http://localhost:${PORT}/__ping`,
    reuseExistingServer: false,
    timeout: 30_000,
    // PRIMER_OPEN=0: serve.py's default behavior opens a real browser tab on
    // startup (nice for `make live`, pointless — and awkward on a CI runner
    // with no display — when Playwright is about to drive its own browser).
    env: { PRIMER_PORT: String(PORT), PRIMER_OPEN: '0' },
  },
});
