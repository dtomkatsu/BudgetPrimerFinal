#!/usr/bin/env python3
"""Render-level regression tests (run by `make -C report2027 validate`).

The one guarantee here: moving text around never breaks the LIVE PREVIEW. Cut a
sentence to paste it elsewhere and, for those few seconds, the source it cited
has nothing pointing at it. In edit mode that must NOT crash the build (it made
a routine move feel like a "critical error"); at publish time it still must, so
a source that stays orphaned — a citation typo, a real dangling def — is caught
before it ships.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent          # report2027/tools
REPORT = HERE.parent                            # report2027
CONTENT = REPORT / "content.md"
FAILS = []


def render(content_path, edit_mode):
    """Run render_report.py against a content file; return (ok, output)."""
    env = dict(os.environ, DOCSYNC_CONTENT=str(content_path))
    if edit_mode:
        env["DOCSYNC_EDIT"] = "1"
    else:
        env.pop("DOCSYNC_EDIT", None)
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        env["DOCSYNC_OUT"] = f.name
    r = subprocess.run([sys.executable, "tools/render_report.py"],
                       cwd=str(REPORT), env=env, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)


def main():
    src = CONTENT.read_text()
    # Pick any footnote citation the fixture has, and drop just that token so the
    # source it names is orphaned while everything else stays valid.
    # Pick a footnote whose source is cited exactly ONCE, so dropping that one
    # citation fully orphans its source (a multiply-cited source would stay
    # cited by its other references).
    import re
    from collections import Counter
    counts = Counter(re.findall(r"\[\^([a-z0-9-]+)\]", src))
    single = next((tok for tok, n in counts.items()
                   if n == 1 and f"[{tok}]:" in src), None)
    assert single, "fixture has no singly-cited footnote to test with"
    token = f"[^{single}]"
    orphaned = src.replace(token, "")            # remove the lone citation → its source is now uncited

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(orphaned)
        draft = f.name

    ok_edit, out_edit = render(draft, edit_mode=True)
    if not ok_edit:
        FAILS.append("edit mode should TOLERATE an orphaned source (mid-move), "
                     f"but the build failed:\n{out_edit[-400:]}")

    ok_pub, out_pub = render(draft, edit_mode=False)
    if ok_pub:
        FAILS.append("publish mode should REFUSE an orphaned source, but the build passed")
    elif "never cited" not in out_pub:
        FAILS.append(f"publish failed for the wrong reason:\n{out_pub[-400:]}")

    # Sanity: the untouched fixture builds clean in publish mode.
    ok_clean, out_clean = render(CONTENT, edit_mode=False)
    if not ok_clean:
        FAILS.append(f"the untouched fixture should build, but it failed:\n{out_clean[-400:]}")

    os.unlink(draft)
    if FAILS:
        print("RENDER TESTS FAILED:\n" + "\n\n".join(FAILS))
        sys.exit(1)
    print("render tests passed")


if __name__ == "__main__":
    main()
