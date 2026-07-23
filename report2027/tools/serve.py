#!/usr/bin/env python3
"""Local live-editing server for docsync reports — project-aware.

    make -C report2027 live          # http://localhost:8010/primer/start.html

The loop this exists for: edit a report — by hand in content.md / layout.json,
or by asking Claude to — and see it in the browser in about a second. No
commit, no CI wait. Save in the draft editor writes the files and commits
LOCALLY; Push is a separate, explicit step that sends it to GitHub, so a save
can never surprise-trigger a deploy or a GitHub Actions run.

Local-first: the files on disk are the single source of truth. The editor
served from here reads and writes THEM (not the GitHub API), and a watcher
rebuilds each project's preview whenever its own files change — so your edits
and Claude's land in the same place and show up together. Stdlib only, except
PyYAML for docsync.yml (already required by docsync.registry).

One process, many projects, possibly many repos: this repo's own docsync.yml
(rxkids, demo-report, and this repo's own budget-primer test fixture) is
always available; `docs/primer/projects.json` — the same registry start.html
reads for its grid — can additionally name a project whose real files live in
a DIFFERENT repo on disk (an optional "local_root"), so a live server always
launched from here can still edit, say, the real Budget Primer content that
lives in ~/BudgetPrimerFinal. Everything below is keyed by project id; there
is no more one global ROOT/CONTENT/LAYOUT — see PROJECTS.
"""
from __future__ import annotations

import glob
import importlib.util
import io
import json
import mimetypes
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SELF_ROOT = Path(__file__).resolve().parents[2]   # this repo — wherever serve.py lives
DOCS = SELF_ROOT / "docs"           # shared UI + any project staged directly under this repo
# The report is a Chrome-printed PDF; export reuses the same engine. Override
# with CHROME_BIN on a non-mac host.
CHROME = os.environ.get("CHROME_BIN") or \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = int(os.environ.get("PRIMER_PORT", "8010"))


