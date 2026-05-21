// ADL Field Observer — Service Worker
// Served by Django (not as a static file) so it gets the correct scope.

const CACHE_NAME = 'adl-field-observer-v1';

// App shell files to pre-cache on install
const APP_SHELL = [
    '{% url "collector_field_pwa" %}',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Network-first for API calls — fall through to queue on failure
    if (url.pathname.startsWith('/api/adl-collector/')) {
        event.respondWith(
            fetch(event.request).catch(() =>
                new Response(JSON.stringify({ detail: 'Offline' }), {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' },
                })
            )
        );
        return;
    }

    // Cache-first for static assets (JS bundles, images, fonts)
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(
                (cached) => cached || fetch(event.request).then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    return response;
                })
            )
        );
        return;
    }

    // App shell — serve cached shell for navigation requests
    if (event.request.mode === 'navigate') {
        event.respondWith(
            caches.match('{% url "collector_field_pwa" %}').then(
                (cached) => cached || fetch(event.request)
            )
        );
        return;
    }
});
