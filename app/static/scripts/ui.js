// ポップアップの表示
function showPopup() {
    const backgroundPopup = document.querySelector(".background-popup");
    const popup = document.querySelector(".popup");
    if (backgroundPopup && popup) {
        backgroundPopup.style.display = "block";
        popup.style.display = "block";
    }
}

// ポップアップの非表示
function closePopup() {
    const backgroundPopup = document.querySelector(".background-popup");
    const popup = document.querySelector(".popup");
    if (backgroundPopup && popup) {
        backgroundPopup.style.display = "none";
        popup.style.display = "none";
    }
}

// ドロップダウンの開閉
function toggleDropdown() {
    var dropdownContent = document.getElementById("dropdown-content");
    dropdownContent.style.display = dropdownContent.style.display === "none" ? "block" : "none";
}

// PWA インストールボタンの処理
let deferredPrompt;
const installButton = document.getElementById("installButton");

function handleInstallButtonClick() {
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then((choiceResult) => {
        if (choiceResult.outcome === "accepted") {
            console.log("ユーザーがアプリのインストールを受け入れました。");
        } else {
            console.log("ユーザーがアプリのインストールを拒否しました。");
        }
        deferredPrompt = null;
    });
}

function handleBeforeInstallPrompt(e) {
    e.preventDefault();
    deferredPrompt = e;
    installButton.style.visibility = "visible";
}

function handleAppInstalled() {
    console.log("アプリがインストールされました。");
    installButton.style.visibility = "hidden";
}

// イベントリスナーの登録
window.onload = function() {
    showPopup();
};

// ドロップダウンのクリックイベント
function handleDocumentClick(event) {
    var dropdownContent = document.getElementById("dropdown-content");
    var dropdownButton = document.getElementById("bottom-dropdown");
    if (dropdownContent && dropdownButton && dropdownContent.style.display === 'block') {
        if (!dropdownButton.contains(event.target)) {
            dropdownContent.style.display = 'none';
        }
    }
}

document.addEventListener('click', handleDocumentClick);

window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
window.addEventListener("appinstalled", handleAppInstalled);

if (installButton) {
    installButton.addEventListener("click", handleInstallButtonClick);
}

// 注目キーワードの表示
function showKeywordOptions(keyword) {
    showPopup();

    if (keyword === 'wildcard') {
        document.getElementById('wildcardOptions').style.display = 'block';
        document.getElementById('resultOptions').style.display = 'none';
    } else if (keyword === 'result') {
        document.getElementById('resultOptions').style.display = 'block';
        document.getElementById('wildcardOptions').style.display = 'none';
    }
}
