document.addEventListener('DOMContentLoaded', function() {
    const headers = document.querySelectorAll('h2');
    const headerArray = Array.from(headers);
    const offsetTops = headerArray.map(header => header.offsetTop);

    window.addEventListener('scroll', () => {
        const scrollPosition = window.scrollY + window.innerHeight * 0.3;

        headerArray.forEach((header, index) => {
            if (scrollPosition >= offsetTops[index] && (index === headerArray.length - 1 || scrollPosition < offsetTops[index + 1])) {
                header.classList.add('sticky');
            } else {
                header.classList.remove('sticky');
            }
        });
    });
});

// スクロールに応じてプログレスバーを更新するJavaScript
window.onscroll = function() {
    const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
    const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrolled = (winScroll / height) * 100;
    const progressTop = document.getElementById("progressTop");
    const progressBottom = document.getElementById("progressBottom");

    progressTop.style.width = scrolled + "%";
    progressBottom.style.width = scrolled + "%";

    if (scrolled === 100) {
        progressTop.style.borderTopRightRadius = "0";
        progressTop.style.borderBottomRightRadius = "0";
        progressBottom.style.borderTopRightRadius = "0";
        progressBottom.style.borderBottomRightRadius = "0";
    }
    else {
        progressTop.style.borderTopRightRadius = "6px";
        progressTop.style.borderBottomRightRadius = "6px";
        progressBottom.style.borderTopRightRadius = "6px";
        progressBottom.style.borderBottomRightRadius = "6px";
    }

    // 色を動的に変更（白からオレンジへ）
    const rTop = 255 - (255 - 240) * (scrolled / 100);
    const gTop = 255 - (255 - 99) * (scrolled / 100);
    const bTop = 255 - (255 - 47) * (scrolled / 100);

    // 色を動的に変更（青から白へ）
    const rBottom = 0 + (255 * (scrolled / 100));
    const gBottom = 68 + (187 * (scrolled / 100));
    const bBottom = 204 + (51 * (scrolled / 100));

    progressTop.style.backgroundColor = `rgb(${rTop}, ${gTop}, ${bTop})`;
    progressBottom.style.backgroundColor = `rgb(${rBottom}, ${gBottom}, ${bBottom})`;
};

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
// これonloadだとうまくいかない
parameterScroll();
