/**
 * FILE: cmfs/cmfs_frontend/public/sw.js
 * ACTION: CREATE (Phase 8)
 *
 * Hand-written (no build-time workbox/next-pwa step) — deliberately
 * simple: cache the app shell so the Gate Check-In page still loads
 * with no connection, and otherwise stay out of the way entirely.
 *
 * IMPORTANT: this never touches the backend API. Requests to a
 * different origin (NEXT_PUBLIC_API_URL, e.g. localhost:8000) and any
 * non-GET request (every /api/gate/checkin/... call) pass straight
 * through to the network, untouched — the offline queue in
 * pages/gate/index.js is what handles those, not this service worker.
 */

const CACHE_VERSION = 'gate-shell-v1';
const PRECACHE_URLS = [
  '/gate',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) =>
      Promise.all(
        PRECACHE_URLS.map((url) =>
          cache.add(url).catch(() => {
            // Non-fatal — e.g. dev server not up yet at install time.
            // The runtime cache-on-fetch logic below fills this in
            // the first time the page is actually visited online.
          })
        )
      )
    )
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Only ever handle same-origin GET requests. Everything else (the
  // backend API on a different origin, and every POST/PUT/DELETE) is
  // left completely alone.
  if (request.method !== 'GET') return;
  if (new URL(request.url).origin !== self.location.origin) return;

  // Page navigations: network-first, falling back to the cached shell
  // (specifically the /gate app shell) when offline.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => cached || caches.match('/gate'))
        )
    );
    return;
  }

  // Static assets (JS/CSS chunks, icons, etc.): cache-first, refreshing
  // the cache in the background on every successful fetch.
  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => cached);
      return cached || networkFetch;
    })
  );
});
