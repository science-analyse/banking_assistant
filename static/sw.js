// Service Worker for Banking Assistant PWA
const CACHE_NAME = 'banking-assistant-v1.0.0';
const STATIC_CACHE = 'banking-assistant-static-v1.0.0';
const DYNAMIC_CACHE = 'banking-assistant-dynamic-v1.0.0';

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
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
];

// API endpoints that should not be cached
const NO_CACHE_URLS = [
    '/api/chat',
    '/api/clear-chat'
];

// Install event - cache static files
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Service Worker: Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => {
                console.log('Service Worker: Static files cached successfully');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('Service Worker: Error caching static files:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                            console.log('Service Worker: Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('Service Worker: Activation complete');
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
    
    // Skip API endpoints that shouldn't be cached
    if (NO_CACHE_URLS.some(endpoint => url.pathname.includes(endpoint))) {
        return;
    }
    
    // Handle static files
    if (STATIC_FILES.includes(url.pathname) || url.pathname === '/') {
        event.respondWith(cacheFirstStrategy(request));
        return;
    }
    
    // Handle other requests
    event.respondWith(networkFirstStrategy(request));
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
        if (networkResponse.status === 200) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('Service Worker: Cache first strategy failed:', error);
        
        // Return offline page for navigation requests
        if (request.destination === 'document') {
            return caches.match('/');
        }
        
        throw error;
    }
}

// Network first strategy for dynamic content
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.status === 200) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Service Worker: Network failed, trying cache:', error);
        
        const cacheResponse = await caches.match(request);
        if (cacheResponse) {
            return cacheResponse;
        }
        
        // Return offline page for navigation requests
        if (request.destination === 'document') {
            return caches.match('/');
        }
        
        throw error;
    }
}

// Handle background sync for offline actions
self.addEventListener('sync', event => {
    console.log('Service Worker: Background sync triggered:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(handleBackgroundSync());
    }
});

// Handle push notifications (for future use)
self.addEventListener('push', event => {
    console.log('Service Worker: Push notification received');
    
    const options = {
        body: event.data ? event.data.text() : 'New banking information available',
        icon: '/static/favicon_io/android-chrome-192x192.png',
        badge: '/static/favicon_io/favicon-32x32.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'View Details',
                icon: '/static/favicon_io/android-chrome-192x192.png'
            },
            {
                action: 'close',
                title: 'Close',
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
    console.log('Service Worker: Notification clicked');
    
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Background sync handler
async function handleBackgroundSync() {
    try {
        // Handle any pending offline actions here
        console.log('Service Worker: Handling background sync');
        
        // For example, sync pending chat messages when back online
        const pendingMessages = await getStoredPendingMessages();
        
        for (const message of pendingMessages) {
            try {
                await sendPendingMessage(message);
                await removePendingMessage(message.id);
            } catch (error) {
                console.error('Service Worker: Failed to sync message:', error);
            }
        }
    } catch (error) {
        console.error('Service Worker: Background sync failed:', error);
    }
}

// Helper functions for offline message handling
async function getStoredPendingMessages() {
    // Implementation would depend on your offline storage strategy
    return [];
}

async function sendPendingMessage(message) {
    // Implementation for sending stored messages
    return fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(message)
    });
}

async function removePendingMessage(messageId) {
    // Implementation for removing synced messages
    console.log('Service Worker: Message synced and removed:', messageId);
}

// Message handling for communication with main thread
self.addEventListener('message', event => {
    console.log('Service Worker: Message received:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    }
});