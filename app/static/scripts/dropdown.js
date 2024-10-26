document.addEventListener('DOMContentLoaded', function() {
    const headers = document.querySelectorAll('h2');
    const headerArray = Array.from(headers).slice(0, -1); // 最後の要素を除外
    const dropdown = document.querySelector('.headerDropdown');
    const offsetTops = headerArray.map(header => header.offsetTop);

    // h2要素のテキストを使用してドロップダウンオプションを生成
    headerArray.forEach((header, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = header.textContent.trim(); // テキストをトリムして設定
        dropdown.appendChild(option);
    });

    // ドロップダウンメニューの変更を監視して、選択されたh2要素にスクロール
    dropdown.addEventListener('change', function() {
        const selectedHeader = headers[this.value];
        selectedHeader.scrollIntoView({ behavior: 'smooth' });
    });

    // スクロールイベントでドロップダウンの選択を更新
    window.addEventListener('scroll', () => {
        const scrollPosition = window.scrollY;

        // 画面内最初のh2より上を見ている場合、dropdown非表示
        if (scrollPosition < offsetTops[0]) {
            dropdown.style.display = 'none';
        }
        else {
            // ヘッダーh2のスクロール固定
            for (let index = 0; index < headerArray.length; index++) {
                // 最後の要素か、次の要素のoffsetTopが現在のスクロール位置よりも大きい場合
                if ((scrollPosition >= offsetTops[index]) && (index === headerArray.length - 1 || scrollPosition < offsetTops[index + 1])) {
                    dropdown.value = index; // ドロップダウンの選択を更新
                    dropdown.style.display = ''; // ドロップダウンを表示
                    break; // ループ処理を終了
                }
            }
        }
    });
});
