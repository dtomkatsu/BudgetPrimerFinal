#!/usr/bin/env python3
"""Local live-editing server for the Budget Primer.

The loop this exists for: edit the report — by hand in content.md / layout.json,
or by asking Claude to — and see it in the browser in about a second. No commit,
no CI wait. Save in the draft editor writes the files and commits LOCALLY;
Push is a separate, explicit step that sends it to GitHub, so a save can never
surprise-trigger a deploy or a GitHub Actions run.

    make -C report2027 live          # http://localhost:8010/primer/edit.html

Local-first: the files on disk are the single source of truth. The editor served
from here reads and writes THEM (not the GitHub API), and a watcher rebuilds the
preview whenever anything changes — so your edits and Claude's land in the same
place and show up together. Stdlib only; nothing to install.
"""
from __future__ import annotations

import glob
import io
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import webbrowser
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
WEB = ROOT / "report2027" / "web"                 # where index.html + assets live
# The report is a Chrome-printed PDF; export reuses the same engine. Override
# with CHROME_BIN on a non-mac host.
CHROME = os.environ.get("CHROME_BIN") or \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
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
# The two files the editor edits, and the branch _push sends them to.
CONTENT = ROOT / "report2027" / "content.md"
LAYOUT = ROOT / "report2027" / "layout.json"
DEPLOY_BRANCH = "main"

# ---- shared build state, guarded by one lock -----------------------------
_lock = threading.Lock()
_cond = threading.Condition()
_version = 0                    # bumps on every successful rebuild
_error = None                  # last build error, or None
_mtimes: dict[str, float] = {}


