/**
 * App shell cache for the draft editor.
 *
 * Three tiers, because "cache everything" would go stale silently and
 * "cache nothing" would refetch Pyodide's ~30MB runtime on every visit:
 *
 * 1. Pyodide's CDN (cdn.jsdelivr.net/pyodide/<version>/…) — cache-first,
 *    forever. The version is IN the URL, so a pin never goes stale; a Pyodide
 *    upgrade is a new URL, which is simply a cache miss the first time.
 * 2. This app's own shell, split by what staleness costs:
 *    - The HTML pages (edit.html, start.html) — NETWORK-FIRST, cache as the
 *      offline fallback. These carried stale-while-revalidate at first, and
 *      it was a bug factory: the file changes daily, so every single visit
 *      ran the PREVIOUS build — fixes looked unshipped, and "clear the
 *      caches" nuked the Pyodide store alongside it, forcing a ~40MB
 *      refetch that read as the whole app hanging. A local dev server makes
 *      the network hit free; deployed, one round-trip per open is nothing
 *      against running week-old code.
 *    - Icons and the manifest — stale-while-revalidate. They change rarely
 *      and a stale icon costs nothing.
 * 3. Everything that is actual report data or a write (engine/*, the GitHub
 *    API, drafts) — network-only. Caching a stale content.md would make a
 *    collaborator's real edit invisible; that failure mode is worse than
 *    "the editor needs a connection to open a report."
 *
 * Bump CACHE_VERSION on any shell change that should evict old entries
 * outright rather than wait for revalidation (e.g. a renamed file).
 */
const CACHE_VERSION = 'primer-shell-v2';
const PYODIDE_CACHE = 'primer-pyodide-v1';

const SHELL_FILES = [
  './start.html',
  './edit.html',
  './manifest.webmanifest',
  './icons/icon.svg',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then(cache => cache.addAll(SHELL_FILES))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_VERSION && k !== PYODIDE_CACHE)
          .map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

const isPyodide = url => url.hostname === 'cdn.jsdelivr.net' && url.pathname.includes('/pyodide/');

// Never cache: report content, layout, the renderer's own data files, any
// GitHub call, or — importantly — index.html itself. That file is not part
// of this app; it is the PUBLISHED, publicly readable report (built by CI
// from content.md), served from the very same directory as the editor. A
// reader who never opened the editor never registers this worker, but anyone
// who DID (this scope is the whole docs/primer/ directory) would otherwise
// have the worker intercept their next visit to the report page too — a
// stale copy of what a reader actually came here to read is a much worse
// failure than "the app shell recaches its own five files."
// The app's own pages: fresh wins, cache is the offline fallback (tier 2).
const isShellPage = url => /\/(edit|start)\.html$/.test(url.pathname);

const isNetworkOnly = url =>
  url.hostname === 'api.github.com' ||
  url.hostname === 'raw.githubusercontent.com' ||
  /\/engine\//.test(url.pathname) ||
  /\/projects\.json$/.test(url.pathname) ||
  /\/primer\/(index\.html)?$/.test(url.pathname);

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;              // writes always hit the network directly
  const url = new URL(req.url);

  if (isPyodide(url)) {
    event.respondWith(
      caches.open(PYODIDE_CACHE).then(async cache => {
        const hit = await cache.match(req);
        if (hit) return hit;
        const res = await fetch(req);
        if (res.ok) cache.put(req, res.clone());
        return res;
      })
    );
    return;
  }

  if (isNetworkOnly(url)) return;                 // let the browser handle it untouched

  if (url.origin === location.origin) {
    event.respondWith(
      caches.open(CACHE_VERSION).then(async cache => {
        const hit = await cache.match(req);
        const network = fetch(req).then(res => {
          if (res.ok) cache.put(req, res.clone());
          return res;
        }).catch(() => hit);                      // offline: fall back to what we had
        // Pages wait for the network so a deploy is live on the very next
        // open; everything else boots from cache and revalidates behind.
        return isShellPage(url) ? network : (hit || network);
      })
    );
  }
});
