// Service Worker for AI Banking Assistant PWA
// Version 2.0.0

const CACHE_NAME = 'banking-assistant-v2.0.0';
const STATIC_CACHE = 'banking-static-v2.0.0';
const API_CACHE = 'banking-api-v2.0.0';
const IMAGE_CACHE = 'banking-images-v2.0.0';

// Assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/loans',
    '/branches', 
    '/chat',
    '/currency',
    '/static/css/styles.css',
    '/static/js/app.js',
    '/static/favicon_io/favicon.ico',
    '/static/favicon_io/android-chrome-192x192.png',
    '/static/favicon_io/android-chrome-512x512.png',
    '/static/favicon_io/apple-touch-icon.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
    'https://cdn.jsdelivr.net/npm/chart.js@4.3.0/dist/chart.min.js',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
];

// API endpoints to cache
const API_ENDPOINTS = [
    '/api/health',
    '/api/currency/rates'
];

// Cache strategies
const CACHE_STRATEGIES = {
    static: 'cache-first',
    api: 'network-first', 
    images: 'cache-first',
    pages: 'network-first'
};

// Cache durations (in milliseconds)
const CACHE_DURATIONS = {
    static: 24 * 60 * 60 * 1000, // 24 hours
    api: 5 * 60 * 1000,          // 5 minutes
    images: 7 * 24 * 60 * 60 * 1000, // 7 days
    pages: 60 * 60 * 1000        // 1 hour
};