# ---- project registry: which report lives in which repo -------------------
def _load_bindings(repo_root: Path) -> dict:
    """Import repo_root's OWN vendored docsync.registry so every path resolves
    against THAT repo, not this one. Each repo carries its own copy of
    docsync/registry.py (see CLAUDE.md's vendoring rule); its module-level
    ROOT is baked to wherever that file physically lives, so importing it
    from its real location — rather than reading its yml with OUR copy — is
    what makes a foreign repo's Binding.content etc. come out correct."""
    reg_file = repo_root / "docsync" / "registry.py"
    if not reg_file.is_file():
        return {}
    mod_name = f"_docsync_registry_{abs(hash(str(repo_root)))}"
    spec = importlib.util.spec_from_file_location(mod_name, reg_file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    try:
        return {b.id: b for b in mod.load_registry()}
    except mod.RegistryError as e:
        print(f"  ({repo_root.name}: {e})")
        return {}


def _load_projects() -> dict:
    """id -> {root, binding}. The registry (projects.json) always lives in,
    and is read from, THIS repo (see the comment in start.html) — the one
    list of every project this server's grid shows, whatever repo each
    project's files actually live in (an entry's optional "local_root" names
    it; absent means it lives right here, alongside serve.py itself)."""
    projects = {}
    self_bindings = _load_bindings(SELF_ROOT)
    reg_path = DOCS / "primer" / "projects.json"
    registry = json.loads(reg_path.read_text()) if reg_path.is_file() else {}
    for pid, entry in registry.items():
        root = Path(entry["local_root"]).expanduser() if entry.get("local_root") else SELF_ROOT
        bindings = self_bindings if root == SELF_ROOT else _load_bindings(root)
        b = bindings.get(pid)
        if b is None:
            print(f"  (projects.json lists '{pid}' but {root}/docsync.yml has no such binding — skipping)")
            continue
        projects[pid] = {"root": root, "binding": b}
    # A binding in THIS repo's own docsync.yml that projects.json doesn't
    # mention yet still gets served (so a freshly staged report works before
    # anyone remembers to register it) — it just won't appear on the grid.
    for pid, b in self_bindings.items():
        projects.setdefault(pid, {"root": SELF_ROOT, "binding": b})
    return projects


PROJECTS = _load_projects()
DEFAULT_PROJECT = "budget-primer" if "budget-primer" in PROJECTS else next(iter(PROJECTS), None)

# Foreign-repo projects: nothing under THIS server's docs/ tree can reach
# another repo's files on disk, so each gets its own reserved URL prefix,
# mapped straight to that project's own staged editor dir (wherever THAT
# repo's docsync.yml editor.dir put it — e.g. BudgetPrimerFinal/docs/primer).
EXTERNAL_MOUNTS = {
    pid: p["binding"].editor.dir
    for pid, p in PROJECTS.items()
    if p["root"] != SELF_ROOT and p["binding"].editor
}
# The inverse, for SELF-rooted projects: which docs/<name> belongs to which
# project id, so a preview page's live-reload banner (and __ping/__events)
# knows which project's build state to show.
SELF_DIR_TO_PID = {
    p["binding"].editor.dir.name: pid
    for pid, p in PROJECTS.items()
    if p["root"] == SELF_ROOT and p["binding"].editor
}


def _watch_patterns(root: Path, b) -> list[str]:
    """Everything a rebuild of this ONE project should react to: its content/
    layout/renderer/engine files (already absolute — resolved by whichever
    repo's registry produced this Binding), any extra globs docsync.yml named
    under `watch:`, and the shared engine code (docsync/*.py, edit.html) that
    lives alongside it in the SAME repo."""
    pats = [str(b.content)]
    e = b.editor
    if e:
        if e.layout:
            pats.append(str(e.layout))
        pats.append(str(e.render))
        pats.extend(str(f) for f in e.engine)
    pats.extend(str(root / w) for w in b.watch)
    pats.append(str(root / "docsync" / "*.py"))
    pats.append(str(root / "docsync" / "editor" / "edit.html"))
    return pats


class ProjectState:
    """One project's rebuild state — a separate lock/condition per project so
    a slow build in one report never blocks another's Save/Push/watch."""

    def __init__(self):
        self.version = 0
        self.error = None
        self.mtimes: dict[str, float] = {}
        self.lock = threading.Lock()
        self.cond = threading.Condition()


STATE = {pid: ProjectState() for pid in PROJECTS}


def _snapshot(patterns: list[str]) -> dict:
    out = {}
    for pat in patterns:
        for p in glob.glob(pat):
            try:
                out[p] = os.path.getmtime(p)
            except OSError:
                pass
    return out


def _ahead(root: Path) -> int:
    """Commits sitting on this project's repo that origin does not have yet —
    what a Push would send. 0 whenever there is nothing to push, including if
    HEAD has no upstream (a detached checkout) rather than raising."""
    r = subprocess.run(["git", "-C", str(root), "rev-list", "--count", "@{u}..HEAD"],
                        capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return 0


def rebuild(pid: str, reason: str = "") -> None:
    """Run this ONE project's build command; record its version and any
    error, then wake everyone watching it. Serialised per-project, so a save
    and the watcher never build the same report over each other — but two
    DIFFERENT projects rebuild independently and concurrently."""
    p = PROJECTS.get(pid)
    if p is None:
        return
    st, root, b = STATE[pid], p["root"], p["binding"]
    with st.lock:
        if b.build:
            # Run through a shell, not shlex.split — the registry documents
            # `build` as "a shell command", and rxkids/demo-report's actually
            # ARE compound ones (render && re-stage the editor); a plain
            # split-and-exec would pass "&&" as a literal argv token instead
            # of chaining, silently skipping the second command.
            r = subprocess.run(b.build, shell=True, cwd=str(root),
                                capture_output=True, text=True)
            ok, output = r.returncode == 0, r.stdout + r.stderr
        else:
            ok, output = True, ""
        # Guarantee the live editor's staged copy is fresh after ANY rebuild —
        # regardless of whether THIS project's own `build:` remembers to
        # re-stage. budget-primer's Makefile chain does; rxkids/demo-report
        # originally didn't, which silently left the editor showing stale
        # content while `build` "succeeded". Idempotent (docsync.stage just
        # copies declared files) and safe to run unconditionally: it preserves
        # whatever --repo a human already set (see stage.py), so this can't
        # un-link a project from the repo it pushes to. This is what makes the
        # live-reload loop correct for EVERY docsync.yml-registered project —
        # one freshly authored here, or one pointed at via a projects.json
        # local_root — without relying on each one's own build: string.
        if ok and b.editor:
            sr = subprocess.run(["python3", "-m", "docsync.stage", "--id", pid],
                                 cwd=str(root), capture_output=True, text=True)
            if sr.returncode != 0:
                ok, output = False, output + "\n[re-stage]\n" + sr.stdout + sr.stderr
        st.mtimes = _snapshot(_watch_patterns(root, b))   # AFTER the build, so
        if ok:                                            # its own writes don't
            st.version += 1                               # look like a fresh change
            st.error = None
            print(f"  [{pid}] rebuilt ({reason or 'change'}) -> v{st.version}")
        else:
            st.error = output.strip()[-3000:]
            print(f"  [{pid}] BUILD FAILED ({reason}):\n{st.error}")
    with st.cond:
        st.cond.notify_all()


def watcher():
    patterns = {pid: _watch_patterns(p["root"], p["binding"]) for pid, p in PROJECTS.items()}
    for pid in PROJECTS:
        STATE[pid].mtimes = _snapshot(patterns[pid])
    while True:
        time.sleep(0.4)
        for pid in PROJECTS:
            now = _snapshot(patterns[pid])
            if now != STATE[pid].mtimes:
                rebuild(pid, "watch")


# ---- the server -------------------------------------------------------------
# %%PID%% is replaced per-response with the project id the served page belongs
# to (or "" when none applies, e.g. start.html) — every fetch/localStorage key
# below is scoped by it so two different projects' preview tabs, open at once,
# never elect a shared leader or react to each other's rebuilds.
RELOAD_JS = """
<script>
(function(){
  var PID = %%PID%%;
  var QS = PID ? ('?project=' + encodeURIComponent(PID)) : '';
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
  function apply(d){
    if(!d) return;
    if(d.error){ show(d.error); return; }
    clear();
    if(last===undefined){ last=d.v; return; }
    if(d.v!==last) location.reload();
  }
  // ONE connection for ALL preview tabs OF THE SAME PROJECT. Each tab opening
  // its own SSE piled them up against Chromium's six-per-origin cap, and
  // stale tabs then deadlocked the whole origin. The tabs elect a single
  // LEADER (a heartbeat lock in localStorage) that holds the only /__events
  // stream and relays each event to the rest through localStorage — a
  // `storage` event fires in every OTHER tab. Followers hold no connection.
  var LK='primer-preview-leader:'+PID, EV='primer-preview-event:'+PID;
  var HB=2000, STALE=6000;
  var me=Math.random().toString(36).slice(2)+Date.now().toString(36);
  var es=null, leading=false, hb=0, evN=0;
  function relay(d){ try{ localStorage.setItem(EV, JSON.stringify({v:d.v, error:d.error, _n:(++evN)+'.'+Date.now()})); }catch(e){} }
  function setLock(){ try{ localStorage.setItem(LK, JSON.stringify({id:me,t:Date.now()})); }catch(e){} }
  function readLock(){ try{ return JSON.parse(localStorage.getItem(LK)||'null'); }catch(e){ return null; } }
  function onmsg(e){ var d={}; try{ d=JSON.parse(e.data||'{}'); }catch(x){} apply(d); relay(d); }
  function openStream(){ if(es) return; try{ es=new EventSource('/__events'+QS); es.onmessage=onmsg; }catch(e){} }
  function stopLeading(){ leading=false; if(es){ es.close(); es=null; } if(hb){ clearInterval(hb); hb=0; } }
  function startLeading(){ setLock(); if(leading) return; leading=true; openStream();
    hb=setInterval(function(){ setLock();
      fetch('/__ping'+QS,{cache:'no-store'}).then(function(r){return r.json();}).then(function(d){ apply(d); relay(d); }).catch(function(){}); }, HB); }
  function elect(){ if(document.hidden){ stopLeading(); return; }
    var lk=readLock();
    if(!lk || Date.now()-lk.t>=STALE || lk.id===me) startLeading(); else stopLeading(); }
  function catchUpOnce(){ fetch('/__ping'+QS,{cache:'no-store'}).then(function(r){return r.json();}).then(apply).catch(function(){}); }
  window.addEventListener('storage', function(e){ if(e.key===EV && !leading && e.newValue){ try{ apply(JSON.parse(e.newValue)); }catch(x){} } });
  document.addEventListener('visibilitychange', function(){ elect(); if(!document.hidden && !leading) catchUpOnce(); });
  window.addEventListener('pagehide', function(){ var lk=readLock(); if(lk && lk.id===me){ try{ localStorage.removeItem(LK); }catch(e){} } stopLeading(); });
  elect(); setInterval(elect, HB);
  if(!document.hidden) catchUpOnce();
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
        parsed = urlparse(self.path)
        clean = parsed.path
        pid = (parse_qs(parsed.query).get("project") or [None])[0]
        if clean == "/__ping":
            return self._json(200, self._ping_payload(pid))
        if clean == "/__events":
            return self._sse(pid)
        for mpid, mount_dir in EXTERNAL_MOUNTS.items():
            prefix = f"/_repo-{mpid}/"
            if clean == prefix[:-1] or clean.startswith(prefix):
                rel = clean[len(prefix):] or "index.html"
                return self._serve_mounted(mount_dir, rel, mpid)
        # Inject the live-reloader into served pages — except the editor, which
        # handles change events itself so it can keep your unsaved edits.
        if clean.endswith(".html") and not clean.endswith("edit.html"):
            return self._inject(clean)
        return super().do_GET()

    def _ping_payload(self, pid: str | None) -> dict:
        if pid not in STATE:
            return {"ok": True, "v": 0, "ahead": 0}
        st = STATE[pid]
        payload = {"ok": True, "v": st.version, "ahead": _ahead(PROJECTS[pid]["root"])}
        if st.error:
            payload["error"] = st.error
        return payload

    def _reload_script(self, pid: str | None) -> str:
        return RELOAD_JS.replace("%%PID%%", json.dumps(pid or ""))

    def _inject(self, clean):
        f = DOCS / clean.lstrip("/")
        if not f.is_file():
            return super().do_GET()
        html = f.read_text(errors="replace")
        pid = SELF_DIR_TO_PID.get(clean.lstrip("/").split("/", 1)[0])
        # rpartition, not the first "</body>": start.html's new-report flow
        # builds a whole starter report as a JS template literal, which
        # contains its OWN literal "</body>" long before the page's real
        # closing tag. Replacing the first occurrence spliced a live
        # <script> block into the middle of that JS string and corrupted the
        # page's syntax ("Unexpected end of input") — the last occurrence is
        # always the actual closing tag.
        script = self._reload_script(pid)
        if "</body>" in html:
            head, sep, tail = html.rpartition("</body>")
            html = head + script + sep + tail
        else:
            html = html + script
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_mounted(self, base_dir: Path, rel_path: str, pid: str):
        """Serve a file from ANOTHER repo's staged editor dir, mounted at
        /_repo-<id>/ — the counterpart to SimpleHTTPRequestHandler's default
        serving of THIS repo's own DOCS tree."""
        try:
            f = (base_dir / rel_path).resolve()
            f.relative_to(base_dir.resolve())    # guard against a ../ escape
        except (ValueError, OSError):
            return self._json(404, {"ok": False, "error": "not found"})
        if not f.is_file():
            return self._json(404, {"ok": False, "error": "not found"})
        if f.suffix == ".html" and f.name != "edit.html":
            html = f.read_text(errors="replace")
            script = self._reload_script(pid)
            if "</body>" in html:
                head, sep, tail = html.rpartition("</body>")
                html = head + script + sep + tail
            else:
                html += script
            body, ctype = html.encode(), "text/html; charset=utf-8"
        else:
            body = f.read_bytes()
            ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _sse(self, pid: str | None):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        st = STATE.get(pid)
        root = PROJECTS[pid]["root"] if pid in PROJECTS else None
        seen = None
        # A stream LEASE, not a lifetime. A zombie holder — a discarded tab or
        # a hung worker context the browser never quite kills — can sit on an
        # open stream forever, ACKing heartbeats, pinning one of the browser's
        # six per-origin sockets. Six of those and the origin is dead: every
        # new load queues behind sockets that never free ("localhost won't
        # load", server perfectly healthy). Ending the response after a bounded
        # window returns the socket no matter what; a LIVE client's EventSource
        # auto-reconnects in ~3s (and the leader's poll covers the gap), while
        # a zombie's held socket simply expires. Starvation becomes transient
        # instead of permanent — self-healing regardless of client bugs.
        deadline = time.time() + 45
        try:
            if st is None:
                time.sleep(min(45, deadline - time.time()))
                return
            while time.time() < deadline:
                with st.cond:
                    st.cond.wait_for(lambda: st.version != seen or st.error is not None,
                                      timeout=min(20, max(0.1, deadline - time.time())))
                    v, err = st.version, st.error
                # A heartbeat keeps proxies from closing an idle stream. ahead
                # rides along so a Save elsewhere (another tab, another Claude
                # session) updates every open editor's Push button too.
                payload = {"v": v, "ahead": _ahead(root)}
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
        pid = req.get("project") or DEFAULT_PROJECT
        if pid not in PROJECTS:
            return self._json(200, {"ok": False, "error": f"unknown project '{pid}'"})
        try:
            msg = self._push(pid) if path == "/__push" else self._save(pid, req)
            return self._json(200, {"ok": True, "message": msg, "v": STATE[pid].version,
                                     "ahead": _ahead(PROJECTS[pid]["root"])})
        except Exception as e:                       # noqa: BLE001 — report it
            return self._json(200, {"ok": False, "error": str(e),
                                     "ahead": _ahead(PROJECTS[pid]["root"])})

    # ---- export: render the editor's CURRENT draft to a file and stream it ---
    # The editor posts its in-memory content + layout, so you download exactly
    # what is on screen — unsaved edits and all — without a Save (which commits)
    # and without touching content.md / layout.json. render_report.py takes the
    # draft from temp files via DOCSYNC_CONTENT/LAYOUT and writes a throwaway
    # HTML next to the project's own published output (so its relative
    # css/js/assets links resolve); Chrome then prints or screenshots it
    # exactly as the project's own `make pdf`-equivalent would.
    def _export(self, req):
        pid = req.get("project") or DEFAULT_PROJECT
        p = PROJECTS.get(pid)
        if p is None:
            return self._json(400, {"ok": False, "error": f"unknown project '{pid}'"})
        root, b = p["root"], p["binding"]
        if not b.editor:
            return self._json(400, {"ok": False, "error": f"'{pid}' has no editor"})
        fmt = (req.get("fmt") or "pdf").lower()
        if fmt not in ("pdf", "png"):
            return self._json(400, {"ok": False, "error": "fmt must be pdf or png"})
        content, layout = req.get("content"), req.get("layout")
        if content is None or layout is None:
            return self._json(400, {"ok": False, "error": "content and layout required"})
        marks = bool(req.get("marks"))
        work = Path(tempfile.mkdtemp(prefix="primer-exp-"))
        token = work.name.rsplit("-", 1)[-1]
        out_html = b.editor.out.parent / f"__export-{token}.html"   # must live
        try:                                                        # beside the
            (work / "content.md").write_text(content)                # project's own
            (work / "layout.json").write_text(layout)                 # output for
            env = dict(os.environ)                                    # its assets
            env["DOCSYNC_CONTENT"] = str(work / "content.md")
            env["DOCSYNC_LAYOUT"] = str(work / "layout.json")
            env["DOCSYNC_OUT"] = str(out_html)
            env.pop("DOCSYNC_EDIT", None)             # publish mode, not edit mode
            if marks and fmt == "pdf":
                env["DOCSYNC_MARKS"] = "1"
            r = subprocess.run(["python3", str(b.editor.render)], cwd=str(root),
                               env=env, capture_output=True, text=True)
            if r.returncode != 0:
                tail = (r.stdout + r.stderr).strip()[-2000:]
                return self._json(200, {"ok": False,
                                        "error": "the draft does not build:\n" + tail})
            if fmt == "pdf":
                data = self._chrome_pdf(out_html)
                return self._bytes(200, "application/pdf", data, f"{pid}.pdf")
            npages = out_html.read_text().count('<section class="page')
            data = self._chrome_png_zip(out_html, npages, pid)
            return self._bytes(200, "application/zip", data, f"{pid}-pages.zip")
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

    def _chrome_png_zip(self, out_html, npages, slug: str) -> bytes:
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
                        z.write(png, f"{slug}-page-{i:02d}.png")
                finally:
                    shutil.rmtree(prof, ignore_errors=True)
        return buf.getvalue()

    def _save(self, pid: str, req) -> str:
        """Write what changed to disk, rebuild, and commit LOCALLY. Never
        pushes on its own — that is a separate, explicit action (_push) the
        editor's Push button asks for, so a save can never surprise-trigger a
        GitHub Actions run (build.yml watches for pushes to main) or race a
        push you were not ready to make yet."""
        p = PROJECTS[pid]
        root, b = p["root"], p["binding"]
        wrote = []
        if req.get("content") is not None:
            b.content.write_text(req["content"]); wrote.append(b.content.name)
        if req.get("layout") is not None and b.editor and b.editor.layout:
            b.editor.layout.write_text(req["layout"]); wrote.append(b.editor.layout.name)
        if not wrote:
            return "nothing to save"
        rebuild(pid, "save")                          # so the built page is current
        if STATE[pid].error:
            raise RuntimeError("the draft does not build — nothing was saved:\n" + STATE[pid].error)
        # Commit ONLY these paths — never whatever else happens to be staged.
        # A path-scoped commit ignores the rest of the index, so an unrelated
        # `git add` elsewhere can never ride along on a Save.
        paths = [str(b.content.relative_to(root))]
        if b.editor and b.editor.layout:
            paths.append(str(b.editor.layout.relative_to(root)))
        paths.extend(b.outputs)
        if b.editor:
            paths.append(str(b.editor.dir.relative_to(root)))
        if subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--",
                           *paths]).returncode == 0:
            return "already up to date"
        _git(root, "commit", "-m", f"{pid}: edit from the live editor (" + ", ".join(wrote) + ")",
             "--", *paths)
        return "saved locally — Push when you're ready to publish"

    def _push(self, pid: str) -> str:
        """Send whatever is committed locally (one Save, or several) to
        GitHub: the current branch, and fast-forward the deploy branch to
        match. Two separate remote refs, so either can independently reject a
        non-fast-forward — most commonly build.yml's own bot commit landing on
        the deploy branch between saves — and that failure is reported plainly
        rather than as raw git stderr, since the fix (ask for a reconcile) is
        the same every time."""
        p = PROJECTS[pid]
        root = p["root"]
        branch = (p["binding"].editor.branch if p["binding"].editor else "main") or "main"
        try:
            _git(root, "push", "origin", "HEAD")                     # this branch
            _git(root, "push", "origin", f"HEAD:{branch}")           # -> deploy
        except RuntimeError as e:
            if "rejected" in str(e) or "fetch first" in str(e):
                raise RuntimeError(
                    "push rejected — the remote has commits this machine doesn't "
                    "(often build.yml's own rebuild). Ask Claude to reconcile it, "
                    "or run: git fetch && git merge origin/" + branch) from e
            raise
        return "pushed — GitHub Pages deploys in about a minute"


