/**
 * Kapital Bank AI Assistant - Service Worker
 * Provides offline functionality and caching for PWA
 */

const CACHE_NAME = 'kapital-bank-assistant-v1.0.0';
const STATIC_CACHE = 'kapital-static-v1';
const DYNAMIC_CACHE = 'kapital-dynamic-v1';

// Files to cache immediately
const STATIC_FILES = [
    '/',
    '/static/css/styles.css',
    '/static/js/app.js',
    '/static/favicon_io/favicon-32x32.png',
    '/static/favicon_io/android-chrome-192x192.png',
    '/static/favicon_io/android-chrome-512x512.png',
    '/loans',
    '/branches',
    '/currency',
    '/chat',
    '/offline' // Offline fallback page
];

// API endpoints to cache
const API_CACHE_PATTERNS = [
    /\/api\/health/,
    /\/api\/currency\/rates/
];

// Network-first patterns (always try network first)
const NETWORK_FIRST_PATTERNS = [
    /\/api\/chat/,
    /\/api\/locations/,
    /\/api\/currency\/compare/
];

// Cache-first patterns (try cache first)
const CACHE_FIRST_PATTERNS = [
    /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/,
    /\.(?:css|js)$/,
    /\/static\//
];

// Install event - cache static files
self.addEventListener('install', event => {
    console.log('[SW] Install event');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('[SW] Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => {
                console.log('[SW] Static files cached');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('[SW] Failed to cache static files:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[SW] Activate event');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('[SW] Cache cleanup complete');
                return self.clients.claim();
            })
    );
});

// Fetch event - handle requests with different strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip chrome-extension and other non-http requests
    if (!url.protocol.startsWith('http')) {
        return;
    }
    
    event.respondWith(handleRequest(request));
});

// Main request handler
async function handleRequest(request) {
    const url = new URL(request.url);
    
    try {
        // Cache-first strategy for static assets
        if (isCacheFirst(url)) {
            return await cacheFirst(request);
        }
        
        // Network-first strategy for dynamic content
        if (isNetworkFirst(url)) {
            return await networkFirst(request);
        }
        
        // API caching strategy
        if (isApiRequest(url)) {
            return await apiCache(request);
        }
        
        // Default: stale-while-revalidate
        return await staleWhileRevalidate(request);
        
    } catch (error) {
        console.error('[SW] Request failed:', error);
        return await handleOffline(request);
    }
}

// Cache-first strategy
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }
    
    const response = await fetch(request);
    if (response.ok) {
        const cache = await caches.open(STATIC_CACHE);
        cache.put(request, response.clone());
    }
    
    return response;
}

// Network-first strategy
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        
        if (response.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, response.clone());
        }
        
        return response;
    } catch (error) {
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        throw error;
    }
}

// API caching strategy
async function apiCache(request) {
    const url = new URL(request.url);
    
    // For health checks and currency rates, use network-first with short cache
    if (url.pathname.includes('/health') || url.pathname.includes('/currency/rates')) {
        try {
            const response = await fetch(request);
            if (response.ok) {
                const cache = await caches.open(DYNAMIC_CACHE);
                // Add timestamp to control cache freshness
                const clonedResponse = response.clone();
                const data = await clonedResponse.json();
                data._cached_at = Date.now();
                
                const modifiedResponse = new Response(JSON.stringify(data), {
                    status: response.status,
                    statusText: response.statusText,
                    headers: response.headers
                });
                
                cache.put(request, modifiedResponse);
            }
            return response;
        } catch (error) {
            // Try cache for offline
            const cached = await caches.match(request);
            if (cached) {
                const data = await cached.json();
                // Check if cache is too old (> 5 minutes for currency, > 1 hour for health)
                const maxAge = url.pathname.includes('/currency') ? 5 * 60 * 1000 : 60 * 60 * 1000;
                const isStale = data._cached_at && (Date.now() - data._cached_at) > maxAge;
                
                if (!isStale) {
                    return cached;
                }
            }
            throw error;
        }
    }
    
    // For other API requests, try network first
    return await networkFirst(request);
}

// Stale-while-revalidate strategy
async function staleWhileRevalidate(request) {
    const cached = await caches.match(request);
    
    const fetchPromise = fetch(request).then(response => {
        if (response.ok) {
            const cache = caches.open(DYNAMIC_CACHE);
            cache.then(c => c.put(request, response.clone()));
        }
        return response;
    });
    
    return cached || fetchPromise;
}

