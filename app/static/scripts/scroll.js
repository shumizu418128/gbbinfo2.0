// スムーズスクロールを実行する関数
function smoothScroll(target, duration) {
    // 対象要素を取得
    const targetElement = document.querySelector(target);
    // スクロール位置を計算（120pxの余裕を持たせる）
    const targetPosition = targetElement.getBoundingClientRect().top - 120;
    // 現在のスクロール位置を取得
    const startPosition = window.scrollY;
    let startTime = null;

    // アニメーションを実行する関数
    function animation(currentTime) {
        // 開始時間を設定
        if (startTime === null) startTime = currentTime;
        // 経過時間を計算
        const timeElapsed = currentTime - startTime;
        // スクロール位置を計算
        const run = ease(timeElapsed, startPosition, targetPosition, duration);
        // スクロールを実行
        window.scrollTo(0, run);
        // 経過時間が指定の時間未満であれば再度アニメーションをリクエスト
        if (timeElapsed < duration) requestAnimationFrame(animation);
    }

    // イージング関数
    function ease(t, b, c, d) {
        t /= d / 2;
        if (t < 1) return (c / 2) * t * t + b;
        t--;
        return (-c / 2) * (t * (t - 2) - 1) + b;
    }

    // アニメーションを開始
    requestAnimationFrame(animation);
}

// ページ内の全てのアンカーリンクにクリックイベントを追加
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function(e) {
        e.preventDefault(); // デフォルトの動作を防ぐ
        // スムーズスクロールを実行
        smoothScroll(this.getAttribute("href"), 400); // 400ms
    });
});

// URLのパラメータに基づいてスクロールを実行する関数
function parameterScroll() {
    const url = new URL(window.location.href);
    const target = url.searchParams.get("scroll"); // スクロール対象を取得
    if (target) {
        const element = document.querySelector(`[name="${target}"]`); // 対象要素を取得
        if (element) {
            // スムーズスクロールを実行
            smoothScroll(`[name="${target}"]`, 400);
        }
    }
}

// ページ読み込み時に実行
window.onload = function() {
    parameterScroll();
};
