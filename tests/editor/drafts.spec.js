// Drafts: Save draft / Share / Publish (docsync/editor/edit.html). Hosted
// mode — /__ping is blocked so local=false and every persistence call goes
// through gh() against the in-memory FakeGitHub (tests/editor/fixtures/
// fake-github.js), never the real GitHub API.
const { hostedTest: test, expect, gotoEditor } = require('./fixtures/editor-test');

// Every dialog in this flow is either a confirm() this test wants to accept
// (the print-fit-cut warning on Save, "publish this draft?", "throw away this
// draft?") or a prompt() with a queued answer (the +Section flow's page
// number / slug). One router avoids ordering/leftover-listener bugs from
// juggling several page.once()/page.on() registrations across a test.
function routeDialogs(page, promptAnswers = []) {
  const queue = [...promptAnswers];
  page.on('dialog', async dialog => {
    if (dialog.type() === 'prompt') {
      const next = queue.shift();
      if (next === undefined) throw new Error(`unexpected prompt: ${dialog.message()}`);
      return dialog.accept(next);
    }
    return dialog.accept();   // confirm()s in this flow are all "yes, proceed"
  });
}

async function addASection(page) {
  routeDialogs(page, ['1', 'draft-section']);
  await page.click('#add');
  await page.frameLocator('#out').locator('.ds-edit').waitFor({ state: 'visible' });
  await page.keyboard.press('Escape');
}

test.describe('drafts: save / share / publish', () => {
  test.beforeEach(async ({ page }) => {
    await gotoEditor(page);
    // Hosted mode never local-pings, so no live-reload race — still, give
    // boot()'s resolveDraft()/gh() lookups (against the fake) a moment.
    await page.waitForTimeout(300);
  });

  test('an edit enables Save draft, Share and Publish (hidden only in local mode)', async ({ page }) => {
    await expect(page.locator('#share')).toBeVisible();   // hidden only when local
    await expect(page.locator('#save')).toHaveText('Save draft');
    await addASection(page);
    await expect(page.locator('#save')).toBeEnabled();
  });

  test('Save draft commits content+layout to draft/<project>/<user> via the Git Data API', async ({ page, github }) => {
    await addASection(page);
    await page.click('#save');
    await expect(page.locator('#stat')).toContainText('draft saved', { timeout: 15000 });

    expect(github.refs.has('draft/budget-primer/test-user')).toBe(true);
    const committed = github.contents.get('draft/budget-primer/test-user:report2027/content.md');
    expect(committed).toContain('extra.basics.draft-section');

    await expect(page.locator('#share')).toBeEnabled();
    await expect(page.locator('#publish')).toBeEnabled();
    await expect(page.locator('#title')).toContainText('draft: test-user');
  });

  test('Publish merges the draft branch into main and returns to the live view', async ({ page, github }) => {
    await addASection(page);
    await page.click('#save');
    await expect(page.locator('#stat')).toContainText('draft saved', { timeout: 15000 });

    await page.click('#publish');   // routeDialogs() already accepts its confirm()
    await expect(page.locator('#stat')).toContainText('published', { timeout: 15000 });

    expect(github.pulls.some(p => p.head === 'draft/budget-primer/test-user' && !p.open)).toBe(true);
    const mainContent = github.contents.get('main:report2027/content.md');
    expect(mainContent).toContain('extra.basics.draft-section');

    await expect(page.locator('#title')).not.toContainText('draft:');
    // $('publish').onclick unconditionally re-enables the button in its final
    // line, success or failure — clicking it again with nothing to publish is
    // a harmless no-op ("nothing to publish yet"), so this isn't a guard to
    // assert on here.
  });

  test('Discard on a saved draft deletes the branch and returns to the live report', async ({ page, github }) => {
    await addASection(page);
    await page.click('#save');
    await expect(page.locator('#stat')).toContainText('draft saved', { timeout: 15000 });
    expect(github.refs.has('draft/budget-primer/test-user')).toBe(true);

    const navigated = page.waitForURL(url => !url.searchParams.has('draft'));
    await page.click('#revert');   // routeDialogs() already accepts its confirm()
    await navigated;

    expect(github.refs.has('draft/budget-primer/test-user')).toBe(false);
  });
});