// Handle offline scenarios
async function handleOffline(request) {
    const url = new URL(request.url);
    
    // Try to find a cached version
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }
    
    // For HTML pages, return offline page
    if (request.headers.get('accept')?.includes('text/html')) {
        const offlinePage = await caches.match('/offline');
        if (offlinePage) {
            return offlinePage;
        }
        
        // Fallback offline response
        return new Response(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Offline - Kapital Bank Assistant</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .offline-container { max-width: 400px; margin: 0 auto; }
                    .offline-icon { font-size: 64px; margin-bottom: 20px; }
                    h1 { color: #1f4e79; }
                    p { color: #666; line-height: 1.6; }
                    .retry-btn { 
                        background: #1f4e79; color: white; border: none; 
                        padding: 12px 24px; border-radius: 6px; cursor: pointer;
                        margin-top: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="offline-container">
                    <div class="offline-icon">🏛️📡</div>
                    <h1>You're Offline</h1>
                    <p>Kapital Bank AI Assistant needs an internet connection to work properly.</p>
                    <p>Please check your connection and try again.</p>
                    <button class="retry-btn" onclick="window.location.reload()">
                        Try Again
                    </button>
                </div>
            </body>
            </html>
        `, {
            status: 200,
            headers: { 'Content-Type': 'text/html' }
        });
    }
    
    // For API requests, return offline JSON
    if (url.pathname.startsWith('/api/')) {
        return new Response(JSON.stringify({
            error: 'Offline',
            message: 'This feature requires an internet connection'
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    // For other requests, return a 503 response
    return new Response('Service Unavailable', { status: 503 });
}

// Helper functions to determine caching strategy
function isCacheFirst(url) {
    return CACHE_FIRST_PATTERNS.some(pattern => pattern.test(url.pathname));
}

function isNetworkFirst(url) {
    return NETWORK_FIRST_PATTERNS.some(pattern => pattern.test(url.pathname));
}

function isApiRequest(url) {
    return url.pathname.startsWith('/api/') || 
           API_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('[SW] Background sync:', event.tag);
    
    if (event.tag === 'background-sync-chat') {
        event.waitUntil(syncPendingChats());
    }
    
    if (event.tag === 'background-sync-analytics') {
        event.waitUntil(syncAnalytics());
    }
});

// Sync pending chat messages when back online
async function syncPendingChats() {
    try {
        // Get pending chats from IndexedDB or localStorage
        const pendingChats = await getPendingChats();
        
        for (const chat of pendingChats) {
            try {
                await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(chat)
                });
                
                // Remove from pending queue
                await removePendingChat(chat.id);
            } catch (error) {
                console.error('[SW] Failed to sync chat:', error);
            }
        }
    } catch (error) {
        console.error('[SW] Background sync failed:', error);
    }
}

// Sync analytics data
async function syncAnalytics() {
    try {
        const analyticsData = await getPendingAnalytics();
        
        if (analyticsData.length > 0) {
            await fetch('/api/analytics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ events: analyticsData })
            });
            
            await clearPendingAnalytics();
        }
    } catch (error) {
        console.error('[SW] Analytics sync failed:', error);
    }
}

// Push notification handling
self.addEventListener('push', event => {
    console.log('[SW] Push notification received');
    
    const options = {
        body: 'New update available for Kapital Bank Assistant',
        icon: '/static/favicon_io/android-chrome-192x192.png',
        badge: '/static/favicon_io/android-chrome-192x192.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'Open App',
                icon: '/static/favicon_io/android-chrome-192x192.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/static/favicon_io/android-chrome-192x192.png'
            }
        ]
    };
    
    if (event.data) {
        const data = event.data.json();
        options.body = data.body || options.body;
        options.data = { ...options.data, ...data };
    }
    
    event.waitUntil(
        self.registration.showNotification('Kapital Bank Assistant', options)
    );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    console.log('[SW] Notification click received');
    
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    } else if (event.action === 'close') {
        // Just close the notification
        return;
    } else {
        // Default action - open app
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Placeholder functions for IndexedDB operations
async function getPendingChats() {
    // Implementation would use IndexedDB to store offline chats
    return [];
}

async function removePendingChat(chatId) {
    // Implementation would remove chat from IndexedDB
}

async function getPendingAnalytics() {
    // Implementation would get analytics data from IndexedDB
    return [];
}

async function clearPendingAnalytics() {
    // Implementation would clear analytics data from IndexedDB
}

// Message handling for communication with main app
self.addEventListener('message', event => {
    console.log('[SW] Message received:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    }
});

console.log('[SW] Service Worker loaded - Kapital Bank AI Assistant v1.0.0');