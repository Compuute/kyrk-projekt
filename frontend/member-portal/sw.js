const CACHE_NAME = 'kyrka-v10';
const OFFLINE_URLS = [
  '/',
  '/index.html',
  '/donate/index.html',
  '/intake/index.html',
  '/education/index.html',
  '/privacy/index.html',
  '/live/index.html',
  '/funeral/index.html',
  '/about/index.html',
  '/contact/index.html',
  '/calendar/index.html',
  '/faq/index.html',
  '/baptism/index.html',
  '/tezkar/index.html',
  '/library/index.html',
  '/support/index.html',
  '/venue/index.html',
  '/styles.css',
  '/app.js',
  '/content.json',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_URLS))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

// Navigations request pretty URLs (/contact/) but OFFLINE_URLS are cached
// under /contact/index.html — a bare caches.match(request) misses and the
// page renders blank. Try the request, then its index.html form, then /.
function navigationFallback(request) {
  return caches.match(request).then((hit) => {
    if (hit) return hit;
    const path = new URL(request.url).pathname;
    const indexKey = path.endsWith('/') ? path + 'index.html' : path + '/index.html';
    return caches.match(indexKey).then((indexHit) => indexHit || caches.match('/index.html'));
  });
}

self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // Network-first for HTML and content.json (always want fresh navigation)
  if (event.request.mode === 'navigate' || url.includes('content.json')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => navigationFallback(event.request))
    );
    return;
  }

  // Stale-while-revalidate for CSS, JS, images, fonts
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request).then((response) => {
        if (response.ok && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});

// Push notification handler
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Nytt från kyrkan';
  const options = {
    body: data.body || '',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    data: { url: data.url || '/' },
    ...(data.body_am ? { actions: [{ action: 'open', title: 'Öppna / ክፈት' }] } : {}),
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(clients.openWindow(url));
});
