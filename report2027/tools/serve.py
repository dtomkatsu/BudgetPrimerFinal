#!/usr/bin/env python3
"""Local live-editing server for the Budget Primer.

The loop this exists for: edit the report — by hand in content.md / layout.json,
or by asking Claude to — and see it in the browser in about a second. No commit,
no CI wait. When you press Save in the draft editor, the files are written and
pushed; GitHub Pages deploys.

    make -C report2027 live          # http://localhost:8010/primer/edit.html

Local-first: the files on disk are the single source of truth. The editor served
from here reads and writes THEM (not the GitHub API), and a watcher rebuilds the
preview whenever anything changes — so your edits and Claude's land in the same
place and show up together. Stdlib only; nothing to install.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
PORT = int(os.environ.get("PRIMER_PORT", "8010"))
BUILD = ["make", "-C", "report2027", "pub"]      # the one build command
# What a rebuild depends on. A change to any of these re-renders the report and
# re-stages the editor; globs so a new tool or engine file is caught too.
WATCH = [
    "report2027/content.md", "report2027/layout.json",
    "report2027/tools/*.py", "report2027/web/primer.css", "report2027/web/primer.js",
    "report2027/data/*.json", "report2027/manual/*.json",
    "docsync/*.py", "docsync/editor/edit.html",
    "docs/js/departments_act175_fy2027.json", "docs/js/historical_trends.json",
]
# The two files the editor edits, and the branch the save endpoint pushes to.
CONTENT = ROOT / "report2027" / "content.md"
LAYOUT = ROOT / "report2027" / "layout.json"
DEPLOY_BRANCH = "main"

# ---- shared build state, guarded by one lock -----------------------------
_lock = threading.Lock()
_cond = threading.Condition()
_version = 0                    # bumps on every successful rebuild
_error = None                  # last build error, or None
_mtimes: dict[str, float] = {}


def _snapshot() -> dict:
    out = {}
    for pat in WATCH:
        for p in glob.glob(str(ROOT / pat)):
            try:
                out[p] = os.path.getmtime(p)
            except OSError:
                pass
    return out


def rebuild(reason: str = "") -> None:
    """Run the one build command; record the version and any error, then wake
    every connected browser. Serialised, so a save and the watcher never build
    over each other."""
    global _version, _error, _mtimes
    with _lock:
        r = subprocess.run(BUILD, cwd=ROOT, capture_output=True, text=True)
        _mtimes = _snapshot()          # AFTER the build, so its own writes do
        if r.returncode == 0:          # not look like a fresh change
            _version += 1
            _error = None
            print(f"  rebuilt ({reason or 'change'}) -> v{_version}")
        else:
            _error = (r.stdout + r.stderr).strip()[-3000:]
            print(f"  BUILD FAILED ({reason}):\n{_error}")
    with _cond:
        _cond.notify_all()


def watcher():
    global _mtimes
    _mtimes = _snapshot()
    while True:
        time.sleep(0.4)
        now = _snapshot()
        if now != _mtimes:
            rebuild("watch")


# ---- the server ----------------------------------------------------------
RELOAD_JS = """
<script>
(function(){
  var last;
  var banner;
  function show(msg){
    if(!banner){ banner=document.createElement('div');
      banner.style.cssText='position:fixed;left:0;right:0;bottom:0;z-index:2147483647;'
        +'background:#8a2b1e;color:#fff;font:12px/1.5 ui-monospace,monospace;'
        +'white-space:pre-wrap;padding:10px 14px;max-height:45vh;overflow:auto;'
        +'box-shadow:0 -6px 24px rgba(0,0,0,.3)';
      document.body.appendChild(banner); }
    banner.textContent='build failed — the preview is the last good version\\n\\n'+msg;
  }
  function clear(){ if(banner){ banner.remove(); banner=null; } }
  try{
    var es=new EventSource('/__events');
    es.onmessage=function(e){
      var d=JSON.parse(e.data||'{}');
      if(d.error){ show(d.error); return; }
      clear();
      if(last===undefined){ last=d.v; return; }
      if(d.v!==last) location.reload();
    };
  }catch(e){}
})();
</script>
"""


class Handler(SimpleHTTPRequestHandler):
    # HTTP/1.1, so the event stream stays a persistent connection. Under the
    # 1.0 default a browser treats the SSE response as a finished short reply
    # and never receives another event — which looked like "I had to reload".
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(DOCS), **k)

    def log_message(self, *a):        # quiet: only the rebuild lines matter
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/__ping":
            return self._json(200, {"ok": True, "v": _version})
        if self.path.split("?")[0] == "/__events":
            return self._sse()
        # Inject the live-reloader into served pages — except the editor, which
        # handles change events itself so it can keep your unsaved edits.
        clean = self.path.split("?")[0]
        if clean.endswith(".html") and not clean.endswith("edit.html"):
            return self._inject(clean)
        return super().do_GET()

    def _inject(self, clean):
        f = DOCS / clean.lstrip("/")
        if not f.is_file():
            return super().do_GET()
        html = f.read_text(errors="replace")
        html = (html.replace("</body>", RELOAD_JS + "</body>", 1)
                if "</body>" in html else html + RELOAD_JS)
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        seen = None
        try:
            while True:
                with _cond:
                    _cond.wait_for(lambda: _version != seen or _error is not None,
                                   timeout=20)
                    v, err = _version, _error
                # A heartbeat keeps proxies from closing an idle stream.
                payload = {"v": v} if not err else {"v": v, "error": err}
                self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
                self.wfile.flush()
                seen = v
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if self.path.split("?")[0] != "/__save":
            return self._json(404, {"ok": False, "error": "unknown endpoint"})
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError as e:
            return self._json(400, {"ok": False, "error": f"bad request: {e}"})
        try:
            msg = self._save(req)
            return self._json(200, {"ok": True, "message": msg, "v": _version})
        except Exception as e:                       # noqa: BLE001 — report it
            return self._json(200, {"ok": False, "error": str(e)})

    def _save(self, req) -> str:
        """Write what changed to disk, rebuild, and push. Local git credentials
        do the push, so no token lives in the browser."""
        wrote = []
        if req.get("content") is not None:
            CONTENT.write_text(req["content"]); wrote.append("content.md")
        if req.get("layout") is not None:
            LAYOUT.write_text(req["layout"]); wrote.append("layout.json")
        if not wrote:
            return "nothing to save"
        rebuild("save")                              # so the built page is current
        if _error:
            raise RuntimeError("the draft does not build — nothing was pushed:\n" + _error)
        # Commit ONLY these paths — never whatever else happens to be staged.
        # A path-scoped commit ignores the rest of the index, so an unrelated
        # `git add` elsewhere can never ride along on a Save.
        paths = ["report2027/content.md", "report2027/layout.json",
                 "report2027/web/index.html", "report2027/web/primer.css",
                 "docs/primer"]
        if subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--",
                           *paths]).returncode == 0:
            return "already up to date"
        _git("commit", "-m", "primer: edit from the live editor (" + ", ".join(wrote) + ")",
             "--", *paths)
        _git("push", "origin", "HEAD")                       # this branch
        _git("push", "origin", f"HEAD:{DEPLOY_BRANCH}")      # -> deploy
        return "pushed — GitHub Pages deploys in about a minute"


def _git(*args):
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed:\n{(r.stdout + r.stderr).strip()[-1500:]}")


def main():
    rebuild("startup")
    threading.Thread(target=watcher, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}/primer/edit.html"
    print(f"\n  Budget Primer — live at {url}")
    print(f"  editing report2027/content.md + report2027/layout.json")
    print(f"  Save in the editor writes those files and pushes to {DEPLOY_BRANCH}.\n")
    if os.environ.get("PRIMER_OPEN", "1") == "1":
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")


if __name__ == "__main__":
    main()
