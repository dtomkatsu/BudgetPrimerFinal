# Saving & collaboration — scope

How the draft editor should save and share work when it's used across **many
projects, by more than one person**. Grounded in how saving works today, then a
phased plan.

---

## 1. How saving works today

The editor (`docs/primer/edit.html`) loads a per-project **manifest**
(`engine/manifest.json`: `id`, `repo`, and the paths of `content.md` /
`layout.json`), renders the report locally through the real Python renderer via
Pyodide, and on **Save** writes back to GitHub.

Two save modes:

- **Local dev** — POSTs `{content, layout}` to `/__save` on the dev server,
  which commits and pushes. No token. (Only when the editor is served by that
  server.)
- **GitHub** — the real path. Uses a **fine-grained PAT** kept in
  `localStorage['docsync-pat']`. On Save it builds a list of changed files
  (`content.md`, and `layout.json` if the visual layer changed) and issues **one
  `PUT contents/<path>` per file, each a separate commit, each `branch: main`**,
  each fetching the file's current `sha` first for optimistic concurrency.
  Uploaded images are a third `PUT` to `main`. A commit to `main` triggers the
  site rebuild and the Google-Doc sync.

### Why this doesn't scale to collaboration

The 55-vs-3 commit fork this document was written after is the failure mode in
the wild, not a hypothetical:

1. **Everyone commits straight to `main`.** No isolation. Two people (or two
   machines) editing at once race on the same files. The only guard is the
   `sha` check → a raw **409** with no resolution UI; the loser silently
   re-saves over, or diverges into a fork.
2. **Non-atomic save.** `content.md` and `layout.json` go as **two separate
   commits**. A failure between them, or two people interleaving, leaves `main`
   in a half-updated state (prose from one edit, layout from another).
3. **PAT per browser.** Each collaborator must mint a fine-grained token with
   Contents:write and paste it in. High friction, no identity (commits aren't
   attributed to the real author), and a write token sits in `localStorage`.
4. **No sharing primitive.** "Share a draft" = push to `main` and tell someone
   to look at the live site. There is no draft URL, no preview, no review.
5. **One repo per deployment.** `repo` is fixed in the manifest. "Many
   projects" today means many separate editor deployments.
6. **Publish == Save.** Every Save is a publish (rebuilds the live site). There
   is no staging between "I'm drafting" and "this is live."

---

## 2. Goals

- **No clobbering.** Concurrent editors never overwrite each other silently.
- **One Save = one atomic change.** Prose + layout move together or not at all.
- **Low-friction identity.** A collaborator signs in once; commits are theirs.
- **Share a draft as a link.** Someone can see the draft without it being live.
- **Draft ≠ publish.** Explicit, reviewable step to go live.
- **Many projects, one editor.** Pick a project; the editor retargets.
- **Keep the good parts.** Local-first Pyodide render, content.md as source of
  truth, git as the durable store and history.

---

## 3. Options

### A. Branch-per-draft + PR (GitHub-native, no new infra)  ← recommended first
Save commits to a **draft branch** (`draft/<project>/<user>`), not `main`.
Three verbs replace one Save:
- **Save draft** → atomic commit of content+layout to the user's draft branch
  (via the Git Data API: blobs → tree → one commit → update ref).
- **Share** → copy the draft's **preview URL** (a per-branch build) and/or open
  a PR.
- **Publish** → open/merge the PR into `main` (which rebuilds the live site).

- *Pros:* isolation (no clobber), atomic commits, real review, attribution via
  PR, history = git. Zero backend — GitHub does it all. Directly prevents the
  fork we hit.
- *Cons:* PAT friction remains (until Option B). Per-branch preview needs an
  Actions workflow. Branch/PR concepts must hide behind the three buttons for
  non-technical authors.

### B. GitHub App + OAuth (identity & tokens solved)
A tiny serverless endpoint (Cloudflare Worker / Vercel function) backs a GitHub
**App** installed on the project repos. Collaborators **sign in with GitHub**;
the endpoint mints a short-lived, repo-scoped token (or commits on their
behalf). Editor calls the endpoint instead of holding a PAT.

- *Pros:* no manual tokens; commits attributed to the real user; central
  permissions; multi-repo is "which repos is the App installed on." Can later
  host locking/presence.
- *Cons:* one small service to host and maintain. Best layered **on top of A**.

### C. Real-time multiplayer (CRDT / Yjs + periodic commit)
Live co-editing with presence; a sync server holds the live doc and commits to
GitHub as the durable/publish store.

- *Pros:* best possible collaboration UX; clobbering is impossible.
- *Cons:* heaviest; overkill for a report edited occasionally. Only if
  simultaneous editing becomes the norm.

---

## 4. Recommendation — phased

**Phase 1 — branch-per-draft, atomic, shareable (Option A).** Highest value,
no new infrastructure, and it fixes the exact failure we just untangled.
1. Retarget Save from `main` to `draft/<project>/<user>`.
2. Make Save **atomic** — one commit for content+layout via the Git Data API,
   replacing the two-`PUT` sequence.
3. Add **Save draft / Share / Publish**. Share copies a preview link; Publish
   opens or merges a PR to `main`.
4. Add an Actions workflow that builds a **per-branch preview** so a draft URL
   exists to share.
5. **Conflict handling:** on a stale-ref push, fetch, show "N changes landed
   since you started," offer rebase-onto-latest or open the diff — never a bare
   409.

**Phase 2 — GitHub App + OAuth (Option B).** Remove manual PATs; real identity
and attribution; multi-repo permissioning. Serverless, short-lived tokens.

**Phase 3 — presence/locking, or CRDT (Option C).** Only if concurrent editing
becomes common. Cheap interim: a soft lock ("Devin is editing — opened 4m ago")
written to the draft branch, before committing to full CRDT.

**Multi-project (spans all phases):** make the editor take a `?project=<id>`
that selects a manifest from a small registry, so one deployed editor serves
every report instead of one deployment per repo.

---

## 5. Concrete first steps (Phase 1, in order)

1. **Atomic commit helper** — replace the per-file `PUT contents/*` loop with a
   `commitTree(repo, branch, [{path, content}], message)` using the Git Data
   API (create blobs → base tree → new tree → commit → `PATCH refs/heads/...`).
   Self-contained; testable against a scratch branch.
2. **Branch selector + `Save draft`** — derive `draft/<project>/<user>`,
   auto-create from `main` if absent, commit there. `#save` becomes `Save
   draft`.
3. **`Share`** — button that copies the preview URL (once the preview workflow
   exists) and offers "open a PR."
4. **Preview workflow** — Actions job building each `draft/**` branch to a
   preview path.
5. **`Publish`** — open/merge the PR to `main`; keep today's rebuild-on-`main`.
6. **Conflict UX** — replace the raw 409 with a fetch + summary + choice.

Each step ships and is verifiable on its own; none needs a backend. Phase 2
layers auth on top without reworking Phase 1.
