document.addEventListener('DOMContentLoaded', function() {
    // ヘッダーdropdown
    const headers = document.querySelectorAll('h1, h2');
    const lastHeader = headers[headers.length - 1];
    const headerArray = lastHeader && lastHeader.id === "bottom-search-menu" ? Array.from(headers).slice(0, -1) : Array.from(headers);
    const dropdown = document.querySelector('.headerDropdown');
    const offsetTops = headerArray.map(header => header.offsetTop);

    headerArray.forEach((header, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = header.textContent.trim();
        dropdown.appendChild(option);
    });

    dropdown.addEventListener('change', function() {
        scrollToHeader(headers[this.value]);
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

    // スクロールイベントでドロップダウンの選択を更新 + スクロールバー
    window.addEventListener('scroll', () => {
        updateDropdownSelection(headerArray, dropdown, offsetTops);
        updateProgressBar();
    });

    // スクロールバー
    const background = document.querySelectorAll(".background-progress-scroll");
    const progressElements = document.querySelectorAll(".progress-scroll");

    function updateProgressBar() {
        const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
        const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrollPercentage = (winScroll / height) * 100;
        const scrollAbsolute = window.scrollY + 50;
        const h1_position = document.querySelector("h1").offsetTop;

        // スクロール位置が最初の<h1>要素より上にある場合、プログレスバーと背景を非表示にする
        if (scrollAbsolute <= h1_position) {
            background.forEach(bg => bg.style.display = "none");
            progressElements.forEach(progress => progress.style.display = "none");
        } else {
            background.forEach(bg => bg.style.display = "block");
            progressElements.forEach(progress => progress.style.display = "block");
        }

        // スクロールバーの長さを更新
        progressElements.forEach(progress => {
            const roundedScrollPercentage = Math.round(scrollPercentage / 10) * 10;
            progress.style.width = roundedScrollPercentage + "%";
        });
    }

    function updateDropdownSelection(headerArray, dropdown, offsetTops) {
        const scrollPosition = window.scrollY + 51;

        if (scrollPosition < offsetTops[0]) {
            dropdown.style.display = 'none';
        } else {
            for (let index = headerArray.length - 1; index >= 0; index--) {
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
    }

    // ページ内の全てのアンカーリンクにクリックイベントを追加
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener("click", function(e) {
            e.preventDefault();
            const targetElement = document.querySelector(this.getAttribute("href"));
            scrollToHeader(targetElement);
        });
    });

    // URLのパラメータに基づいてスクロールを実行する関数
    function parameterScroll() {
        const url = new URL(window.location.href);
        const target = url.searchParams.get("scroll");
        if (target) {
            const element = document.querySelector(`[name="${target}"]`);
            if (element) {
                scrollToHeader(element);
            }
        }
    }

    function scrollToHeader(headerElement) {
        const y = headerElement.getBoundingClientRect().top + window.scrollY - 50;
        window.scrollTo({top: y, behavior: 'smooth'});
    }

    parameterScroll();
});

function redirect_year(page_name) {
    const year = document.getElementById("year").value;
    if (/^\d+$/.test(year)) {
        window.location.href = '/' + year + '/' + page_name;
    } else {
        console.error('Invalid year input');
    }
}
