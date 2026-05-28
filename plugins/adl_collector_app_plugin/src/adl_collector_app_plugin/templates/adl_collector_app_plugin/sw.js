// ADL Field Observer — Service Worker
// Served by Django (not as a static file) so it gets the correct scope.

const CACHE_NAME = 'adl-field-observer-v4';
const SHELL_URL = '{% url "plugins:collector_field_pwa" %}';

self.addEventListener('install', (event) => {
    // Pre-cache the shell on install so offline works from the first visit.
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.add(SHELL_URL))
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

    // Network-first for API calls — return offline error if unreachable.
    if (url.pathname.startsWith('/api/adl-collector/')) {
        event.respondWith(
            fetch(event.request).catch(() =>
                new Response(JSON.stringify({detail: 'Offline'}), {
                    status: 503,
                    headers: {'Content-Type': 'application/json'},
                })
            )
        );
        return;
    }

    // Cache-first for static assets (JS bundles, images, fonts).
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

    // Navigation requests (HTML shell) — network-first, fall back to cache.
    // This means template changes are visible immediately when online, and
    // the app still loads from cache when offline.
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).then((response) => {
                // Update the cached shell with the fresh response.
                const clone = response.clone();
                caches.open(CACHE_NAME).then((cache) => cache.put(SHELL_URL, clone));
                return response;
            }).catch(() => caches.match(SHELL_URL))
        );
        return;
    }
});
