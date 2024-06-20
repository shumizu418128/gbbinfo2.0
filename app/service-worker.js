
  self.addEventListener('fetch', function(event) {
    event.respondWith(
      // ネットワークからリクエストを取得する
      fetch(event.request)
        .then(function(response) {
          // レスポンスが正常であれば、キャッシュを開き、そのレスポンスをキャッシュに保存する
          if (response && response.status === 200) {
            var responseToCache = response.clone();
            caches.open('my-cache')
              .then(function(cache) {
                cache.put(event.request, responseToCache);
              });
          }
          return response; // レスポンスを返す
        })
        .catch(function() {
          // ネットワークにアクセスできない場合はキャッシュを使用する
          return caches.match(event.request);
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
