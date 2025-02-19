document.addEventListener('DOMContentLoaded', function() {
    const headers = document.querySelectorAll('h1, h2');
    const lastHeader = headers[headers.length - 1];
    const headerArray = lastHeader && lastHeader.id === "bottom-search-menu" ? Array.from(headers).slice(0, -1) : Array.from(headers);
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
        const y = selectedHeader.getBoundingClientRect().top + window.scrollY - 50;
        window.scrollTo({
            top: y,
            behavior: 'smooth'
        });
    });

    function getTextWidth(text, fontSize) {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        context.font = `${fontSize}px 'Noto Sans JP'`;
        return context.measureText(text).width;
    }

    function calculateFontSize(text, maxWidth) {
        let fontSize = 24;
        let textWidth = getTextWidth(text, fontSize);
        while (textWidth >= maxWidth) {
            fontSize -= 1;
            textWidth = getTextWidth(text, fontSize);
        }
        return fontSize;
    }

    // スクロールイベントでドロップダウンの選択を更新
    window.addEventListener('scroll', () => {
        const scrollPosition = window.scrollY + 51;

        // 画面内最初のh2より上を見ている場合、dropdown非表示
        if (scrollPosition < offsetTops[0]) {
            dropdown.style.display = 'none';
        } else {
            for (let index = headerArray.length - 1; index >= 0; index--) {
                // 最後の要素か、次の要素のoffsetTopが現在のスクロール位置よりも大きい場合
                if ((scrollPosition >= offsetTops[index])) {
                    dropdown.value = index;
                    dropdown.style.display = '';
                    const dropdownWidth = dropdown.offsetWidth - 80;
                    const fontSize = calculateFontSize(headerArray[index].textContent, dropdownWidth);
                    dropdown.style.fontSize = `${fontSize}px`;
                    break;
                }
            }
        }
    });
});
