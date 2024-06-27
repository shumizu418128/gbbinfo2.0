function showPopup() {
    document.querySelector(".overlay").style.display = "block";
    document.querySelector(".popup").style.display = "block";
}

function closePopup() {
    document.querySelector(".overlay").style.display = "none";
    document.querySelector(".popup").style.display = "none";
}
// ページが読み込まれたらポップアップを表示する
window.onload = function() {
    showPopup();
}
