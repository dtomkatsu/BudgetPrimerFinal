# docsync setup

The sync engine runs in GitHub Actions, so it needs Google credentials that
don't depend on anyone's browser session. That means a **service account**: a
robot Google identity whose key lives in a GitHub secret. This is the one part
nobody can automate away — it needs a human with access to the Google account.

Everything else is already in the repo: `docsync.yml` (the bindings),
`.github/workflows/docsync.yml` (the engine), and `docsync/` (the code).

## One-time, ~15 minutes

`docsync/setup.sh` does steps 1–4 for you if you have `gcloud` and `gh`
installed and are logged into both. Otherwise, by hand:

**1. Create a project and service account** — <https://console.cloud.google.com>

Any project works; a dedicated one keeps quotas clean. Create a service
account (e.g. `docsync`), and note the email it gets:
`docsync@<project>.iam.gserviceaccount.com`.

No IAM roles are needed. The service account reaches docs only because you
share them with it in step 4 — exactly like sharing with a person.

**2. Enable the two APIs** — Google Docs API and Google Drive API.

**3. Create a JSON key** and store it as a GitHub secret:

```sh
gh secret set GOOGLE_SERVICE_ACCOUNT_KEY < key.json
rm key.json          # the secret is the only copy that should exist
```

**4. Share every bound doc with the service-account email as Editor.**

Open each doc in `docsync.yml`, hit Share, paste the service-account email,
set Editor, uncheck "Notify people". Editor is required: docsync pushes to the
doc, not just reads it.

**5. Initialise each binding** — one push per binding, which replaces the doc's
contents with the repo's and records the sync state:

```sh
export GOOGLE_SERVICE_ACCOUNT_KEY="$(cat key.json)"
python3 -m docsync.sync push --id budget-primer
git add docsync/.state && git commit -m "docsync: initialise budget-primer" && git push
```

This overwrites the doc. Make a copy first if it holds anything you want.

After that the workflow takes over: a doc edit reaches the site within ~15
minutes, and a prose change pushed to `main` reaches the doc on the next run.

## Day to day

```sh
make -C report2027 doc-status    # has anything drifted?
make -C report2027 doc-diff      # what would a pull change?
make -C report2027 pull-doc      # doc -> repo, then rebuild
```

`pull` needs no credentials as long as the doc is link-shared — the Markdown
export endpoint is readable without them. `push` and `status` always need the
key, because only Drive can report when the doc last changed.

## What the engine will not do

* **Overwrite doc edits that were never pulled.** A push checks the doc's
  content hash and modified time against the last sync. If the doc moved and
  the repo moved, it stops and opens a `docsync-conflict` issue. Resolve by
  choosing a side: `make -C report2027 pull-doc` (doc wins) or
  `python3 -m docsync.sync push --id <id> --force` (repo wins).
* **Commit prose that would break the build.** A pull parses the doc exactly
  as the renderer will — every `[[key]]` present, every `[^id]` backed by a
  source — and writes nothing if it fails.
* **Preserve what Docs cannot represent.** Images, complex tables and layout
  don't round-trip. Prose, headings, bold/italic, links and lists do. The
  tests in `docsync/test_docsync.py` pin every quirk found so far.

## Adding a report

Add an entry to `docsync.yml`, share the doc with the service account, and run
one `push` to initialise. For a page that just wants a doc's prose, use
`fragment` mode and drop two comments where the content belongs:

```html
<!-- docsync:start -->
<!-- docsync:end -->
```