// Install Event - Cache static assets
self.addEventListener('install', event => {
    console.log('🔧 Service Worker installing...');
    
    event.waitUntil(
        Promise.all([
            // Cache static assets
            caches.open(STATIC_CACHE).then(cache => {
                console.log('📦 Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            }),
            
            // Cache API endpoints
            caches.open(API_CACHE).then(cache => {
                console.log('🔗 Pre-caching API endpoints');
                return Promise.allSettled(
                    API_ENDPOINTS.map(url => 
                        fetch(url)
                            .then(response => {
                                if (response.ok) {
                                    return cache.put(url, response.clone());
                                }
                            })
                            .catch(err => console.warn(`Failed to cache ${url}:`, err))
                    )
                );
            })
        ]).then(() => {
            console.log('✅ Service Worker installed successfully');
            // Force activation
            return self.skipWaiting();
        })
    );
});

// Activate Event - Clean up old caches
self.addEventListener('activate', event => {
    console.log('🚀 Service Worker activating...');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            caches.keys().then(cacheNames => {
                const validCaches = [CACHE_NAME, STATIC_CACHE, API_CACHE, IMAGE_CACHE];
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (!validCaches.includes(cacheName)) {
                            console.log('🗑️ Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            
            // Claim all clients
            self.clients.claim()
        ]).then(() => {
            console.log('✅ Service Worker activated successfully');
        })
    );
});

// Fetch Event - Handle requests with appropriate caching strategy
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests and chrome-extension requests
    if (request.method !== 'GET' || url.protocol === 'chrome-extension:') {
        return;
    }
    
    // Determine caching strategy based on request type
    if (isStaticAsset(request)) {
        event.respondWith(handleStaticAsset(request));
    } else if (isAPIRequest(request)) {
        event.respondWith(handleAPIRequest(request));
    } else if (isImageRequest(request)) {
        event.respondWith(handleImageRequest(request));
    } else if (isPageRequest(request)) {
        event.respondWith(handlePageRequest(request));
    } else {
        // Default: network-first for other requests
        event.respondWith(handleNetworkFirst(request, STATIC_CACHE));
    }
});

// Static Asset Handler - Cache First
async function handleStaticAsset(request) {
    try {
        const cache = await caches.open(STATIC_CACHE);
        const cached = await cache.match(request);
        
        if (cached && !isExpired(cached, CACHE_DURATIONS.static)) {
            return cached;
        }
        
        const response = await fetch(request);
        if (response.ok) {
            await cache.put(request, response.clone());
        }
        return response;
        
    } catch (error) {
        console.warn('Static asset fetch failed:', error);
        const cached = await caches.match(request);
        return cached || createErrorResponse('Static asset unavailable');
    }
}

// API Request Handler - Network First with fallback
async function handleAPIRequest(request) {
    try {
        const response = await fetch(request, {
            headers: {
                'Cache-Control': 'no-cache'
            }
        });
        
        if (response.ok) {
            const cache = await caches.open(API_CACHE);
            await cache.put(request, response.clone());
            return response;
        }
        
        throw new Error(`API responded with ${response.status}`);
        
    } catch (error) {
        console.warn('API request failed, using cache:', error);
        
        const cache = await caches.open(API_CACHE);
        const cached = await cache.match(request);
        
        if (cached) {
            // Add offline indicator to cached responses
            const cachedResponse = cached.clone();
            cachedResponse.headers.set('X-Served-From', 'cache');
            return cachedResponse;
        }
        
        // Return offline response for specific endpoints
        if (request.url.includes('/api/health')) {
            return new Response(JSON.stringify({
                status: 'offline',
                timestamp: new Date().toISOString(),
                database: 'unknown',
                mcp_client: 'unknown',
                ai_model: 'unknown'
            }), {
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        if (request.url.includes('/api/currency/rates')) {
            return new Response(JSON.stringify({
                rates: {
                    USD: 1.70,
                    EUR: 1.85,
                    RUB: 0.019,
                    TRY: 0.050,
                    GBP: 2.10
                },
                last_updated: new Date().toISOString(),
                source: 'cached',
                offline: true
            }), {
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        return createErrorResponse('Service temporarily unavailable');
    }
}

// Image Request Handler - Cache First
async function handleImageRequest(request) {
    try {
        const cache = await caches.open(IMAGE_CACHE);
        const cached = await cache.match(request);
        
        if (cached && !isExpired(cached, CACHE_DURATIONS.images)) {
            return cached;
        }
        
        const response = await fetch(request);
        if (response.ok) {
            await cache.put(request, response.clone());
        }
        return response;
        
    } catch (error) {
        const cached = await caches.match(request);
        return cached || createPlaceholderImage();
    }
}

// Page Request Handler - Network First
async function handlePageRequest(request) {
    return handleNetworkFirst(request, CACHE_NAME);
}

// Generic Network First Handler
async function handleNetworkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        
        if (response.ok) {
            const cache = await caches.open(cacheName);
            await cache.put(request, response.clone());
        }
        
        return response;
        
    } catch (error) {
        const cached = await caches.match(request);
        
        if (cached) {
            return cached;
        }
        
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            return caches.match('/') || createOfflinePage();
        }
        
        return createErrorResponse('Resource unavailable offline');
    }
}

// Helper Functions
function isStaticAsset(request) {
    const url = new URL(request.url);
    return url.pathname.includes('/static/') || 
           url.hostname === 'cdn.jsdelivr.net' ||
           url.hostname === 'unpkg.com' ||
           url.hostname === 'cdnjs.cloudflare.com';
}

function isAPIRequest(request) {
    return request.url.includes('/api/');
}

function isImageRequest(request) {
    const url = new URL(request.url);
    return /\.(jpg|jpeg|png|gif|webp|svg|ico)$/i.test(url.pathname);
}

function isPageRequest(request) {
    return request.mode === 'navigate' || 
           (request.destination === 'document' && request.method === 'GET');
}

function isExpired(response, maxAge) {
    const cachedDate = new Date(response.headers.get('date') || Date.now());
    return Date.now() - cachedDate.getTime() > maxAge;
}

function createErrorResponse(message) {
    return new Response(JSON.stringify({ error: message }), {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
    });
}

function createPlaceholderImage() {
    // Simple 1x1 transparent PNG
    const transparentPNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
    return new Response(atob(transparentPNG), {
        headers: { 'Content-Type': 'image/png' }
    });
}

function createOfflinePage() {
    const offlineHTML = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - Banking Assistant</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    text-align: center;
                    padding: 2rem;
                    background: linear-gradient(135deg, #1f4e79 0%, #2980b9 100%);
                    color: white;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                }
                .container {
                    max-width: 400px;
                    background: rgba(255,255,255,0.1);
                    padding: 2rem;
                    border-radius: 10px;
                    backdrop-filter: blur(10px);
                }
                h1 { margin-bottom: 1rem; }
                p { margin-bottom: 1.5rem; opacity: 0.9; }
                button {
                    background: white;
                    color: #1f4e79;
                    border: none;
                    padding: 1rem 2rem;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: transform 0.2s;
                }
                button:hover { transform: translateY(-2px); }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏦 Banking Assistant</h1>
                <h2>📴 You're Offline</h2>
                <p>Some features may not be available while offline. The app will automatically reconnect when your internet connection is restored.</p>
                <button onclick="window.location.reload()">Try Again</button>
            </div>
        </body>
        </html>
    `;
    
    return new Response(offlineHTML, {
        headers: { 'Content-Type': 'text/html' }
    });
}

// Background Sync for failed API requests
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        event.waitUntil(retryFailedRequests());
    }
});

async function retryFailedRequests() {
    // Implementation for retrying failed requests when back online
    console.log('🔄 Retrying failed requests...');
    
    try {
        // Check if we're back online
        const healthCheck = await fetch('/api/health');
        if (healthCheck.ok) {
            console.log('✅ Back online, connection restored');
            
            // Notify all clients that we're back online
            const clients = await self.clients.matchAll();
            clients.forEach(client => {
                client.postMessage({ type: 'CONNECTION_RESTORED' });
            });
        }
    } catch (error) {
        console.log('❌ Still offline');
    }
}

// Push notifications (for future enhancement)
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/favicon_io/android-chrome-192x192.png',
            badge: '/static/favicon_io/android-chrome-192x192.png',
            vibrate: [100, 50, 100],
            data: data.data || {},
            actions: data.actions || []
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    const urlToOpen = event.notification.data?.url || '/';
    
    event.waitUntil(
        self.clients.matchAll().then(clients => {
            // Check if app is already open
            for (const client of clients) {
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            
            // Open new window/tab
            if (self.clients.openWindow) {
                return self.clients.openWindow(urlToOpen);
            }
        })
    );
});

// Message handling from main app
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// Performance monitoring
let performanceMetrics = {
    cacheHits: 0,
    cacheMisses: 0,
    networkRequests: 0,
    offlineRequests: 0
};

// Update performance metrics
function updateMetrics(type) {
    performanceMetrics[type]++;
    
    // Send metrics to main app periodically
    if (performanceMetrics.networkRequests % 10 === 0) {
        self.clients.matchAll().then(clients => {
            clients.forEach(client => {
                client.postMessage({
                    type: 'SW_METRICS',
                    metrics: performanceMetrics
                });
            });
        });
    }
}

console.log('🎯 Banking Assistant Service Worker loaded successfully');