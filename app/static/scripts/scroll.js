document.addEventListener('DOMContentLoaded', function() {
    const background = document.querySelectorAll(".background-progress-scroll");
    const progressElements = document.querySelectorAll(".progress-scroll");

    window.addEventListener('scroll', () => {
        const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
        const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrolled = (winScroll / height) * 100;

        // スクロールバーの表示・非表示
        if (winScroll <= 90) {
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
            progress.style.width = scrolled + "%";
        });
    });
});

// ページ内の全てのアンカーリンクにクリックイベントを追加
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function(e) {
        e.preventDefault(); // デフォルトの動作を防ぐ
        const targetElement = document.querySelector(this.getAttribute("href"));
        const y = targetElement.getBoundingClientRect().top + window.scrollY;

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
            const yOffset = -100; // 上部に100pxの余裕を持たせる
            const y = element.getBoundingClientRect().top + window.scrollY + yOffset;

            // スムーズスクロールを実行
            window.scrollTo({top: y, behavior: 'smooth'});
        }
    }
}

// ページ読み込み時に実行
// これonloadだとうまくいかない
parameterScroll();
