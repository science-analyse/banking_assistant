// Service Worker for Banking Assistant PWA
const CACHE_NAME = 'banking-assistant-v1';
const urlsToCache = [
  '/',
  '/static/css/styles.css',
  '/static/js/app.js',
  '/static/favicon_io/favicon-32x32.png',
  '/static/favicon_io/favicon-16x16.png',
  'https://cdn.tailwindcss.com'
];

// Install event
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch event
self.addEventListener('fetch', event => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // Skip WebSocket requests
  if (event.request.url.includes('/ws')) return;

  // Skip API requests (always fetch fresh data)
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          // Return a custom offline response for API requests
          return new Response(
            JSON.stringify({
              error: 'Offline',
              message: 'Unable to fetch data. Please check your connection.'
            }),
            {
              headers: { 'Content-Type': 'application/json' }
            }
          );
        })
    );
    return;
  }

  // For other requests, try cache first, then network
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }

        return fetch(event.request).then(response => {
          // Check if we received a valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response
          const responseToCache = response.clone();

          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });

          return response;
        });
      })
      .catch(() => {
        // Offline fallback
        if (event.request.destination === 'document') {
          return caches.match('/');
        }
      })
  );
});

// Activate event
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];

  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Background sync for offline messages
self.addEventListener('sync', event => {
  if (event.tag === 'send-message') {
    event.waitUntil(sendQueuedMessages());
  }
});

async function sendQueuedMessages() {
  // This would be implemented to send queued messages when back online
  console.log('Syncing messages...');
}