#!/usr/bin/env python3
"""Diagnose a docsync setup and print exactly what is missing.

    python3 -m docsync.doctor

Everything about this setup fails in the same few ways — no key, key present
but the doc was never shared, folder missing, binding never initialised. Each
one produces a different unhelpful error from Google. This turns all of them
into one checklist with the next action spelled out.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docsync import fetch, state as st                        # noqa: E402
from docsync.bind import folder_id                            # noqa: E402
from docsync.registry import RegistryError, load_registry     # noqa: E402

OK, WARN, BAD = "  ok  ", " todo ", " FAIL "


def line(mark: str, msg: str, fix: str = "") -> None:
    print(f"[{mark}] {msg}")
    if fix:
        print(f"         -> {fix}")


def main() -> int:
    problems = 0
    print("docsync doctor\n")

    key = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", "").strip()
    if not key:
        line(WARN, "no GOOGLE_SERVICE_ACCOUNT_KEY in the environment",
             "locally: export GOOGLE_SERVICE_ACCOUNT_KEY=\"$(cat key.json)\"\n"
             "         in CI:   gh secret set GOOGLE_SERVICE_ACCOUNT_KEY < key.json\n"
             "         to make one: ./docsync/setup.sh   (see docsync/SETUP.md)")
        print("\nWithout a key only `pull` works, and only on link-shared docs.")
        return 1

    sa = fetch.service_account_email(key)
    if not sa:
        line(BAD, "GOOGLE_SERVICE_ACCOUNT_KEY is not a service-account key",
             "it should be the whole key.json, starting '{'. Re-mint with "
             "./docsync/setup.sh")
        return 1
    line(OK, f"service account: {sa}")

    try:
        # Check the real import chain: google-auth does not pull in requests,
        # so `import google.auth` succeeding proves nothing.
        from google.auth.transport.requests import Request      # noqa: F401,PLC0415
        from google.oauth2 import service_account               # noqa: F401,PLC0415
    except ImportError as e:
        line(BAD, f"a dependency is missing ({e.name})",
             "pip install google-auth requests pyyaml")
        return 1

    try:
        tok = fetch.access_token(key)
        line(OK, "key mints an access token")
    except fetch.FetchError as e:
        line(BAD, f"key will not authenticate: {e}",
             "re-run ./docsync/setup.sh to mint a fresh key")
        return 1

    fid = folder_id()
    if fid:
        ok, why = fetch.can_access(fid, tok)
        line(OK if ok else BAD, f"docs folder {fid}" + ("" if ok else f" — {why}"),
             "" if ok else f"share that folder with {sa} as Editor")
        problems += 0 if ok else 1
    else:
        line(WARN, "no 'folder:' in docsync.yml",
             "new docs will land in the service account's own Drive and will "
             "not appear in yours until shared.\n"
             "         Make a Drive folder, share it with the address above as "
             "Editor, and add its id as 'folder:' in docsync.yml.")

    try:
        bindings = load_registry()
    except RegistryError as e:
        line(BAD, f"registry: {e}")
        return 1

    print()
    for b in bindings:
        ok, why = fetch.can_access(b.doc, tok)
        if not ok:
            line(BAD, f"{b.id}: cannot reach its doc — {why}",
                 f"share https://docs.google.com/document/d/{b.doc}/edit "
                 f"with {sa} as Editor")
            problems += 1
            continue
        if not b.content.exists():
            line(BAD, f"{b.id}: {b.content} is missing")
            problems += 1
            continue
        s = st.load(b.state_file)
        if not s.initialised:
            line(WARN, f"{b.id}: never initialised",
                 f"python3 -m docsync.sync push --id {b.id}   "
                 f"(this REPLACES the doc's contents)")
        else:
            line(OK, f"{b.id}: bound, last synced {s.synced_at[:19] or '?'}")

    print()
    if problems:
        print(f"{problems} problem(s) to fix before the sync can run.")
        return 1
    print("Setup looks good.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
