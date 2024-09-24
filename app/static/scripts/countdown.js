// カウントダウンの終了日時
const countDownDate = new Date("Nov 1, 2024 00:00:00 GMT+09:00").getTime();

function updateCountdown() {
  // 現在の日時をミリ秒で取得
  const nowMillis = new Date().getTime();

  // 終了日時までの時間差
  const distance = countDownDate - nowMillis;

  // 時間、分、秒、ミリ秒に変換
  const days = Math.floor(distance / (1000 * 60 * 60 * 24));
  const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((distance % (1000 * 60)) / 1000);
  let milliseconds = distance % 1000;  // ミリ秒を取得

  // ミリ秒を3桁に揃える
  if (milliseconds < 100) {
    milliseconds = "0" + (milliseconds < 10 ? "0" : "") + milliseconds;
  }

  // HTMLに表示
  document.getElementById("countdown").innerHTML = days + "日 " + hours + "時間 " +
    minutes + "分 " + seconds + "秒 " + milliseconds;

  // カウントダウンが終了したらテキストを表示
  if (distance < 0) {
    document.getElementById("countdown").innerHTML = "EXPIRED";
  } else {
    // 次のフレームで再度呼び出し
    requestAnimationFrame(updateCountdown);
  }
}

// 初回呼び出し
requestAnimationFrame(updateCountdown);
