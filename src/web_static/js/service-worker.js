/* service-worker.js
 * Copyright (c) 2025 marsmensch
 * SPDX-License-Identifier: MIT
 */
/**
 * NomadBuild - PWA Service Worker
 */

const CACHE_NAME = 'nomadbuild-cache-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/css/normalize.css',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/img/logo.png',
  '/static/img/favicon.png',
  '/static/img/apple-touch-icon.png',
  '/manifest.json'
];

// Install event - cache assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(cacheName => {
          return cacheName !== CACHE_NAME;
        }).map(cacheName => {
          return caches.delete(cacheName);
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  // Skip caching API calls
  if (event.request.url.includes('/api/') ||
      event.request.url.includes('/socket.io/')) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached response if found
        if (response) {
          return response;
        }
        
        // Otherwise fetch from network
        return fetch(event.request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response since it can only be consumed once
            const responseToCache = response.clone();
            
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
              
            return response;
          });
      })
      .catch(() => {
        // If both cache and network fail, show offline page
        // In this basic implementation, we just return nothing
      })
  );
}); 