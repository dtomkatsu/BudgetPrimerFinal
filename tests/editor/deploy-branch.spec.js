// Per-project deploy branch (docsync/editor/edit.html BRANCH). A project's
// manifest names the branch its drafts fork from and publish to; it defaults
// to main (covered by drafts.spec.js), but a repo may deploy from production,
// gh-pages, or any name. Here the manifest is rewritten on the wire to declare
// branch:"production", and the fake GitHub is seeded with that branch — so a
// real Save-then-Publish must fork from and merge into production, never main.
const { hostedTest: test, expect, gotoEditor, fillDialog, submitDialog,
        submitDialogIfPresent } = require('./fixtures/editor-test');

async function addASection(page) {
  await page.click('#add');
  await fillDialog(page, { page: 'basics', slug: 'branch-section' });
  await submitDialog(page);
  await page.frameLocator('#out').locator('.ds-edit').waitFor({ state: 'visible' });
  await page.keyboard.press('Escape');
}

test.describe('per-project deploy branch', () => {
  test.beforeEach(async ({ context, github }) => {
    // The project deploys from production, not main. Seed it at main's tip so
    // there is something to fork from, then flip the served manifest's branch.
    github.refs.set('production', github.refs.get('main'));
    await context.route('**/engine/manifest.json*', async route => {
      const res = await route.fetch();
      const m = await res.json();
      m.branch = 'production';
      await route.fulfill({ json: m });
    });
  });

  test('a draft forks from the deploy branch and Publish merges back into it', async ({ page, github }) => {
    await gotoEditor(page);
    await page.waitForTimeout(300);

    await addASection(page);
    await page.click('#save');
    await submitDialogIfPresent(page);        // print-fit-cut confirm, if any
    await expect(page.locator('#stat')).toContainText('draft saved', { timeout: 15000 });

    // The draft exists — ensureBranch found production to fork from. Had it
    // still forked from a hardcoded main, this project (which never touches
    // main) would be deploying from the wrong place.
    expect(github.refs.has('draft/budget-primer/test-user')).toBe(true);

    await page.click('#publish');
    await submitDialog(page);                 // "Make this draft the live report?"
    await expect(page.locator('#stat')).toContainText('published', { timeout: 15000 });

    // The PR targeted production, and the edit landed there — not on main.
    const pr = github.pulls.find(p => p.head === 'draft/budget-primer/test-user');
    expect(pr).toBeTruthy();
    expect(pr.base).toBe('production');
    expect(github.contents.get('production:report2027/content.md'))
      .toContain('extra.basics.branch-section');
    expect(github.contents.get('main:report2027/content.md') || '')
      .not.toContain('extra.basics.branch-section');
  });
});