def _git(root: Path, *args, timeout=45):
    # A detached dev server has no terminal and no GUI session to answer a
    # credential prompt, so a git that decides to ASK — a first push before the
    # keychain has cached anything, an unreachable remote — would hang the push
    # AND the editor's spinner forever. Force non-interactive and cap the wait:
    # a missing credential or dead network now fails in seconds with a message
    # you can act on. A credential already in the keychain is still used without
    # a prompt, so a push that worked keeps working.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0",
           "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=10"}
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                           text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"git {args[0]} timed out after {timeout}s — the remote didn't answer, "
            "or a credential prompt had no terminal to answer it. Run the push once "
            "in your own terminal so the keychain caches the credential, then retry.")
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed:\n{(r.stdout + r.stderr).strip()[-1500:]}")


class _IPv6Server(ThreadingHTTPServer):
    # macOS resolves `localhost` to BOTH 127.0.0.1 and ::1, and per RFC 6724 a
    # browser tries ::1 FIRST. Binding IPv4 only left ::1:PORT dead, so Chrome/
    # Safari stalled on the IPv6 attempt while curl (which picked IPv4) worked —
    # the classic "curl loads it, the browser spins" split. We listen on BOTH
    # loopback addresses so it doesn't matter which the browser picks.
    address_family = socket.AF_INET6


