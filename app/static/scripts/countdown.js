// カウントダウンの終了日時
const countDownDate1 = new Date("Oct 31, 2025 0:00:00 GMT+09:00").getTime();
const countDownDate2 = new Date("Oct 13, 2024 23:59:00 GMT+09:00").getTime();

function updateCountdown() {
    const nowMillis = new Date().getTime();

    const distance1 = countDownDate1 - nowMillis;
    // const distance2 = countDownDate2 - nowMillis;

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

    // GBB開催日
    document.getElementById("countdown").innerHTML = formatCountdown(distance1);

    // チケット販売カウントダウン（オプション）
    // const ticketCountdownElement = document.getElementById("ticketDeadCountdown");
    // if (ticketCountdownElement) {
    //     ticketCountdownElement.innerHTML = formatCountdown(distance2);
    // }
    requestAnimationFrame(updateCountdown);
}
requestAnimationFrame(updateCountdown);
