// This is the service worker with the combined offline experience (Offline page + Offline copy of pages)

const CACHE = "pwabuilder-offline-page";

importScripts('https://storage.googleapis.com/workbox-cdn/releases/5.1.2/workbox-sw.js');

const currentYear = new Date().getFullYear();
const offlineFallbackPage = `/${currentYear}/top`;

self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
});

self.addEventListener('install', async(event) => {
    event.waitUntil(
        caches.open(CACHE)
        .then((cache) => cache.add(offlineFallbackPage))
    );
});

if (workbox.navigationPreload.isSupported()) {
    workbox.navigationPreload.enable();
}

// ネットワーク優先の戦略に変更
workbox.routing.registerRoute(
    new RegExp('/*'),
    new workbox.strategies.NetworkFirst({
        cacheName: CACHE,
        plugins: [
            new workbox.expiration.ExpirationPlugin({
                maxEntries: 50,
                maxAgeSeconds: 30 * 24 * 60 * 60, // 30日間
            }),
        ],
    })
);

self.addEventListener('fetch', (event) => {
    if (event.request.mode === 'navigate') {
        event.respondWith((async() => {
            try {
                const networkResp = await fetch(event.request);
                return networkResp;
            } catch (error) {
                const cache = await caches.open(CACHE);
                const cachedResp = await cache.match(offlineFallbackPage);
                return cachedResp;
            }
        })());
    }
});