def _serve_forever(servers):
    """serve_forever on the first socket in the calling thread, the rest in
    daemon threads. All share one Handler, so a Save/Push on either family hits
    the same build state."""
    for s in servers[1:]:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    servers[0].serve_forever()


def main():
    if not PROJECTS:
        print("  no projects found — check docsync.yml and docs/primer/projects.json")
    for pid in PROJECTS:
        rebuild(pid, "startup")
    threading.Thread(target=watcher, daemon=True).start()
    # Two loopback listeners (IPv4 + IPv6), NOT a dual-stack `::` bind — the save/
    # push/export endpoints must stay off the LAN. If IPv6 loopback is somehow
    # unavailable, fall back to IPv4-only rather than refuse to start.
    servers = [ThreadingHTTPServer(("127.0.0.1", PORT), Handler)]
    try:
        servers.append(_IPv6Server(("::1", PORT), Handler))
    except OSError as e:
        print(f"  (IPv6 loopback unavailable: {e}; serving IPv4 only)")
    url = f"http://localhost:{PORT}/primer/start.html"
    print(f"\n  Primer editor — live at {url}")
    for pid, p in sorted(PROJECTS.items()):
        print(f"    {pid} -> {p['root']}")
    if os.environ.get("PRIMER_OPEN", "1") == "1":
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        _serve_forever(servers)
    except KeyboardInterrupt:
        print("\n  stopped")


if __name__ == "__main__":
    main()
