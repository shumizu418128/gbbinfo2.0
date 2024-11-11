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

function search_participants(year) {
    const input = document.getElementById('keyword').value;
    const loadingElement = document.getElementById('loading');

    if (input) { // 少なくとも1文字以上で検索を開始
        loadingElement.textContent = `検索中：${input}`; // スピナーの上に質問を表示
        loadingElement.style.display = 'block';

        fetch(`/${year}/search_participants`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({keyword: input})
        })
        .then(response => response.json())
        .then(data => {
            const table = data.map(participant =>
                `<tr>
                    <td>
                        ${participant.is_cancelled ? '【辞退】<br><s>' : ''}
                        ${participant.name}
                        <div id="small-text">${participant.members}</div>
                        ${participant.is_cancelled ? '</s>' : ''}
                    </td>
                    <td>
                        ${participant.is_cancelled ? `<s>${participant.category}</s>` : participant.category}
                    </td>
                    <td style="${participant.ticket_class.length > 11 ? 'font-size: 12px;' : ''}">
                        ${participant.is_cancelled ? `<s>${participant.ticket_class}</s>` : participant.ticket_class}
                    </td>
                </tr>`
            ).join('');
            if (table != '') {
                document.getElementById('participants-search-result').innerHTML = `${table}`;
                loadingElement.style.display = 'none';
            }
            else {
                document.getElementById('participants-search-result').innerHTML = '<p>-</p>';
                loadingElement.style.display = 'none';
            }
        })
        .catch(error => console.error('Error:', error));
    } else {
        document.getElementById('participants-search-result').innerHTML = '<p>-</p>';
        loadingElement.style.display = 'none';
    }
}
