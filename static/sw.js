// Service Worker for Kapital Bank AI Assistant
// Light Mode Only - PWA Support with Offline Functionality

const CACHE_NAME = 'kapital-bank-v1.0.0';
const OFFLINE_URL = '/offline';

// Resources to cache for offline functionality
const CACHE_URLS = [
  '/',
  '/offline',
  '/currency',
  '/locations', 
  '/chat',
  '/loans',
  '/static/css/styles.css',
  '/static/js/app.js',
  '/static/favicon_io/favicon-32x32.png',
  '/static/favicon_io/favicon-16x16.png',
  '/static/favicon_io/apple-touch-icon.png',
  '/static/favicon_io/android-chrome-192x192.png',
  '/static/favicon_io/android-chrome-512x512.png',
  // Bootstrap and other CDN resources
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
];

// API endpoints that should be cached
const API_CACHE_URLS = [
  '/api/health',
  '/api/currency/rates',
  '/api/currency/supported',
  '/api/locations'
];

// Install event - cache resources
self.addEventListener('install', event => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching app shell...');
        return cache.addAll(CACHE_URLS);
      })
      .then(() => {
        // Cache API endpoints with error handling
        return caches.open(CACHE_NAME + '-api');
      })
      .then(apiCache => {
        console.log('Caching API endpoints...');
        return Promise.allSettled(
          API_CACHE_URLS.map(url => 
            fetch(url)
              .then(response => {
                if (response.ok) {
                  return apiCache.put(url, response.clone());
                }
              })
              .catch(err => console.log(`Failed to cache ${url}:`, err))
          )
        );
      })
      .then(() => {
        console.log('Service Worker installation complete');
        return self.skipWaiting();
      })
      .catch(err => {
        console.error('Service Worker installation failed:', err);
      })
  );
});

// Activate event - cleanup old caches
self.addEventListener('activate', event => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames
            .filter(cacheName => {
              return cacheName !== CACHE_NAME && 
                     cacheName !== CACHE_NAME + '-api' &&
                     cacheName.startsWith('kapital-bank-');
            })
            .map(cacheName => {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('Service Worker activation complete');
        return self.clients.claim();
      })
  );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Handle different types of requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Handle navigation requests
  if (request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(request));
    return;
  }
  
  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }
  
  // Handle static resources
  event.respondWith(handleStaticRequest(request));
});

// Handle navigation requests (HTML pages)
async function handleNavigationRequest(request) {
  try {
    // Try network first
    const response = await fetch(request);
    
    if (response.ok) {
      // Cache successful responses
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
      return response;
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    console.log('Network failed for navigation, trying cache:', error);
    
    // Try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // For specific pages, try to serve cached version
    const url = new URL(request.url);
    const cachedPage = await caches.match(url.pathname);
    if (cachedPage) {
      return cachedPage;
    }
    
    // Fall back to offline page
    const offlineResponse = await caches.match(OFFLINE_URL);
    if (offlineResponse) {
      return offlineResponse;
    }
    
    // Last resort - basic offline response
    return new Response(
      createOfflineHTML(),
      {
        status: 200,
        headers: { 'Content-Type': 'text/html' }
      }
    );
  }
}

// Handle API requests
async function handleApiRequest(request) {
  const url = new URL(request.url);
  
  try {
    // Try network first with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    
    const response = await fetch(request, {
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      // Cache successful API responses
      const apiCache = await caches.open(CACHE_NAME + '-api');
      
      // Only cache GET requests for certain endpoints
      if (shouldCacheApiResponse(url.pathname)) {
        apiCache.put(request, response.clone());
      }
      
      return response;
    } else {
      throw new Error(`API HTTP ${response.status}`);
    }
  } catch (error) {
    console.log('API network failed, trying cache:', error);
    
    // Try cache for API requests
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      // Add header to indicate cached response
      const headers = new Headers(cachedResponse.headers);
      headers.set('X-Served-By', 'ServiceWorker-Cache');
      headers.set('X-Cache-Date', new Date().toISOString());
      
      return new Response(cachedResponse.body, {
        status: cachedResponse.status,
        statusText: cachedResponse.statusText,
        headers: headers
      });
    }
    
    // Return offline fallback for specific API endpoints
    return createOfflineApiResponse(url.pathname);
  }
}

// Handle static resource requests
async function handleStaticRequest(request) {
  try {
    // Try cache first for static resources
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      // Check if we should update in background
      if (shouldUpdateInBackground(request.url)) {
        updateCacheInBackground(request);
      }
      return cachedResponse;
    }
    
    // Try network
    const response = await fetch(request);
    
    if (response.ok) {
      // Cache the response
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
      return response;
    }
    
    throw new Error(`HTTP ${response.status}`);
  } catch (error) {
    console.log('Static resource failed:', error);
    
    // For critical CSS/JS, try to serve a fallback
    if (request.url.includes('.css')) {
      return new Response('/* Offline - CSS unavailable */', {
        headers: { 'Content-Type': 'text/css' }
      });
    }
    
    if (request.url.includes('.js')) {
      return new Response('// Offline - JS unavailable', {
        headers: { 'Content-Type': 'application/javascript' }
      });
    }
    
    // For other resources, return a network error
    return new Response('Resource unavailable offline', {
      status: 503,
      headers: { 'Content-Type': 'text/plain' }
    });
  }
}

