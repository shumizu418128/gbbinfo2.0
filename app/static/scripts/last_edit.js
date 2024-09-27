// '/last-commit' エンドポイントから最新のコミット情報を取得
fetch("/last-commit")
  .then((response) => {
    // レスポンスが正常でない場合はエラーをスロー
    if (!response.ok) {
      throw new Error("最終更新：取得失敗");
    }
    // レスポンスをJSON形式に変換して返す
    return response.json();
  })
  .then((data) => {
    // 取得したデータからコミット日を取得し、フォーマットする
    const commitDate = data.length > 0 ?
      new Date(data[0].commit.author.date).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" }) :
      "-";

    // 最終更新日をHTML要素に表示
    document.getElementById("last-deploy-date").innerText = `最終更新：${commitDate}`;

    // last-deploy-date2が存在する場合のみ更新
    const lastDeployDate2 = document.getElementById("last-deploy-date2");
    if (lastDeployDate2) {
      lastDeployDate2.innerText = `最終更新：${commitDate}`;
    }
  })
  .catch((error) => {
    // エラーが発生した場合はコンソールにエラーメッセージを表示
    console.error("最終更新：取得失敗", error);
    // 最終更新失敗のメッセージをHTML要素に表示
    document.getElementById("last-deploy-date").innerText = "最終更新：取得失敗";

    // last-deploy-date2が存在する場合のみ更新
    const lastDeployDate2 = document.getElementById("last-deploy-date2");
    if (lastDeployDate2) {
      lastDeployDate2.innerText = "最終更新：取得失敗";
    }
  });
