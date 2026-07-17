#!/usr/bin/env python3
"""Bind a Google Doc to a file in this repo, in one command.

    python3 -m docsync.bind snap-timeline --title "SNAP Timeline" \
        --mode fragment --target snap-timeline/index.html

Creates the doc, wires the registry, seeds the doc from the content file (or
seeds a starter file from the target page), and records the sync state. The
service account owns the new doc and shares it back to you, so there is no
per-doc sharing step — that is the difference between binding a doc in one
command and doing a five-minute console dance every time.

To adopt a doc that already exists, pass --doc <id-or-url>. That one you must
share with the service account yourself first (it cannot grant itself access to
something it does not own) — `doctor` prints the address to share with.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docsync import fetch                                     # noqa: E402
from docsync.registry import MODES, ROOT, REGISTRY, load_registry  # noqa: E402
from docsync.sync import do_push, token                       # noqa: E402

STARTER = """[[sources]]
"""


def doc_id_of(s: str) -> str:
    m = re.search(r"/document/d/([A-Za-z0-9_-]+)", s)
    return m.group(1) if m else s


def owner_email() -> str:
    """Who to share a new doc back to.

    Not git's user.email — that is usually a GitHub noreply alias, which is not
    a Google account and cannot be granted access. docsync.yml's `share_with`
    wins; otherwise ask gcloud who is logged in.
    """
    import subprocess                                          # noqa: PLC0415
    import yaml                                                # noqa: PLC0415

    data = yaml.safe_load(REGISTRY.read_text()) or {}
    if (who := (data.get("share_with") or "").strip()):
        return who
    r = subprocess.run(["gcloud", "config", "get-value", "account"],
                       capture_output=True, text=True)
    who = r.stdout.strip()
    return "" if not who or "noreply" in who else who


def folder_id() -> str | None:
    """The Drive folder new docs are created in, from docsync.yml's top level.
    Optional: without it a doc lands in the service account's own Drive, which
    works but will not show up in your Drive UI until it is shared."""
    import yaml                                                # noqa: PLC0415
    data = yaml.safe_load(REGISTRY.read_text()) or {}
    return (data.get("folder") or "").strip() or None


def registry_entry(b: dict) -> str:
    lines = [f"\n  - id: {b['id']}",
             f"    doc: {b['doc']}",
             f"    mode: {b['mode']}",
             f"    content: {b['content']}"]
    if b.get("target"):
        lines.append(f"    target: {b['target']}")
    if b.get("build"):
        lines.append(f"    build: {b['build']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id", help="binding id (lowercase kebab-case)")
    ap.add_argument("--title", help="title for the new doc (default: the id)")
    ap.add_argument("--mode", choices=list(MODES), default="fragment")
    ap.add_argument("--content", help="content file (default: <id>/content.md)")
    ap.add_argument("--target", help="fragment mode: the page to inject into")
    ap.add_argument("--build", default="", help="command to rebuild after a pull")
    ap.add_argument("--doc", help="adopt an existing doc instead of creating one")
    ap.add_argument("--share-with", default="", help="email to share the doc with "
                                                     "(default: git user.email)")
    args = ap.parse_args()

    # Everything checkable locally is checked before touching Google, so a
    # typo'd flag never surfaces as an auth error.
    if any(b.id == args.id for b in load_registry()):
        print(f"'{args.id}' is already bound — edit docsync.yml to change it",
              file=sys.stderr)
        return 2
    if args.mode == "fragment" and not args.target:
        print("fragment mode needs --target (the page to inject into)",
              file=sys.stderr)
        return 2
    content = ROOT / (args.content or f"{args.id}/content.md")

    tok = token()
    if not tok:
        print("bind needs GOOGLE_SERVICE_ACCOUNT_KEY — see docsync/SETUP.md",
              file=sys.stderr)
        return 2

    # Adopt vs create. Adoption cannot be automated end to end: only the doc's
    # owner can share it, and that is not us.
    if args.doc:
        doc = doc_id_of(args.doc)
        ok, why = fetch.can_access(doc, tok)
        if not ok:
            import os                                          # noqa: PLC0415
            sa = fetch.service_account_email(
                os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", ""))
            print(f"cannot reach that doc: {why}\n\n"
                  f"Share it with this address as Editor, then retry:\n  {sa}",
                  file=sys.stderr)
            return 2
        print(f"adopting existing doc {doc}")
    else:
        title = args.title or args.id
        doc = fetch.create_doc(title, tok, folder_id())
        print(f"created doc {doc} — https://docs.google.com/document/d/{doc}/edit")
        email = args.share_with or owner_email()
        if email:
            fetch.share(doc, email, tok)
            print(f"  shared with {email} as editor")

    if not content.exists():
        content.parent.mkdir(parents=True, exist_ok=True)
        content.write_text(STARTER if args.mode == "slots" else
                           f"# {args.title or args.id}\n\nWrite here.\n")
        print(f"  seeded {content.relative_to(ROOT)}")

    entry = {"id": args.id, "doc": doc, "mode": args.mode,
             "content": str(content.relative_to(ROOT)),
             "target": args.target, "build": args.build}
    REGISTRY.write_text(REGISTRY.read_text().rstrip("\n") + "\n"
                        + registry_entry(entry))
    print(f"  added to {REGISTRY.name}")

    b = next(x for x in load_registry() if x.id == args.id)
    do_push(b, tok, force=True)      # a doc we just made has nothing to lose
    print(f"\nbound. Commit docsync.yml and docsync/.state/{args.id}.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
