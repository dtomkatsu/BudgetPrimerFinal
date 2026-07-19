// Drafts: Save draft / Share / Publish (docsync/editor/edit.html). Hosted
// mode — /__ping is blocked so local=false and every persistence call goes
// through gh() against the in-memory FakeGitHub (tests/editor/fixtures/
// fake-github.js), never the real GitHub API.
const { hostedTest: test, expect, gotoEditor, fillDialog, submitDialog, submitDialogIfPresent } = require('./fixtures/editor-test');

// Every modal here is a native <dialog>: the +Section form, the print-fit-cut
// confirm on Save, and the publish/discard confirms. submitDialog clicks OK on
// whichever one is currently open.
async function addASection(page) {
  await page.click('#add');
  await fillDialog(page, { page: 'basics', slug: 'draft-section' });
  await submitDialog(page);
  await page.frameLocator('#out').locator('.ds-edit').waitFor({ state: 'visible' });
  await page.keyboard.press('Escape');
}

/** Save, accepting the print-fit-cut confirm if the added section raises one. */
async function saveAcceptingFit(page) {
  await page.click('#save');
  await submitDialogIfPresent(page);   // "N pages will be cut off — Save anyway?"
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
    await saveAcceptingFit(page);
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
    await saveAcceptingFit(page);
    await expect(page.locator('#stat')).toContainText('draft saved', { timeout: 15000 });

    await page.click('#publish');
    await submitDialog(page);   // "Make this draft the live report?"
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
    await saveAcceptingFit(page);
    await expect(page.locator('#stat')).toContainText('draft saved', { timeout: 15000 });
    expect(github.refs.has('draft/budget-primer/test-user')).toBe(true);

    await page.click('#revert');
    await submitDialog(page);   // "Throw away this saved draft?"
    await page.waitForURL(url => !url.searchParams.has('draft'));

    expect(github.refs.has('draft/budget-primer/test-user')).toBe(false);
  });
});
