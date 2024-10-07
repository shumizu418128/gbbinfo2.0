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
if (document.getElementById('search-form-top')) {
    document.getElementById('search-form-top').onsubmit = handleFormSubmit;
}
if (document.getElementById('search-form-bottom')) {
    document.getElementById('search-form-bottom').onsubmit = handleFormSubmit;
}
if (document.getElementById('search-form-nav')) {
    document.getElementById('search-form-nav').onsubmit = handleFormSubmit;
}

document.getElementById('bottom-navigation-search').addEventListener('click', function() {
    const searchMenu = document.getElementById('search-menu-nav');
    // メニューを開く
    if (searchMenu.style.display === 'none' || searchMenu.style.display === '') {
        openSearchMenu();
    // メニューを閉じる
    } else {
        closeSearchMenu();
    }
});

// メニューの外側をクリックしたときにメニューを非表示にする処理
document.addEventListener('click', function(event) {
    const searchMenu = document.getElementById('search-menu-nav');
    const bottomNav = document.querySelector('.bottom-navigation');
    // クリックされた要素がメニューまたはボトムナビゲーションでない場合
    if (searchMenu.style.display === 'block' && !bottomNav.contains(event.target)) {
        closeSearchMenu();
    }
});

function closeSearchMenu() {
    const searchMenu = document.getElementById('search-menu-nav');
    const searchIcon = document.getElementById('search-icon');
    const closeIcon = document.getElementById('close-icon');
    const searchMsg = document.getElementById('search-msg');

    searchMenu.style.display = 'none'; // メニューを非表示
    searchMsg.textContent = 'さがす'; // 検索ボタンのテキストを変更
    searchIcon.style.display = 'block'; // 検索アイコンを表示
    closeIcon.style.display = 'none'; // 閉じるアイコンを非表示
}

function openSearchMenu() {
    const searchMenu = document.getElementById('search-menu-nav');
    const searchIcon = document.getElementById('search-icon');
    const closeIcon = document.getElementById('close-icon');
    const searchMsg = document.getElementById('search-msg');

    searchMenu.style.display = 'block'; // メニューを表示
    searchMsg.textContent = 'とじる';
    searchIcon.style.display = 'none'; // 検索アイコンを非表示
    closeIcon.style.display = 'block'; // 閉じるアイコンを表示
}
