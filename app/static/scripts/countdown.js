// カウントダウンの終了日時
// GBB開催日時
const countDownDate = new Date("Oct 31, 2025 14:00:00 GMT+09:00").getTime();

function updateCountdown() {
    const nowMillis = new Date().getTime();
    const distance = countDownDate - nowMillis;

    // フォーマット関数
    function formatCountdown(distance) {
        if (distance <= 0) return "and that's TIME!";

        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        const milliseconds = Math.floor(distance % 1000);

        return `${days} days ${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")} ${String(milliseconds).padStart(3, "0")}`;
    }

    document.getElementById("countdown").innerHTML = formatCountdown(distance);
    requestAnimationFrame(updateCountdown);
}
requestAnimationFrame(updateCountdown);
