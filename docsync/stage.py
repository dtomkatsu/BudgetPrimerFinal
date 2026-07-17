#!/usr/bin/env python3
"""Stage the draft editor next to a report.

    python3 -m docsync.stage --id budget-primer

The editor runs the report's OWN renderer in the browser, so it needs that
renderer, whatever the renderer reads, and a description of the report. All of
that is copied to `<dir>/engine/` and described by `<dir>/engine/manifest.json`,
and the editor is copied in beside it.

Two things this buys, and they are the point:

* **One editor, any report.** The editor knows nothing about the Budget Primer.
  It reads the manifest sitting next to it and renders whatever it names. A
  second report is a second entry in docsync.yml, not a second editor.
* **Same origin.** Fetching the renderer from raw.githubusercontent let its CDN
  hand out a copy several commits old — a page that renders fine and is quietly
  wrong. Staged here, the engine can only ever be the one that shipped with the
  editor it is running in.

Everything written here is a build artifact, like the rendered HTML. Never edit
it; edit `docsync/editor/edit.html` and re-stage.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docsync.registry import ROOT, Binding, RegistryError, get, load_registry  # noqa: E402

EDITOR = Path(__file__).resolve().parent / "editor" / "edit.html"
PACKAGE = ("content.py", "normalise.py", "layout.py")


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def manifest(b: Binding) -> dict:
    """What the editor needs to know, in the editor's own terms.

    Paths are given twice: the URL to fetch (relative to the editor's page) and
    the path the renderer expects inside Pyodide's filesystem. The renderer is
    written for a repo checkout, so the browser has to rebuild one.
    """
    e = b.editor
    files = {"engine/docsync/" + n: "docsync/" + n for n in PACKAGE}
    files["engine/" + rel(e.render)] = rel(e.render)
    files["engine/" + rel(b.content)] = rel(b.content)
    if e.layout:
        files["engine/" + rel(e.layout)] = rel(e.layout)
    for f in e.engine:
        files["engine/" + rel(f)] = rel(f)
    return {
        "id": b.id,
        "repo": None,               # filled by --repo, or the editor asks
        "files": files,
        "render": rel(e.render),
        "content": rel(b.content),
        "layout": rel(e.layout) if e.layout else None,
        "out": rel(e.out),
        "assets": rel(e.assets) if e.assets else None,
        "page": {"w": e.page[0], "h": e.page[1]},
        "margins": {"side": e.margins[0], "top": e.margins[1]},
        "palette": e.palette or [],
    }


def stage(b: Binding, repo: str = "") -> None:
    if not b.editor:
        raise RegistryError(f"'{b.id}' has no editor: block in docsync.yml")
    e = b.editor
    eng = e.dir / "engine"
    m = manifest(b)
    if repo:
        m["repo"] = repo

    for url, src in m["files"].items():
        dst = e.dir / url
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / src, dst)

    # A package needs an __init__; the real one imports the registry (pyyaml),
    # which the renderer never needs and Pyodide would have to install.
    (eng / "docsync" / "__init__.py").write_text("")
    (eng / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    shutil.copy2(EDITOR, e.dir / "edit.html")
    print(f"  staged {len(m['files'])} files + editor -> {rel(e.dir)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="only this binding (default: every one with an editor)")
    ap.add_argument("--repo", default="", help="owner/name the editor saves to")
    a = ap.parse_args()
    try:
        bindings = [get(a.id)] if a.id else [b for b in load_registry() if b.editor]
    except RegistryError as err:
        print(f"registry error: {err}", file=sys.stderr)
        return 2
    if not bindings:
        print("no bindings have an editor: block", file=sys.stderr)
        return 0
    for b in bindings:
        print(f"{b.id}:")
        stage(b, a.repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
