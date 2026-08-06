#!/usr/bin/env python3
"""An MCP server exposing a running docsync editor's reports, READ-ONLY.

Point any MCP client at this and it can answer "what is in this report?" —
every slot's markdown, every source and whether it is cited, every placed
object's geometry, every addressable element id — without a browser and
without knowing anything about the editor's internals.

    claude mcp add primer -- python3 /path/to/docsync/mcp_server.py

It is a thin client over the dev server's own /__inventory and /__ping
(report2027/tools/serve.py); PRIMER_URL overrides the default origin. No
dependencies, by the same argument serve.py makes for urllib over a package:
two endpoints and a line protocol do not justify one, and this has to run
wherever the editor already runs.

WHY READ-ONLY, deliberately
---------------------------
Editing belongs to the browser's window.docsync.api, not here. The editor
holds the document in MEMORY: open a report, type, and content.md on disk is
already stale. A write from this side would land on disk under that session
and be silently overwritten by its next Save — the edit would simply vanish,
with nothing to see and nothing to undo. The browser API has no such gap:
every verb runs pushHistory() first, so a pilot's edit is one ⌘Z from undone
and visibly part of the same document the human is looking at.

Reads have no such hazard — a stale read is merely stale, and /__ping's
version says so. So this server does the half that is safe from outside, and
leaves the half that needs to be inside, inside. Giving it writes means first
answering how an out-of-band write coordinates with an open editor's unsaved
buffer; until there is an answer, "cannot" beats "sometimes eats your work".
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("PRIMER_URL", "http://localhost:8010").rstrip("/")
PROTOCOL = "2025-06-18"          # echoed back to a client that asks for another
TIMEOUT = 180                    # an elements render is a full build; be patient


def _get(path: str, params: dict | None = None) -> dict:
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:                                   # noqa: BLE001
            return {"ok": False, "error": f"HTTP {e.code} from {url}"}
    except urllib.error.URLError as e:
        # By far the commonest failure, and worth naming rather than leaking a
        # connection-refused traceback: the editor simply is not running.
        return {"ok": False, "error": f"no editor server at {BASE} ({e.reason}). "
                "Start it (the Budget Primer Editor app, or `make -C report2027 "
                "live`), or set PRIMER_URL if it listens elsewhere."}
    except (TimeoutError, json.JSONDecodeError) as e:
        return {"ok": False, "error": f"{BASE}{path}: {e}"}


# ---------------------------------------------------------------- tools

def t_list_reports(_args: dict) -> dict:
    """Every report this editor serves."""
    reg = _get("/projects.json")
    if isinstance(reg, dict) and reg.get("ok") is False:
        return reg
    return {"ok": True, "reports": [
        {"id": pid, "name": e.get("name", pid), "repo": e.get("repo"),
         "local_root": e.get("local_root")}
        for pid, e in sorted(reg.items())]}


def t_status(args: dict) -> dict:
    """Build state: version, unpushed commits, and any build error."""
    return _get("/__ping", {"project": args["project"]})


def t_inventory(args: dict) -> dict:
    """The whole report as data. `elements` costs a render; skip it when the
    question is only about text."""
    return _get("/__inventory", {"project": args["project"],
                                 "elements": "1" if args.get("elements", True) else "0"})


def t_get_slot(args: dict) -> dict:
    """One slot's full markdown — the unit the editor edits."""
    inv = _get("/__inventory", {"project": args["project"], "elements": "0"})
    if not inv.get("ok"):
        return inv
    key = args["key"]
    for s in inv["slots"]:
        if s["key"] == key:
            return {"ok": True, "key": key, "md": s["md"]}
    near = [s["key"] for s in inv["slots"] if key.lower() in s["key"].lower()][:8]
    return {"ok": False, "error": f"no slot '{key}'",
            "did_you_mean": near or [s["key"] for s in inv["slots"][:8]]}


def t_search(args: dict) -> dict:
    """Find where a phrase appears — across slot markdown, source citations
    and text-box contents. The headless answer to "where does the report say
    X?", which otherwise means reading every slot."""
    inv = _get("/__inventory", {"project": args["project"], "elements": "0"})
    if not inv.get("ok"):
        return inv
    q = args["query"].lower()
    hits = []
    for s in inv["slots"]:
        if q in s["md"].lower():
            i = s["md"].lower().index(q)
            hits.append({"where": "slot", "key": s["key"],
                         "excerpt": s["md"][max(0, i - 60):i + len(q) + 60].strip()})
    for s in inv["sources"]:
        if q in (s["text"] + " " + s["url"]).lower():
            hits.append({"where": "source", "key": s["id"],
                         "excerpt": s["text"], "cites": s["cites"]})
    for b in inv["placed"]["boxes"]:
        if q in str(b.get("md", "")).lower():
            hits.append({"where": "textbox", "key": "text." + str(b.get("id")),
                         "page": b.get("page"), "excerpt": str(b.get("md"))[:160]})
    return {"ok": True, "query": args["query"], "count": len(hits), "hits": hits}


