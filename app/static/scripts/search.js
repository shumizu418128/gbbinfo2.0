// フォームの送信イベントを取得
function handleFormSubmit(event) {
    // デフォルトの送信を防ぐ
    event.preventDefault();

    // フォームデータを取得
    const formData = new FormData(this);

    // フォームデータのうちquestionの内容をローディング画面に表示
    const question = formData.get('question'); // 'question'フィールドの値を取得
    const loadingElement = document.getElementById('loading');

    // スピナーを表示するためのHTMLを設定
    loadingElement.innerHTML = `<div>検索中：${question}</div><br>`; // スピナーの上に質問を表示
    loadingElement.style.display = 'block';

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
    });
}

// 各フォームにイベントリスナーを追加
if (document.getElementById('searchForm')) {
    document.getElementById('searchForm').onsubmit = handleFormSubmit;
}
if (document.getElementById('searchForm2')) {
    document.getElementById('searchForm2').onsubmit = handleFormSubmit;
}
