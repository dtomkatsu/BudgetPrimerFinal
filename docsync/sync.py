#!/usr/bin/env python3
"""docsync — keep Google Docs and this repo's reports in step.

    python3 -m docsync.sync status              # what has drifted, per binding
    python3 -m docsync.sync pull [--id X]       # doc -> repo (validated)
    python3 -m docsync.sync push [--id X]       # repo -> doc (conflict-checked)
    python3 -m docsync.sync check [--id X]      # validate the doc, write nothing
    python3 -m docsync.sync build [--id X]      # re-run the report's build

`pull` is safe by construction: a doc that does not satisfy the report is never
written. `push` is safe by conflict check: a doc holding edits that are not in
the repo is never overwritten — it reports a conflict and stops.

Credentials: set GOOGLE_SERVICE_ACCOUNT_KEY (the service-account JSON) to reach
docs that are not link-shared, and for `push`, which always needs them. See
docsync/SETUP.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import os
import subprocess
import sys
import tempfile
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docsync import fetch, fragment, state as st                    # noqa: E402
from docsync.content import Content, ContentError                   # noqa: E402
from docsync.normalise import leading_comment, normalise            # noqa: E402
from docsync.registry import Binding, RegistryError, get, load_registry  # noqa: E402


class Status(str, Enum):
    IN_SYNC = "in-sync"
    DOC_AHEAD = "doc-ahead"        # doc has edits the repo lacks -> pull
    REPO_AHEAD = "repo-ahead"      # repo has edits the doc lacks -> push
    CONFLICT = "conflict"          # both moved apart -> human required
    UNINITIALISED = "uninitialised"


def token() -> str | None:
    key = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", "").strip()
    return fetch.access_token(key) if key else None


def doc_content(b: Binding, tok: str | None) -> str:
    """The doc, normalised into the committed file's canonical form."""
    header = leading_comment(b.content.read_text()) if b.content.exists() else ""
    return normalise(fetch.fetch_markdown(b.doc, tok), header)


def validate(b: Binding, md: str) -> str:
    """Parse exactly as the build will. Raises ContentError if the doc could
    not produce a working report."""
    if b.mode == "fragment":
        html = fragment.to_html(md)
        if not html.strip():
            raise ContentError(f"{b.id}: the doc converted to an empty fragment")
        return f"fragment: {len(html)} chars of HTML"

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(md)
        tmp = Path(f.name)
    try:
        c = Content(tmp)
        import re                                          # noqa: PLC0415
        for sid in re.findall(r"\[\^([^\]]+)\]", md):
            if sid not in c.sources:
                raise ContentError(
                    f"{b.id}: prose cites [^{sid}] but no such id under [[sources]]")
        return f"slots: {len(c._raw)} keys, {len(c.sources)} sources"
    finally:
        tmp.unlink(missing_ok=True)


def local_content(b: Binding) -> str:
    return b.content.read_text() if b.content.exists() else ""


def status_of(b: Binding, tok: str | None) -> tuple[Status, str]:
    s = st.load(b.state_file)
    local = local_content(b)
    remote = doc_content(b, tok)

    doc_changed = st.content_hash(remote) != s.content_hash
    repo_changed = st.content_hash(local) != s.content_hash

    if not s.initialised:
        return Status.UNINITIALISED, "no sync state recorded yet"
    if remote == local:
        return Status.IN_SYNC, ""
    if doc_changed and repo_changed:
        return Status.CONFLICT, "the doc and the repo have diverged"
    if doc_changed:
        return Status.DOC_AHEAD, "the doc has edits the repo does not"
    return Status.REPO_AHEAD, "the repo has edits the doc does not"


