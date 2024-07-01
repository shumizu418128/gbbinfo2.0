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
      const commitSha = lastCommit.sha.substring(0, 6);
      document.getElementById("last-deploy-hash").innerText = commitSha;
    } else {
      document.getElementById("last-deploy-hash").innerText = "-";
    }
  })
  .catch((error) => {
    console.error("取得失敗:", error);
    document.getElementById("last-deploy-hash").innerText =
      error.message || "取得失敗";
  });
