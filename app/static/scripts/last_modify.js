// GitHub APIを使用して最終commit時刻を取得
const token = process.env.GITHUB_TOKEN; // 環境変数からパーソナルアクセストークンを取得

fetch("https://api.github.com/repos/shumizu418128/gbbinfo2.0/commits", {
  headers: {
    'Authorization': `token ${token}`
  }
})
  .then((response) => {
    if (response.status === 403) {
      throw new Error("APIのレートリミットに達しました。しばらくしてから再試行してください。");
    }
    return response.json();
  })
  .then((data) => {
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