def t_uncited_sources(args: dict) -> dict:
    """Sources nothing cites. They RENDER while editing but refuse to publish,
    so this is the check worth running before anyone tries to ship."""
    inv = _get("/__inventory", {"project": args["project"], "elements": "0"})
    if not inv.get("ok"):
        return inv
    bad = [s for s in inv["sources"] if not s["cites"]]
    return {"ok": True, "uncited": bad, "count": len(bad),
            "publishable": not bad,
            "note": "an uncited source blocks publish/export; it is normal "
                    "MID-EDIT (a sentence cut to be moved) and only matters "
                    "when shipping" if bad else ""}


TOOLS = [
    {"name": "list_reports", "fn": t_list_reports,
     "description": "List every report the running docsync editor serves.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "status", "fn": t_status,
     "description": "Build state for one report: version, unpushed commit count, "
                    "any build error.",
     "inputSchema": {"type": "object", "required": ["project"], "properties": {
         "project": {"type": "string", "description": "report id, e.g. budget-primer"}}}},
    {"name": "inventory", "fn": t_inventory,
     "description": "The whole report as data: every slot's markdown, every source "
                    "with its citation count, the geometry of everything placed, and "
                    "(unless elements=false) every addressable element id. Geometry "
                    "is only stored for placed objects; an unmoved designed element's "
                    "position needs the editor's own docsync.api.inventory().",
     "inputSchema": {"type": "object", "required": ["project"], "properties": {
         "project": {"type": "string"},
         "elements": {"type": "boolean",
                      "description": "include addressable ids (costs a render); "
                                     "default true"}}}},
    {"name": "get_slot", "fn": t_get_slot,
     "description": "One slot's full markdown.",
     "inputSchema": {"type": "object", "required": ["project", "key"], "properties": {
         "project": {"type": "string"},
         "key": {"type": "string", "description": "slot key, e.g. whopays.p1"}}}},
    {"name": "search", "fn": t_search,
     "description": "Find a phrase across slots, sources and text boxes.",
     "inputSchema": {"type": "object", "required": ["project", "query"], "properties": {
         "project": {"type": "string"}, "query": {"type": "string"}}}},
    {"name": "uncited_sources", "fn": t_uncited_sources,
     "description": "Sources nothing cites — these block publishing.",
     "inputSchema": {"type": "object", "required": ["project"], "properties": {
         "project": {"type": "string"}}}},
]
BY_NAME = {t["name"]: t for t in TOOLS}

INSTRUCTIONS = (
    "Read-only access to the reports served by a running docsync draft editor.\n\n"
    "Start with list_reports, then inventory(project) — that one call carries "
    "every slot's markdown, every source, and every addressable element id, "
    "so there is no need to hunt.\n\n"
    "EDITING IS NOT HERE, on purpose. The editor holds the document in memory, "
    "so a write from outside would be overwritten by its next Save with nothing "
    "to see and nothing to undo. To CHANGE a report, drive window.docsync.api "
    "in the open editor (setSlot/place/recolor/batch — every verb is one undo "
    "step). Use these tools to decide WHAT to change."
)


# ------------------------------------------------------------ JSON-RPC

def _send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _result(rid, result) -> None:
    _send({"jsonrpc": "2.0", "id": rid, "result": result})


def _error(rid, code, message) -> None:
    _send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})


def handle(req: dict) -> None:
    method, rid = req.get("method"), req.get("id")
    params = req.get("params") or {}
    # A notification has no id and must draw no reply at all — answering one
    # is a protocol error, not a harmless extra.
    if method == "initialize":
        asked = params.get("protocolVersion")
        return _result(rid, {
            "protocolVersion": asked if isinstance(asked, str) and asked else PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "docsync-primer", "version": "1.0.0"},
            "instructions": INSTRUCTIONS,
        })
    if method in ("notifications/initialized", "notifications/cancelled"):
        return
    if method == "ping":
        return _result(rid, {})
    if method == "tools/list":
        return _result(rid, {"tools": [
            {k: t[k] for k in ("name", "description", "inputSchema")} for t in TOOLS]})
    if method == "tools/call":
        name = params.get("name")
        spec = BY_NAME.get(name)
        if spec is None:
            return _error(rid, -32602, f"unknown tool '{name}'")
        args = params.get("arguments") or {}
        missing = [k for k in spec["inputSchema"].get("required", []) if k not in args]
        if missing:
            return _error(rid, -32602, f"{name}: missing {', '.join(missing)}")
        try:
            out = spec["fn"](args)
        except Exception as e:                                  # noqa: BLE001
            out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        # isError marks a FAILED call the model should read and react to,
        # rather than a transport fault — the payload still travels either way.
        return _result(rid, {
            "content": [{"type": "text", "text": json.dumps(out, indent=2)}],
            "isError": not out.get("ok", True),
        })
    if rid is not None:
        _error(rid, -32601, f"unknown method '{method}'")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            _error(None, -32700, "parse error")
            continue
        try:
            handle(req)
        except Exception as e:                                  # noqa: BLE001
            _error(req.get("id"), -32603, f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