def render_build(b: Binding) -> None:
    if not b.build:
        return
    print(f"  building: {b.build}")
    r = subprocess.run(b.build, shell=True, cwd=b.content.parent.parent,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise ContentError(f"{b.id}: build failed\n{r.stdout[-2000:]}{r.stderr[-2000:]}")


def record(b: Binding, content: str, tok: str) -> None:
    """Mark both sides as agreeing on `content` right now.

    A sync point, wherever it came from: the hash is what the doc and the repo
    last agreed on, and every later 'did this side move?' is measured from it.
    """
    st.save(b.state_file, st.State(
        content_hash=st.content_hash(content),
        doc_modified=fetch.fetch_modified_time(b.doc, tok),
        synced_at=dt.datetime.now(dt.timezone.utc).isoformat()))


def do_pull(b: Binding, tok: str | None, write: bool, show_diff: bool) -> bool:
    md = doc_content(b, tok)
    print(f"  {validate(b, md)}")

    old = local_content(b)
    if md == old:
        print("  already matches the doc")
        # The sides agree, so this is a sync point even though nothing moved —
        # recording it keeps a stale hash from inventing a conflict later.
        if tok and st.content_hash(md) != st.load(b.state_file).content_hash:
            record(b, md, tok)
        return False
    if show_diff:
        sys.stdout.writelines(difflib.unified_diff(
            old.splitlines(True), md.splitlines(True),
            fromfile=f"{b.content.name} (repo)", tofile=f"{b.content.name} (doc)"))
    if not write:
        return True

    b.content.write_text(md)
    if b.mode == "fragment" and b.target:
        page = b.target.read_text()
        b.target.write_text(fragment.inject(page, fragment.to_html(md), b.anchor))
    render_build(b)
    print(f"  wrote {b.content.relative_to(b.content.parent.parent.parent)}")
    # A pull IS a sync point: both sides now hold `md`. Without this the next
    # repo edit reads as "both sides moved" and reports a conflict nobody caused.
    if tok:
        record(b, md, tok)
    else:
        print("  note: no credentials, so the sync point was not recorded — "
              "run `status` with a key to re-establish it")
    return True


def do_push(b: Binding, tok: str, force: bool) -> Status:
    if not b.content.exists():
        raise ContentError(f"{b.id}: {b.content} does not exist")
    local = local_content(b)
    s = st.load(b.state_file)

    if not force:
        status, why = status_of(b, tok)
        if status is Status.IN_SYNC:
            print("  doc already matches the repo")
            record(b, local, tok)
            return status
        if status is Status.CONFLICT:
            print(f"  CONFLICT — {why}; not touching either side")
            return status
        if status is Status.DOC_AHEAD:
            print(f"  refusing — {why}; run `pull` first")
            return status
        if status is Status.UNINITIALISED and not s.initialised:
            print("  no sync state — pushing to initialise "
                  "(the doc's current contents are replaced)")

    fetch.replace_doc(b.doc, local, tok)
    record(b, local, tok)
    print("  doc updated from the repo")
    return Status.IN_SYNC


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["status", "pull", "push", "check", "build"])
    ap.add_argument("--id", help="only this binding (default: all)")
    ap.add_argument("--diff", action="store_true", help="show pending changes")
    ap.add_argument("--force", action="store_true",
                    help="push: overwrite the doc, discarding its edits")
    args = ap.parse_args()

    try:
        bindings = [get(args.id)] if args.id else load_registry()
    except RegistryError as e:
        print(f"registry error: {e}", file=sys.stderr)
        return 2

    tok = token() if args.action != "build" else None
    if args.action == "push" and not tok:
        print("push needs GOOGLE_SERVICE_ACCOUNT_KEY — see docsync/SETUP.md",
              file=sys.stderr)
        return 2

    rc, conflicts = 0, []
    for b in bindings:
        print(f"\n{b}  <- doc {b.doc[:12]}…")
        try:
            if args.action == "build":
                # Rebuilding is not syncing: someone editing content.md or
                # layout.json needs the site regenerated, and that has nothing
                # to do with the Google Doc. Conflating them meant every save
                # from the editor pushed prose to the doc and never rebuilt the
                # page — so nothing an editor did ever reached the report.
                render_build(b)
                print("  built")
            elif args.action in ("status",):
                status, why = status_of(b, tok)
                print(f"  {status.value}{' — ' + why if why else ''}")
                if status is Status.CONFLICT:
                    conflicts.append(b.id)
            elif args.action in ("pull", "check"):
                changed = do_pull(b, tok, write=(args.action == "pull"),
                                  show_diff=args.diff or args.action == "check")
                if args.action == "check" and changed:
                    print("  (check only — nothing written)")
            elif args.action == "push":
                if do_push(b, tok, args.force) is Status.CONFLICT:
                    conflicts.append(b.id)
        except (ContentError, fetch.FetchError) as e:
            print(f"  REFUSED — {e}", file=sys.stderr)
            rc = 1

    if conflicts:
        print(f"\nconflicts needing a human: {', '.join(conflicts)}", file=sys.stderr)
        rc = rc or 3
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
