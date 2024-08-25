// フォームの送信イベントを取得
document.getElementById('searchForm').onsubmit = function(event) {
    // デフォルトの送信を防ぐ
    event.preventDefault();

    // ローディング画面を表示
    document.getElementById('loading').style.display = 'block';

    // フォームデータを取得
    const formData = new FormData(this);

    // フェッチAPIを使用してデータを送信
    fetch(this.action, {
        method: "POST", // POSTメソッドで送信
        headers: {
            'Content-Type': 'application/json' // JSON形式で送信
        },
        body: JSON.stringify(Object.fromEntries(formData)) // データをJSON形式に変換して送信
    })
    .then(response => response.json()) // レスポンスをjsonとして取得
    .then(data => {
        // 取得したURLにリダイレクト
        window.location.href = data.url;
    })
};
