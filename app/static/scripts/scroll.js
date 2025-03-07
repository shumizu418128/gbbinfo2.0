document.addEventListener('DOMContentLoaded', function() {
    const background = document.querySelectorAll(".background-progress-scroll");
    const progressElements = document.querySelectorAll(".progress-scroll");

    window.addEventListener('scroll', () => {
        const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
        const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrollPercentage = (winScroll / height) * 100;
        const scrollAbsolute = window.scrollY + 50;
        const h1_position = document.querySelector("h1").offsetTop;

        // スクロールバーの表示・非表示
        if (scrollAbsolute <= h1_position) {
            background.forEach(bg => {
                bg.style.display = "none";
            });
            progressElements.forEach(progress => {
                progress.style.display = "none";
            });
        }
        else {
            background.forEach(bg => {
                bg.style.display = "block";
            });
            progressElements.forEach(progress => {
                progress.style.display = "block";
            });
        }

        // スクロールバーの長さ設定
        progressElements.forEach(progress => {
            progress.style.width = scrollPercentage + "%";
        });
    });
});

// ページ内の全てのアンカーリンクにクリックイベントを追加
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function(e) {
        e.preventDefault(); // デフォルトの動作を防ぐ
        const targetElement = document.querySelector(this.getAttribute("href"));
        const y = targetElement.getBoundingClientRect().top + window.scrollY - 50;

        // スムーズスクロールを実行
        window.scrollTo({top: y, behavior: 'smooth'});
    });
});

// URLのパラメータに基づいてスクロールを実行する関数
function parameterScroll() {
    const url = new URL(window.location.href);
    const target = url.searchParams.get("scroll"); // スクロール対象を取得
    if (target) {
        const element = document.querySelector(`[name="${target}"]`); // 対象要素を取得
        if (element) {
            const y = element.getBoundingClientRect().top + window.scrollY - 50;

            // スムーズスクロールを実行
            window.scrollTo({top: y, behavior: 'smooth'});
        }
    }
}

// ページ読み込み時に実行
document.addEventListener('DOMContentLoaded', parameterScroll);
