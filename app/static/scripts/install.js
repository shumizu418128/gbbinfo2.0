let deferredPrompt;
const installButton = document.getElementById("installButton");

window.addEventListener("beforeinstallprompt", (e) => {
  // インストールプロンプトを表示する前に発生
  e.preventDefault();
  deferredPrompt = e;
  // ボタンを表示
  installButton.style.visibility = "visible";

  installButton.addEventListener("click", (e) => {
    // プロンプトを表示
    deferredPrompt.prompt();
    // ユーザーの応答を待つ
    deferredPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === "accepted") {
        console.log("ユーザーがアプリのインストールを受け入れました。");
      } else {
        console.log("ユーザーがアプリのインストールを拒否しました。");
      }
      deferredPrompt = null;
    });
  });
});

window.addEventListener("appinstalled", (evt) => {
  // アプリがインストールされた後に発生
  console.log("アプリがインストールされました。");
  // ボタンを非表示にする
  installButton.style.visibility = "hidden";
});
