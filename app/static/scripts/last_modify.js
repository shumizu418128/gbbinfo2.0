// サーバーから最終commit時刻を取得
fetch('/last-commit')
  .then(response => {
    if (!response.ok) {
      throw new Error('データの取得に失敗しました');
    }
    return response.json();
  })
  .then(data => {
    if (data.length > 0) {
      // 最も最近のcommitを取得
      const lastCommit = data[0];
      const commitTime = new Date(lastCommit.commit.author.date);
      document.getElementById("last-deploy-time").innerText =
        commitTime.toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" }) + " JST";
    } else {
      document.getElementById("last-deploy-time").innerText =
        "取得失敗";
    }
  })
  .catch((error) => {
    console.error("取得失敗:", error);
    document.getElementById("last-deploy-time").innerText =
      error.message || "取得失敗";
  });
