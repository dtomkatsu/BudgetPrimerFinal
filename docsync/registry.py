"""docsync.yml -> Binding objects.

The registry is the single place that says which doc feeds which file. Adding a
report to the sync is a registry entry, not new code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docsync.yml"

_ID_RE = re.compile(r"^[a-z0-9-]+$")
MODES = ("slots", "fragment")


class RegistryError(RuntimeError):
    pass


@dataclass
class Binding:
    id: str
    doc: str
    mode: str
    content: Path              # the committed file the doc syncs to
    build: str = ""            # shell command to rebuild after a pull
    target: Path | None = None  # fragment mode: page to inject into
    anchor: str = "docsync"    # fragment mode: <!-- docsync:start|end -->
    pr: bool = False           # open a PR instead of committing to main
    outputs: list[str] = field(default_factory=list)  # extra paths to commit

    @property
    def state_file(self) -> Path:
        return ROOT / "docsync" / ".state" / f"{self.id}.json"

    def __str__(self) -> str:
        return f"{self.id} ({self.mode})"


def _require(d: dict, key: str, where: str):
    if key not in d or d[key] in (None, ""):
        raise RegistryError(f"{where}: missing required key '{key}'")
    return d[key]


def load_registry(path: Path = REGISTRY) -> list[Binding]:
    try:
        import yaml                                   # noqa: PLC0415
    except ImportError as e:
        raise RegistryError("pyyaml is required: pip install pyyaml") from e

    if not path.exists():
        raise RegistryError(f"{path} does not exist")
    data = yaml.safe_load(path.read_text()) or {}
    raw = data.get("bindings") or []
    if not raw:
        raise RegistryError(f"{path}: no bindings defined")

    out, seen = [], set()
    for i, b in enumerate(raw):
        where = f"{path.name}: binding #{i + 1}"
        bid = _require(b, "id", where)
        if not _ID_RE.match(bid):
            raise RegistryError(f"{where}: id '{bid}' must be lowercase kebab-case")
        if bid in seen:
            raise RegistryError(f"{where}: duplicate id '{bid}'")
        seen.add(bid)

        mode = _require(b, "mode", where)
        if mode not in MODES:
            raise RegistryError(
                f"{where}: mode '{mode}' must be one of {', '.join(MODES)}")

        target = b.get("target")
        if mode == "fragment" and not target:
            raise RegistryError(f"{where}: fragment mode requires 'target'")

        out.append(Binding(
            id=bid,
            doc=_require(b, "doc", where),
            mode=mode,
            content=ROOT / _require(b, "content", where),
            build=b.get("build", ""),
            target=ROOT / target if target else None,
            anchor=b.get("anchor", "docsync"),
            pr=bool(b.get("pr", False)),
            outputs=list(b.get("outputs") or []),
        ))
    return out


def get(binding_id: str, path: Path = REGISTRY) -> Binding:
    for b in load_registry(path):
        if b.id == binding_id:
            return b
    raise RegistryError(f"no binding with id '{binding_id}' in {path.name}")
