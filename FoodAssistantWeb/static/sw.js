const CACHE = 'yemek-asistani-v4';
const STATIC_ASSETS = ['/static/styles.css?v=4', '/static/app.js?v=4', '/manifest.json'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);

  // HTML her zaman ağdan — eski arayüz önbelleğe alınmasın
  if (e.request.mode === 'navigate' || url.pathname === '/') {
    e.respondWith(fetch(e.request));
    return;
  }

  // API istekleri önbelleğe alınmasın
  const apiPrefixes = ['/chat', '/search', '/recipe', '/favorites', '/plan', '/preferences', '/my-recipes'];
  if (apiPrefixes.some(p => url.pathname.startsWith(p))) return;

  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
