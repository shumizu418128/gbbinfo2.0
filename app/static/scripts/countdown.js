// カウントダウンの終了日時
// GBBスタート時刻
const countDownDate1 = new Date("Nov 1, 2024 15:20:00 GMT+09:00").getTime();

// チケット販売終了日時（現在未使用）
const countDownDate2 = new Date("Oct 13, 2024 23:59:00 GMT+09:00").getTime();


function updateCountdown() {
    // 現在の日時をミリ秒で取得
    const nowMillis = new Date().getTime();

    // 終了日時までの時間差
    const distance1 = countDownDate1 - nowMillis;
    const distance2 = countDownDate2 - nowMillis;

    // 時間、分、秒、ミリ秒に変換
    const days1 = Math.floor(distance1 / (1000 * 60 * 60 * 24));
    const hours1 = Math.floor((distance1 % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes1 = Math.floor((distance1 % (1000 * 60 * 60)) / (1000 * 60));
    const seconds1 = Math.floor((distance1 % (1000 * 60)) / 1000);
    let milliseconds1 = distance1 % 1000; // ミリ秒を取得

    const days2 = Math.floor(distance2 / (1000 * 60 * 60 * 24));
    const hours2 = Math.floor((distance2 % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes2 = Math.floor((distance2 % (1000 * 60 * 60)) / (1000 * 60));
    const seconds2 = Math.floor((distance2 % (1000 * 60)) / 1000);
    let milliseconds2 = distance2 % 1000; // ミリ秒を取得

    // ミリ秒を3桁に揃える
    if (milliseconds1 < 100) {
        milliseconds1 = "0" + (milliseconds1 < 10 ? "0" : "") + milliseconds1;
    }
    if (milliseconds2 < 100) {
        milliseconds2 = "0" + (milliseconds2 < 10 ? "0" : "") + milliseconds2;
    }

    // HTMLに表示 (カウントダウンが終了したら0時間0分0秒と表示)
    document.getElementById("countdown").innerHTML =
        distance1 < 0 ? "0時間 0分 0秒" :
        days1 + "日 " + hours1 + "時間 " +
        minutes1 + "分 " + seconds1 + "秒 " + milliseconds1;


    const ticketCountdownElement = document.getElementById("ticketDeadCountdown");
    if (ticketCountdownElement) {
        ticketCountdownElement.innerHTML =
            distance2 < 0 ? "チケット販売終了！" :
            days2 + "日 " + hours2 + "時間 " +
            minutes2 + "分 " + seconds2 + "秒 " + milliseconds2;
    }

    // 次のフレームで再度呼び出し
    requestAnimationFrame(updateCountdown);
}

// 初回呼び出し
window.onload = function() {
    requestAnimationFrame(updateCountdown);
}