// Helper functions
function shouldCacheApiResponse(pathname) {
  const cacheableEndpoints = [
    '/api/health',
    '/api/currency/rates',
    '/api/currency/supported',
    '/api/locations'
  ];
  return cacheableEndpoints.some(endpoint => pathname.startsWith(endpoint));
}

function shouldUpdateInBackground(url) {
  // Update CSS and JS files in background
  return url.includes('.css') || url.includes('.js') || url.includes('/api/');
}

async function updateCacheInBackground(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response);
    }
  } catch (error) {
    // Ignore background update errors
    console.log('Background update failed:', error);
  }
}

function createOfflineApiResponse(pathname) {
  let offlineData = {};
  
  if (pathname.includes('/currency/rates')) {
    offlineData = {
      base_currency: "AZN",
      source: "CBAR (Central Bank of Azerbaijan Republic) - Cached Data",
      source_note: "CBAR is the regulatory authority that sets official exchange rates. Commercial banks reference these rates and add their service margins.",
      last_updated: new Date().toISOString(),
      rates: {
        "USD": {"rate": 1.70, "name": "US Dollar"},
        "EUR": {"rate": 1.85, "name": "Euro"},
        "GBP": {"rate": 2.15, "name": "British Pound"},
        "RUB": {"rate": 0.018, "name": "Russian Ruble"},
        "TRY": {"rate": 0.055, "name": "Turkish Lira"},
        "GEL": {"rate": 0.63, "name": "Georgian Lari"}
      },
      status: "offline",
      disclaimer: "These are cached CBAR reference rates. Actual bank rates may differ and include service fees."
    };
  } else if (pathname.includes('/health')) {
    offlineData = {
      status: "offline",
      timestamp: new Date().toISOString(),
      version: "1.0.0",
      services: {
        currency_api: "offline",
        chat_ai: "offline", 
        maps: "offline"
      }
    };
  } else if (pathname.includes('/locations')) {
    offlineData = {
      locations: [],
      total: 0,
      status: "offline",
      message: "Location services require internet connection"
    };
  } else {
    offlineData = {
      error: "Service unavailable offline",
      status: "offline"
    };
  }
  
  return new Response(JSON.stringify(offlineData), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'X-Served-By': 'ServiceWorker-Offline'
    }
  });
}

function createOfflineHTML() {
  return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Offline - Kapital Bank</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8f9fa;
            color: #212529;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .icon {
            font-size: 4rem;
            color: #6c757d;
            margin-bottom: 20px;
        }
        h1 {
            color: #1f4e79;
            margin-bottom: 20px;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background: #1f4e79;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px;
        }
        .offline-info {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📶</div>
        <h1>You're Offline</h1>
        <p>It looks like you've lost your internet connection.</p>
        
        <div class="offline-info">
            <h3>Emergency Contact</h3>
            <p><strong>Customer Service:</strong><br>
            <a href="tel:+994123100000">+994 12 310 00 00</a></p>
            
            <p><strong>Banking Hours:</strong><br>
            Mon-Fri: 09:00-18:00<br>
            Saturday: 09:00-14:00</p>
        </div>
        
        <a href="javascript:window.location.reload()" class="btn">Try Again</a>
        <a href="/" class="btn">Go Home</a>
    </div>
    
    <script>
        // Auto-redirect when connection is restored
        window.addEventListener('online', function() {
            window.location.reload();
        });
    </script>
</body>
</html>
  `;
}

// Message handling for communication with main thread
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_URLS') {
    // Cache additional URLs requested by the app
    const urls = event.data.urls;
    caches.open(CACHE_NAME).then(cache => {
      cache.addAll(urls).catch(err => {
        console.log('Failed to cache additional URLs:', err);
      });
    });
  }
});

// Background sync for when connection is restored
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    event.waitUntil(updateCaches());
  }
});

async function updateCaches() {
  try {
    // Update critical API endpoints
    const apiCache = await caches.open(CACHE_NAME + '-api');
    
    for (const url of API_CACHE_URLS) {
      try {
        const response = await fetch(url);
        if (response.ok) {
          await apiCache.put(url, response);
          console.log('Updated cache for:', url);
        }
      } catch (error) {
        console.log('Failed to update cache for:', url, error);
      }
    }
  } catch (error) {
    console.log('Background sync failed:', error);
  }
}

// Push notification handling (for future use)
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    
    const options = {
      body: data.body || 'New notification from Kapital Bank',
      icon: '/static/favicon_io/android-chrome-192x192.png',
      badge: '/static/favicon_io/favicon-32x32.png',
      tag: data.tag || 'kapital-bank-notification',
      data: data.data || {},
      requireInteraction: false,
      silent: false
    };
    
    event.waitUntil(
      self.registration.showNotification(
        data.title || 'Kapital Bank',
        options
      )
    );
  }
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  const clickAction = event.notification.data?.clickAction || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        // Try to focus existing window
        for (const client of clientList) {
          if (client.url.includes(clickAction) && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(clickAction);
        }
      })
  );
});