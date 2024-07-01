// サーバーから最終commit時刻を取得
fetch('/last-commit')
  .then(response => {
    if (!response.ok) {
      throw new Error('unable to fetch last commit');
    }
    return response.json();
  })
  .then(data => {
    if (data.length > 0) {
      // 最も最近のcommitを取得
      const lastCommit = data[0];
      const commitSha = lastCommit.sha.substring(0, 7);
      document.getElementById("last-deploy-hash").innerText = commitSha;
    } else {
      document.getElementById("last-deploy-hash").innerText = "-";
    }
  })
  .catch((error) => {
    console.error("unable to fetch last commit:", error);
    document.getElementById("last-deploy-hash").innerText =
      error.message || "unable to fetch last commit";
  });
