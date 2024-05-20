// カウントダウンの終了日時
var countDownDate = new Date("Nov 1, 2024 00:00:00").getTime();

// 1ミリ秒ごとに更新
var countdownfunction = setInterval(function() {

  // 現在の日時
  var now = new Date().getTime();

  // 今の年
    var year = new Date().getFullYear();

  // 終了日時までの時間差
  var distance = countDownDate - now;

  // 時間、分、秒、ミリ秒に変換
  var days = Math.floor(distance / (1000 * 60 * 60 * 24));
  var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
  var seconds = Math.floor((distance % (1000 * 60)) / 1000);
  var milliseconds = distance % 1000;  // ミリ秒を取得

    // ミリ秒を3桁に揃える
    if(milliseconds < 100){
        milliseconds = "0" + (milliseconds < 10 ? "0" : "") + milliseconds;
        }
  // HTMLに表示
  document.getElementById("countdown").innerHTML = days + "日 " + hours + "時間 "
  + minutes + "分 " + seconds + "秒 " + milliseconds;

  // カウントダウンが終了したらテキストを表示
  if (distance < 0) {
    clearInterval(countdownfunction);
    document.getElementById("countdown").innerHTML = "EXPIRED";
  }
}, 1);  // 1ミリ秒ごとに更新
