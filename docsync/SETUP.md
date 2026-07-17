# docsync setup

The engine runs in GitHub Actions, so it needs a Google identity that isn't
tied to anyone's browser session: a **service account**, whose key lives in a
GitHub secret.

The important thing about the cost below: **it is once, ever — not per repo and
not per doc.** One service account serves every repo you own. One shared folder
removes per-doc sharing forever. After that, binding a new doc is one command.

```
once ever ........  ./docsync/setup.sh          (~2 min, needs gcloud + gh)
per new doc ......  python3 -m docsync.bind <id> --title "..."
anything wrong ...  python3 -m docsync.doctor
```

## Once, ever

```sh
./docsync/setup.sh
```

It creates a GCP project, enables the Docs and Drive APIs, makes a service
account, mints a key, stores it as the `GOOGLE_SERVICE_ACCOUNT_KEY` secret,
creates a Drive folder for synced docs, and shares that folder back to you. It
prints the folder id — put it in `docsync.yml` as `folder:` and you're done.

No IAM roles are granted. The service account can only reach docs you put in
that folder (or share with it by hand) — its blast radius is exactly what you
hand it, the same as sharing with a person.

To reuse the same account in **another repo**, don't re-run setup: just make
the key available there. An organisation-level secret covers every repo at
once, or `gh secret set GOOGLE_SERVICE_ACCOUNT_KEY -R owner/other-repo < key.json`.

### If you'd rather do it by hand

1. <https://console.cloud.google.com> — new project; enable **Google Docs API**
   and **Google Drive API**; create a service account; create a JSON key.
2. `gh secret set GOOGLE_SERVICE_ACCOUNT_KEY < key.json` then `rm key.json`.
3. Make a Drive folder, share it with the service-account email as **Editor**,
   and put its id (from the folder URL) in `docsync.yml` as `folder:`.

## Per new doc

```sh
python3 -m docsync.bind snap-timeline --title "SNAP Timeline" \
    --mode fragment --target snap-timeline/index.html
```

This creates the doc in the shared folder, shares it back to you, seeds a
content file, adds the registry entry, and initialises the sync state. There is
no sharing step: the service account made the doc, so it already has access.

For a doc that **already exists**, you must share it yourself first — the
service account cannot grant itself access to something it doesn't own. Run
`python3 -m docsync.doctor` to get the address, share as Editor, then:

```sh
python3 -m docsync.bind budget-primer --doc <url> --mode slots \
    --content report2027/content.md
```

Commit `docsync.yml` and `docsync/.state/<id>.json` afterwards.

## Day to day

```sh
python3 -m docsync.doctor         # what's set up, what isn't, what to do
make -C report2027 doc-status     # has anything drifted?
make -C report2027 doc-diff       # what would a pull change?
make -C report2027 pull-doc       # doc -> repo, then rebuild
```

`pull` needs no credentials while a doc is link-shared — the Markdown export
endpoint is readable without them. `push` and `status` always need the key,
because only Drive reports when a doc last changed.

## What the engine will not do

* **Overwrite doc edits that were never pulled.** A push compares the doc's
  content hash and modified time to the last sync. If both sides moved, it
  stops and opens a `docsync-conflict` issue. Resolve by choosing a side:
  `make -C report2027 pull-doc` (doc wins) or
  `python3 -m docsync.sync push --id <id> --force` (repo wins).
* **Commit prose that would break the build.** A pull parses the doc exactly as
  the renderer will — every `[[key]]` present, every `[^id]` backed by a source
  — and writes nothing if that fails.
* **Preserve what Docs cannot represent.** Images, complex tables and layout
  don't round-trip; prose, headings, bold/italic, links and lists do.
  `docsync/test_docsync.py` pins every quirk found so far, so a change in
  Google's exporter fails there first.

## Modes

**slots** — the doc fills named `[[key]]` slots and the renderer owns layout.
Right for art-directed reports. New prose sections need no code: add
`[[extra.<page>.<slug>]]`.

**fragment** — the whole doc becomes HTML between two comments in a page. Right
for anything that just wants a doc's prose:

```html
<!-- docsync:start -->
<!-- docsync:end -->
```
