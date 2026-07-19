/**
 * App shell cache for the draft editor.
 *
 * Three tiers, because "cache everything" would go stale silently and
 * "cache nothing" would refetch Pyodide's ~30MB runtime on every visit:
 *
 * 1. Pyodide's CDN (cdn.jsdelivr.net/pyodide/<version>/…) — cache-first,
 *    forever. The version is IN the URL, so a pin never goes stale; a Pyodide
 *    upgrade is a new URL, which is simply a cache miss the first time.
 * 2. This app's own shell (this page, the editor, its CSS/icons/manifest) —
 *    stale-while-revalidate. Boots instantly from cache; a newer deploy is
 *    fetched in the background and used on the NEXT load, never blocking
 *    this one.
 * 3. Everything that is actual report data or a write (engine/*, the GitHub
 *    API, drafts) — network-only. Caching a stale content.md would make a
 *    collaborator's real edit invisible; that failure mode is worse than
 *    "the editor needs a connection to open a report."
 *
 * Bump CACHE_VERSION on any shell change that should evict old entries
 * outright rather than wait for revalidation (e.g. a renamed file).
 */
const CACHE_VERSION = 'primer-shell-v1';
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
        return hit || network;
      })
    );
  }
});
