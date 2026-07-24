"""Vendor the engine into every consumer repo — automatically.

    python3 -m docsync.vendor            # sync all consumers in vendor.yml
    python3 -m docsync.vendor --dry-run  # show what would change
    python3 -m docsync.vendor --force    # overwrite even a dirty consumer
    python3 -m docsync.vendor --no-commit

This repo is the canonical home of the editor engine; consumer repos
(~/BudgetPrimerFinal, and any future report repo) carry vendored COPIES so
each stays self-contained for CI, other machines and madison. The copies
used to be synced by hand — "fix here, remember to copy" — which is exactly
the kind of accounting that rots. Now:

- WHAT the engine is needs no manifest: every file git tracks under
  docsync/ plus report2027/tools/serve.py. Add a module to the package and
  it vendors itself.
- WHO consumes it is one line per repo in vendor.yml.
- WHEN is automatic: .githooks/post-commit runs this after any commit that
  touches an engine path (install once per clone:
  git config core.hooksPath .githooks).

Per consumer this script: refuses if the consumer's engine paths are dirty
(engine edits must never originate in a consumer — fix here first;
--force overrides), copies the canonical files, restages every editor
binding in the consumer's own docsync.yml, and commits JUST the engine
paths there (a local commit only — deploying is still the consumer's own
explicit Push). It never starts or stops anyone's dev server; if the
consumer's live server is running, it reminds you to relaunch the app.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR_YML = ROOT / "vendor.yml"

# Engine paths, relative to either repo root. serve.py rides along because
# consumers run the live server from their own checkout.
EXTRA = ["report2027/tools/serve.py"]


def _sh(args: list[str], cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          check=True).stdout


def engine_files() -> list[str]:
    """Every tracked file under docsync/ (the package IS the manifest)."""
    files = [f for f in _sh(["git", "ls-files", "docsync/"], ROOT).splitlines()
             if f and not f.endswith((".pyc",))]
    return files + EXTRA


def consumers() -> list[Path]:
    import yaml                                       # noqa: PLC0415
    if not VENDOR_YML.exists():
        print(f"{VENDOR_YML} not found — no consumers registered", file=sys.stderr)
        return []
    data = yaml.safe_load(VENDOR_YML.read_text()) or {}
    out = []
    for c in data.get("consumers") or []:
        p = Path(str(c["path"] if isinstance(c, dict) else c)).expanduser()
        if not (p / "docsync.yml").exists():
            print(f"  skipping {p}: no docsync.yml (not a docsync repo)",
                  file=sys.stderr)
            continue
        out.append(p)
    return out


def dirty_engine_paths(repo: Path) -> list[str]:
    out = _sh(["git", "status", "--porcelain", "--",
               "docsync", *EXTRA], repo)
    return [l for l in out.splitlines() if l.strip()]


def stage_ids(repo: Path) -> list[str]:
    """Editor bindings in the CONSUMER's registry, read with its own code."""
    code = ("import sys; sys.path.insert(0, '.');"
            "from docsync.registry import load_registry;"
            "print('\\n'.join(b.id for b in load_registry() if b.editor))")
    try:
        return [l for l in _sh([sys.executable, "-c", code], repo).splitlines() if l]
    except subprocess.CalledProcessError as e:
        print(f"  could not read {repo.name}/docsync.yml: {e.stderr.strip()}",
              file=sys.stderr)
        return []


def vendor_one(repo: Path, files: list[str], *, dry: bool, force: bool,
               commit: bool) -> bool:
    print(f"\n{repo}")
    dirty = dirty_engine_paths(repo)
    if dirty and not force:
        print("  REFUSING: engine paths are dirty in the consumer — engine "
              "changes must be made in primer-editor, not here. Reconcile "
              "(or --force to overwrite):")
        for l in dirty[:10]:
            print(f"    {l}")
        return False

    changed = []
    for rel in files:
        src, dst = ROOT / rel, repo / rel
        if not src.exists():
            continue
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            continue
        changed.append(rel)
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    if not changed:
        print("  already in sync")
        return True
    for rel in changed:
        print(f"  {'would copy' if dry else 'copied'}  {rel}")
    if dry:
        return True

    ids = stage_ids(repo)
    for bid in ids:
        r = subprocess.run([sys.executable, "-m", "docsync.stage", "--id", bid],
                           cwd=repo)
        if r.returncode != 0:
            print(f"  STAGE FAILED for '{bid}' — fix and re-run "
                  f"python3 -m docsync.stage --id {bid} in {repo}",
                  file=sys.stderr)
            return False

    if commit:
        # engine paths plus the restaged editor bundles (each binding's
        # editor dir lives under docs/ by convention; add skips the unchanged)
        paths = ["docsync", *EXTRA] + (["docs"] if (repo / "docs").is_dir() else [])
        subprocess.run(["git", "add", "--", *paths], cwd=repo, capture_output=True)
        msg = ("vendor engine from primer-editor\n\n"
               "Automated copy by python3 -m docsync.vendor (primer-editor "
               "is the engine's canonical home; see its CLAUDE.md). "
               f"Files: {', '.join(changed)}")
        r = subprocess.run(["git", "commit", "-m", msg], cwd=repo,
                           capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  committed in {repo.name} (local only — Push stays yours)")
        else:
            print("  nothing new to commit" if "nothing" in r.stdout
                  else f"  commit failed: {r.stderr.strip()}")

    if any(rel.endswith(("serve.py", "edit.html")) for rel in changed):
        print("  NOTE: if this repo's live editor server is running, relaunch "
              "its app to pick up the new engine (never restart it from here).")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Vendor the engine to consumers.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="overwrite a consumer whose engine paths are dirty")
    ap.add_argument("--no-commit", action="store_true",
                    help="copy + restage but leave the consumer uncommitted")
    args = ap.parse_args()

    files = engine_files()
    ok = True
    reps = consumers()
    if not reps:
        return 0
    for repo in reps:
        ok = vendor_one(repo, files, dry=args.dry_run, force=args.force,
                        commit=not args.no_commit) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
