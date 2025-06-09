// Enhanced Service Worker for Banking Assistant PWA
const CACHE_VERSION = 'v2.0.0';
const CACHE_NAME = `banking-assistant-${CACHE_VERSION}`;
const STATIC_CACHE = `banking-assistant-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `banking-assistant-dynamic-${CACHE_VERSION}`;
const API_CACHE = `banking-assistant-api-${CACHE_VERSION}`;

// Files to cache for offline functionality
const STATIC_FILES = [
    '/',
    '/static/css/styles.css',
    '/static/js/app.js',
    '/static/favicon_io/android-chrome-192x192.png',
    '/static/favicon_io/android-chrome-512x512.png',
    '/static/favicon_io/apple-touch-icon.png',
    '/static/favicon_io/favicon-32x32.png',
    '/static/favicon_io/favicon-16x16.png',
    '/static/favicon_io/favicon.ico',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
];

// API endpoints that should use network-first strategy
const API_ENDPOINTS = [
    '/api/chat',
    '/api/clear-chat',
    '/api/banking-info',
    '/api/services'
];

// Install event - cache static files
self.addEventListener('install', event => {
    console.log('[ServiceWorker] Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('[ServiceWorker] Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => {
                console.log('[ServiceWorker] Static files cached successfully');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('[ServiceWorker] Error caching static files:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[ServiceWorker] Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (!cacheName.includes(CACHE_VERSION)) {
                            console.log('[ServiceWorker] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('[ServiceWorker] Activation complete');
                // Take control of all clients immediately
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Handle API requests
    if (API_ENDPOINTS.some(endpoint => url.pathname.includes(endpoint))) {
        event.respondWith(networkFirstStrategy(request));
        return;
    }
    
    // Handle static files
    if (STATIC_FILES.includes(url.pathname) || url.pathname === '/') {
        event.respondWith(cacheFirstStrategy(request));
        return;
    }
    
    // Handle other requests with stale-while-revalidate
    event.respondWith(staleWhileRevalidate(request));
});

// Cache first strategy for static files
async function cacheFirstStrategy(request) {
    try {
        const cacheResponse = await caches.match(request);
        if (cacheResponse) {
            return cacheResponse;
        }
        
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('[ServiceWorker] Cache first strategy failed:', error);
        
        // Return offline page for navigation requests
        if (request.destination === 'document') {
            return createOfflineResponse();
        }
        
        throw error;
    }
}

// Network first strategy for API requests
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        
        // Cache successful API responses
        if (networkResponse.ok) {
            const cache = await caches.open(API_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[ServiceWorker] Network failed, trying cache:', error);
        
        const cacheResponse = await caches.match(request);
        if (cacheResponse) {
            return cacheResponse;
        }
        
        // Return offline API response
        return createOfflineAPIResponse();
    }
}

// Stale while revalidate strategy
async function staleWhileRevalidate(request) {
    const cache = await caches.open(DYNAMIC_CACHE);
    const cacheResponse = await cache.match(request);
    
    const networkPromise = fetch(request).then(response => {
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    }).catch(error => {
        console.log('[ServiceWorker] Network request failed:', error);
        return cacheResponse || createOfflineResponse();
    });
    
    return cacheResponse || networkPromise;
}

// Create offline response for pages
function createOfflineResponse() {
    const html = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - Banking Assistant</title>
            <style>
                body {
                    font-family: 'Inter', system-ui, -apple-system, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: #f8fafc;
                    color: #0f172a;
                }
                .offline-container {
                    text-align: center;
                    padding: 2rem;
                    max-width: 400px;
                }
                .offline-icon {
                    width: 80px;
                    height: 80px;
                    margin: 0 auto 1.5rem;
                    opacity: 0.5;
                }
                h1 {
                    font-size: 1.5rem;
                    margin-bottom: 0.5rem;
                }
                p {
                    color: #475569;
                    line-height: 1.6;
                }
                button {
                    margin-top: 1.5rem;
                    padding: 0.75rem 1.5rem;
                    background: #2563eb;
                    color: white;
                    border: none;
                    border-radius: 0.5rem;
                    font-weight: 500;
                    cursor: pointer;
                }
                button:hover {
                    background: #1e40af;
                }
            </style>
        </head>
        <body>
            <div class="offline-container">
                <svg class="offline-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"></path>
                </svg>
                <h1>You're offline</h1>
                <p>It looks like you've lost your internet connection. Please check your connection and try again.</p>
                <button onclick="window.location.reload()">Try Again</button>
            </div>
        </body>
        </html>
    `;
    
    return new Response(html, {
        headers: { 'Content-Type': 'text/html' },
        status: 200
    });
}

// Create offline API response
function createOfflineAPIResponse() {
    return new Response(JSON.stringify({
        error: 'You are currently offline',
        offline: true
    }), {
        headers: { 'Content-Type': 'application/json' },
        status: 503
    });
}

// Handle background sync for offline actions
self.addEventListener('sync', event => {
    console.log('[ServiceWorker] Background sync triggered:', event.tag);
    
    if (event.tag === 'sync-messages') {
        event.waitUntil(syncMessages());
    }
});

// Sync offline messages
async function syncMessages() {
    try {
        const cache = await caches.open('offline-messages');
        const requests = await cache.keys();
        
        for (const request of requests) {
            try {
                const response = await fetch(request);
                if (response.ok) {
                    await cache.delete(request);
                }
            } catch (error) {
                console.error('[ServiceWorker] Failed to sync message:', error);
            }
        }
    } catch (error) {
        console.error('[ServiceWorker] Background sync failed:', error);
    }
}

// Handle push notifications
self.addEventListener('push', event => {
    console.log('[ServiceWorker] Push notification received');
    
    const options = {
        body: event.data ? event.data.text() : 'New update available',
        icon: '/static/favicon_io/android-chrome-192x192.png',
        badge: '/static/favicon_io/favicon-32x32.png',
        vibrate: [100, 50, 100],
        tag: 'banking-notification',
        renotify: true,
        actions: [
            {
                action: 'open',
                title: 'Open App',
                icon: '/static/favicon_io/android-chrome-192x192.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('Banking Assistant', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    console.log('[ServiceWorker] Notification clicked');
    
    event.notification.close();
    
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(clientList => {
            // Check if there's already a window/tab open
            for (const client of clientList) {
                if (client.url === '/' && 'focus' in client) {
                    return client.focus();
                }
            }
            // If not, open a new window
            if (clients.openWindow) {
                return clients.openWindow('/');
            }
        })
    );
});

// Message handling for communication with main thread
self.addEventListener('message', event => {
    console.log('[ServiceWorker] Message received:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_VERSION });
    }
    
    if (event.data && event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => caches.delete(cacheName))
                );
            }).then(() => {
                event.ports[0].postMessage({ success: true });
            })
        );
    }
});

// Periodic background sync (if supported)
self.addEventListener('periodicsync', event => {
    if (event.tag === 'update-cache') {
        event.waitUntil(updateCache());
    }
});

// Update cache periodically
async function updateCache() {
    try {
        const cache = await caches.open(STATIC_CACHE);
        const promises = STATIC_FILES.map(async url => {
            try {
                const response = await fetch(url, { cache: 'no-cache' });
                if (response.ok) {
                    await cache.put(url, response);
                }
            } catch (error) {
                console.error(`[ServiceWorker] Failed to update ${url}:`, error);
            }
        });
        
        await Promise.all(promises);
        console.log('[ServiceWorker] Cache updated successfully');
    } catch (error) {
        console.error('[ServiceWorker] Cache update failed:', error);
    }
}