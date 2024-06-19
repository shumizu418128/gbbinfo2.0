self.addEventListener('install', function(event) {
    event.waitUntil(
      caches.open('my-cache').then(function(cache) {
        const year = new Date().getFullYear(); // 今年を取得
        return cache.addAll([
          `/`,
          `/${year}/top`,
          `/${year}/ticket`,
          `/${year}/time_schedule`,
          `/${year}/stream`,
          `/${year}/result`,
          `/others/how_to_plan`,
          '/static/css/style.css',
          '/static/css/table.css',
          '/static/css/dropdown.css',
          '/static/css/button.css',
          '/static/images/background.webp',
          '/static/images/header.webp',
          '/static/scripts/script.js',
          '/static/favicon.ico',
          '/static/icon.png',
          // 他のキャッシュしたいファイルを追加
        ]);
      })
    );
  });

// フェッチイベントでキャッシュされたファイルを提供
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // キャッシュがヒットした場合はキャッシュのレスポンスを返す
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

// アクティベートイベントで古いキャッシュを削除
self.addEventListener('activate', function(event) {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
