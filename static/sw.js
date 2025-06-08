// static/sw.js

const CACHE_NAME = 'banking-assistant-v1';
const urlsToCache = [
    '/',
    '/static/css/styles.css',
    '/static/js/app.js',
    '/static/favicon_io/favicon-32x32.png',
    '/static/favicon_io/favicon-16x16.png',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Install service worker
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

// Fetch resources
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // Skip API requests - always fetch fresh
    if (event.request.url.includes('/api/')) return;
    
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached version or fetch new
                return response || fetch(event.request);
            })
    );
});

// Update service worker
self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME];
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (!cacheWhitelist.includes(cacheName)) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});