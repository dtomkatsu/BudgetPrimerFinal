"""Per-binding sync state, committed to the repo.

The Apps Script kept this in PropertiesService, which lives inside one doc and
is invisible to CI. Committing it instead means any machine — a laptop, a
workflow run — can tell whether the doc has moved since the last sync.

    content_hash  what was last known to be on BOTH sides
    doc_modified  Drive modifiedTime right after that sync
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class State:
    content_hash: str = ""
    doc_modified: str = ""
    synced_at: str = ""

    @property
    def initialised(self) -> bool:
        return bool(self.content_hash and self.doc_modified)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load(path: Path) -> State:
    if not path.exists():
        return State()
    try:
        return State(**json.loads(path.read_text()))
    except (json.JSONDecodeError, TypeError) as e:
        raise RuntimeError(f"{path} is corrupt — delete it to re-initialise: {e}")


def save(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2) + "\n")
