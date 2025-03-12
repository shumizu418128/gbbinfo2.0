// カウントダウンの終了日時 (GBB開催日時)
const countdownEndTime = new Date("Oct 31, 2025 14:00:00 GMT+09:00").getTime();

function updateTimer() {
    const nowTime = new Date().getTime();
    const timeLeft = countdownEndTime - nowTime;

    function formatTimeLeft(timeLeft) {
        if (timeLeft <= 0) return "and that's TIME!";

        const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
        const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
        const milliseconds = Math.floor(timeLeft % 1000);

        return `${days} days ${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")} ${String(milliseconds).padStart(3, "0")}`;
    }

    document.getElementById("countdown").innerHTML = formatTimeLeft(timeLeft);
    requestAnimationFrame(updateTimer);
}

requestAnimationFrame(updateTimer);
