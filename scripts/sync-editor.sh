#!/bin/bash
# Pull the draft editor + docsync engine from the primer-editor repo into this
# report repo, so the local fast-loop (make -C report2027 live) runs the latest
# editor without this repo being where the editor is developed.
#
# Editor development lives in github.com/dtomkatsu/primer-editor. This vendors a
# snapshot of it here. Run it whenever you want the newest editor; commit the
# result like any other change.
#
#   ./scripts/sync-editor.sh                 # clones/pulls primer-editor to a cache
#   EDITOR_SRC=~/primer-editor ./scripts/sync-editor.sh   # use a local checkout
set -euo pipefail

REPO="${EDITOR_REPO:-https://github.com/dtomkatsu/primer-editor.git}"
SRC="${EDITOR_SRC:-$HOME/.cache/primer-editor}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Get / refresh the source.
if [ -n "${EDITOR_SRC:-}" ]; then
  echo "Using local editor checkout: $SRC"
elif [ -d "$SRC/.git" ]; then
  echo "Refreshing $SRC…"; git -C "$SRC" pull --ff-only --quiet
else
  echo "Cloning $REPO -> $SRC…"; git clone --quiet --depth 1 "$REPO" "$SRC"
fi

# The engine (content.py / layout.py / normalise.py + staging tooling) — the
# shared dependency this report's own `make pub` also imports. Vendored whole.
rsync -a --delete --exclude '__pycache__' --exclude '.state' "$SRC/docsync/" "$HERE/docsync/"

# The canonical editor source is docsync/editor/edit.html (came with docsync
# above). Re-stage it beside this report so docs/primer/ is current.
( cd "$HERE" && make -C report2027 editor >/dev/null )

# The parts of docs/primer that are the editor SHELL, not this report's staged
# engine (which `make editor` above regenerates): start page, importer, SW,
# manifest, icons.
for f in start.html htmlimport.js sw.js manifest.webmanifest; do
  [ -f "$SRC/docs/primer/$f" ] && cp "$SRC/docs/primer/$f" "$HERE/docs/primer/$f"
done
[ -d "$SRC/docs/primer/icons" ] && rsync -a "$SRC/docs/primer/icons/" "$HERE/docs/primer/icons/"

echo "Synced. Review with: git -C \"$HERE\" status"