def _ahead() -> int:
    """Commits sitting on this machine that origin does not have yet — what a
    Push would send. 0 whenever there is nothing to push, including if HEAD
    has no upstream (a detached checkout) rather than raising."""
    r = subprocess.run(["git", "-C", str(ROOT), "rev-list", "--count", "@{u}..HEAD"],
                        capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return 0


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

    def end_headers(self):
        # Never cache. A rebuild replaces edit.html and the engine files on
        # disk; without this the browser reuses the copy it loaded first and a
        # reload silently shows stale code — exactly the kind of ghost that
        # wastes an afternoon.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):        # quiet: only the rebuild lines matter
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, code, ctype, data, filename):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?")[0] == "/__ping":
            return self._json(200, {"ok": True, "v": _version, "ahead": _ahead()})
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
        # rpartition, not the first "</body>": start.html's new-report flow
        # builds a whole starter report as a JS template literal, which
        # contains its OWN literal "</body>" long before the page's real
        # closing tag. Replacing the first occurrence spliced a live
        # <script> block into the middle of that JS string and corrupted the
        # page's syntax ("Unexpected end of input") — the last occurrence is
        # always the actual closing tag.
        if "</body>" in html:
            head, sep, tail = html.rpartition("</body>")
            html = head + RELOAD_JS + sep + tail
        else:
            html = html + RELOAD_JS
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
                # A heartbeat keeps proxies from closing an idle stream. ahead
                # rides along so a Save elsewhere (another tab, another Claude
                # session) updates every open editor's Push button too.
                payload = {"v": v, "ahead": _ahead()}
                if err:
                    payload["error"] = err
                self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
                self.wfile.flush()
                seen = v
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/__save", "/__push", "/__export"):
            return self._json(404, {"ok": False, "error": "unknown endpoint"})
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError as e:
            return self._json(400, {"ok": False, "error": f"bad request: {e}"})
        if path == "/__export":
            return self._export(req)                 # writes its own response
        try:
            msg = self._push() if path == "/__push" else self._save(req)
            return self._json(200, {"ok": True, "message": msg, "v": _version, "ahead": _ahead()})
        except Exception as e:                       # noqa: BLE001 — report it
            return self._json(200, {"ok": False, "error": str(e), "ahead": _ahead()})

    # ---- export: render the editor's CURRENT draft to a file and stream it ---
    # The editor posts its in-memory content + layout, so you download exactly
    # what is on screen — unsaved edits and all — without a Save (which commits)
    # and without touching content.md / layout.json. render_report.py takes the
    # draft from temp files via DOCSYNC_CONTENT/LAYOUT and writes a throwaway
    # HTML into web/ (so its relative primer.css/js/assets links resolve); Chrome
    # then prints or screenshots it exactly as `make pdf` does.
    def _export(self, req):
        fmt = (req.get("fmt") or "pdf").lower()
        if fmt not in ("pdf", "png"):
            return self._json(400, {"ok": False, "error": "fmt must be pdf or png"})
        content, layout = req.get("content"), req.get("layout")
        if content is None or layout is None:
            return self._json(400, {"ok": False, "error": "content and layout required"})
        marks = bool(req.get("marks"))
        work = Path(tempfile.mkdtemp(prefix="primer-exp-"))
        token = work.name.rsplit("-", 1)[-1]
        out_html = WEB / f"__export-{token}.html"     # must live in web/ for assets
        try:
            (work / "content.md").write_text(content)
            (work / "layout.json").write_text(layout)
            env = dict(os.environ)
            env["DOCSYNC_CONTENT"] = str(work / "content.md")
            env["DOCSYNC_LAYOUT"] = str(work / "layout.json")
            env["DOCSYNC_OUT"] = str(out_html)
            env.pop("DOCSYNC_EDIT", None)             # publish mode, not edit mode
            if marks and fmt == "pdf":
                env["DOCSYNC_MARKS"] = "1"
            r = subprocess.run(["python3", "tools/render_report.py"],
                               cwd=str(ROOT / "report2027"), env=env,
                               capture_output=True, text=True)
            if r.returncode != 0:
                tail = (r.stdout + r.stderr).strip()[-2000:]
                return self._json(200, {"ok": False,
                                        "error": "the draft does not build:\n" + tail})
            if fmt == "pdf":
                data = self._chrome_pdf(out_html)
                return self._bytes(200, "application/pdf", data,
                                   "Budget-Primer-FY2026-27.pdf")
            npages = out_html.read_text().count('<section class="page')
            data = self._chrome_png_zip(out_html, npages)
            return self._bytes(200, "application/zip", data, "Budget-Primer-pages.zip")
        except Exception as e:                        # noqa: BLE001 — report it
            return self._json(200, {"ok": False, "error": str(e)})
        finally:
            try:
                out_html.unlink()
            except OSError:
                pass
            shutil.rmtree(work, ignore_errors=True)

    def _chrome_capture(self, args, out_file, deadline=50.0, settle=2.0) -> bool:
        """Run headless Chrome and return once out_file is fully written.

        This build of Chrome writes the PDF/PNG in a few seconds but then does
        NOT exit under --headless=new, so waiting on the process (subprocess.run)
        hangs forever. We watch the OUTPUT instead: once its size holds steady
        it is done, and we kill the whole process group — main plus the gpu/
        renderer helpers — so nothing lingers between exports."""
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        start, last, held = time.time(), -1, 0.0
        try:
            while time.time() - start < deadline:
                if proc.poll() is not None:       # some versions do self-exit
                    break
                time.sleep(0.4)
                sz = out_file.stat().st_size if out_file.exists() else -1
                if sz > 0 and sz == last:
                    held += 0.4
                    if held >= settle:
                        break
                else:
                    held = 0.0
                last = sz
        finally:
            if proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        proc.kill()
        return out_file.exists() and out_file.stat().st_size > 0

    def _chrome_pdf(self, out_html) -> bytes:
        prof = Path(tempfile.mkdtemp(prefix="primer-chrome-"))
        pdf = prof / "out.pdf"
        try:
            if not self._chrome_capture(
                [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--no-first-run", f"--user-data-dir={prof}",
                 "--virtual-time-budget=12000", "--no-pdf-header-footer",
                 f"--print-to-pdf={pdf}", out_html.resolve().as_uri()],
                pdf, deadline=50, settle=2.0):
                raise RuntimeError("Chrome produced no PDF within the time limit.")
            return pdf.read_bytes()
        finally:
            shutil.rmtree(prof, ignore_errors=True)

    def _chrome_png_zip(self, out_html, npages) -> bytes:
        # One screenshot per page via primer.js's ?only=N isolation; 816x1056 css
        # px = 8.5x11in, doubled for a crisp raster. A fresh profile per page —
        # Chrome is killed, not exited, so a reused profile can hold a lock.
        base = out_html.resolve().as_uri()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i in range(1, max(npages, 1) + 1):
                prof = Path(tempfile.mkdtemp(prefix="primer-chrome-"))
                png = prof / f"page-{i}.png"
                try:
                    if self._chrome_capture(
                        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                         "--no-first-run", f"--user-data-dir={prof}",
                         "--virtual-time-budget=8000", "--hide-scrollbars",
                         "--force-device-scale-factor=2", "--window-size=816,1056",
                         f"--screenshot={png}", f"{base}?only={i}"],
                        png, deadline=30, settle=1.0):
                        z.write(png, f"budget-primer-page-{i:02d}.png")
                finally:
                    shutil.rmtree(prof, ignore_errors=True)
        return buf.getvalue()

    def _save(self, req) -> str:
        """Write what changed to disk, rebuild, and commit LOCALLY. Never
        pushes on its own — that is a separate, explicit action (_push) the
        editor's Push button asks for, so a save can never surprise-trigger a
        GitHub Actions run (build.yml watches for pushes to main) or race a
        push you were not ready to make yet."""
        wrote = []
        if req.get("content") is not None:
            CONTENT.write_text(req["content"]); wrote.append("content.md")
        if req.get("layout") is not None:
            LAYOUT.write_text(req["layout"]); wrote.append("layout.json")
        if not wrote:
            return "nothing to save"
        rebuild("save")                              # so the built page is current
        if _error:
            raise RuntimeError("the draft does not build — nothing was saved:\n" + _error)
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
        return "saved locally — Push when you're ready to publish"

    def _push(self) -> str:
        """Send whatever is committed locally (one Save, or several) to
        GitHub: the current branch, and fast-forward the deploy branch to
        match. Two separate remote refs, so either can independently reject a
        non-fast-forward — most commonly build.yml's own bot commit landing on
        main between saves — and that failure is reported plainly rather than
        as raw git stderr, since the fix (ask for a reconcile) is the same
        every time."""
        try:
            _git("push", "origin", "HEAD")                       # this branch
            _git("push", "origin", f"HEAD:{DEPLOY_BRANCH}")      # -> deploy
        except RuntimeError as e:
            if "rejected" in str(e) or "fetch first" in str(e):
                raise RuntimeError(
                    "push rejected — the remote has commits this machine doesn't "
                    "(often build.yml's own rebuild). Ask Claude to reconcile it, "
                    "or run: git fetch && git merge origin/" + DEPLOY_BRANCH) from e
            raise
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
    print(f"  Save writes those files and commits locally; Push sends it to {DEPLOY_BRANCH}.\n")
    if os.environ.get("PRIMER_OPEN", "1") == "1":
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")


if __name__ == "__main__":
    main()
