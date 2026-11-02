/* FreeAmir PWA Service Worker */
const CACHE_VERSION = 'freeamir-v1';
const OFFLINE_URL = '/offline/';
const PRECACHE_URLS = [
  OFFLINE_URL,
  '/static/manifest.json',
  '/static/icons/logo.svg',
  '/static/icons/icon-192.svg',
  '/static/icons/icon-512.svg',
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(PRECACHE_URLS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;
  const isCDN = url.hostname === 'cdn.tailwindcss.com' || url.hostname === 'cdn.jsdelivr.net';
  if (!sameOrigin && !isCDN) return;
  if (request.method !== 'GET') return;
  if (sameOrigin && (url.pathname.startsWith('/admin/') || url.pathname.startsWith('/api/'))) {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  if ((sameOrigin && url.pathname.startsWith('/static/')) || isCDN) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, clone));
          }
          return response;
        }).catch(() => cached);
      })
    );
    return;
  }

  event.respondWith(fetch(request).catch(() => caches.match(request)));
});
