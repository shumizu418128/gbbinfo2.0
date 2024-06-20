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
        // キャッシュがヒットした場合
        if (response) {
          // キャッシュの更新がないか確認する
          fetch(event.request).then(function(networkResponse) {
            // ネットワークレスポンスがある場合
            if (networkResponse && networkResponse.status === 200) {
              // キャッシュを開く
              caches.open('my-cache').then(function(cache) {
                // キャッシュにネットワークレスポンスを保存する
                cache.put(event.request, networkResponse.clone());
              });
            }
          });
          return response;
        }
        // キャッシュがヒットしなかった場合
        return fetch(event.request).then(function(networkResponse) {
          // ネットワークレスポンスがある場合
          if (networkResponse && networkResponse.status === 200) {
            // キャッシュを開く
            caches.open('my-cache').then(function(cache) {
              // キャッシュにネットワークレスポンスを保存する
              cache.put(event.request, networkResponse.clone());
            });
          }
          return networkResponse;
        });
      })
  );
});
// アクティベートイベントで古いキャッシュを削除
self.addEventListener('activate', function(event) {
  const cacheWhitelist = "my-cache";
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

self.addEventListener('sync', function(event) {
  if (event.tag == 'update-content') {
    event.waitUntil(
      fetch('/latest-updates').then(function(response) {
        return response.json();
      }).then(function(data) {
        // ここで最新情報をキャッシュまたはページに更新する処理を行う
        console.log('最新情報が更新されました', data);
      }).catch(function(err) {
        console.error('最新情報の取得に失敗しました', err);
      })
    );
  }
});
