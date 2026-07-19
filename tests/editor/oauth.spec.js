// GitHub OAuth device-flow sign-in (docsync/editor/edit.html): signIn() polls
// a relay (M.oauth.relay) for /device/code then /device/token — see
// OAUTH_SETUP.md. This repo's manifest ships with no "oauth" block today (the
// paste-a-token fallback is what's actually configured), so this test injects
// one into the manifest response and fakes the relay, to exercise the code
// path that OAUTH_SETUP.md would activate.
const { hostedTest: test, expect, gotoEditor } = require('./fixtures/editor-test');

const RELAY = 'https://fake-relay.test';

async function withOauthManifest(context) {
  // get()'s cache-buster appends ?cb=<timestamp> to every fetch, this one
  // included — the glob must match that suffix too, not just the bare path.
  await context.route('**/engine/manifest.json*', async route => {
    const res = await route.fetch();
    const m = await res.json();
    m.oauth = { client_id: 'test-client-id', relay: RELAY };
    await route.fulfill({ response: res, json: m });
  });
}

test.describe('oauth device-flow sign-in', () => {
  test.beforeEach(async ({ context }) => {
    await withOauthManifest(context);
    // /device/code: hand back a fake user code and a fast poll interval.
    await context.route(`${RELAY}/device/code`, route => route.fulfill({
      json: {
        device_code: 'fake-device-code', user_code: 'ABCD-1234',
        verification_uri: 'https://github.com/login/device',
        expires_in: 900, interval: 1,
      },
    }));
  });

  test('polling the relay completes sign-in and stores a token', async ({ page, context }) => {
    await context.route(`${RELAY}/device/token`, route => route.fulfill({
      json: { access_token: 'fake-oauth-token', token_type: 'bearer', expires_in: 28800 },
    }));

    await gotoEditor(page);
    // hostedTest seeds a PAT so the app never prompts on its own; Token…
    // explicitly clears it first, which is what actually triggers ensureAuth().
    await page.click('#tok');

    const panel = page.locator('#authpanel');
    await expect(panel).toBeVisible();
    await expect(panel.locator('.au-code')).toHaveText('ABCD-1234');

    await expect(panel).toBeHidden({ timeout: 10_000 });
    const stored = await page.evaluate(() => localStorage.getItem('docsync-pat'));
    expect(stored).toBe('fake-oauth-token');
  });

  test('an authorization_pending poll is retried, not treated as failure', async ({ page, context }) => {
    let calls = 0;
    await context.route(`${RELAY}/device/token`, route => {
      calls++;
      if (calls === 1) return route.fulfill({ json: { error: 'authorization_pending' } });
      return route.fulfill({ json: { access_token: 'fake-oauth-token-2', token_type: 'bearer' } });
    });

    await gotoEditor(page);
    await page.click('#tok');
    await expect(page.locator('#authpanel')).toBeHidden({ timeout: 10_000 });

    expect(calls).toBeGreaterThanOrEqual(2);
    const stored = await page.evaluate(() => localStorage.getItem('docsync-pat'));
    expect(stored).toBe('fake-oauth-token-2');
  });

  test('a declined sign-in clears the panel without storing a token', async ({ page, context }) => {
    await context.route(`${RELAY}/device/token`, route => route.fulfill({
      json: { error: 'access_denied' },
    }));

    await gotoEditor(page);
    await page.click('#tok');
    await expect(page.locator('#authpanel .au-msg')).toContainText('declined', { timeout: 10_000 });
    await expect(page.locator('#authpanel')).toBeHidden({ timeout: 5_000 });

    const stored = await page.evaluate(() => localStorage.getItem('docsync-pat'));
    expect(stored).toBeNull();
  });
});
