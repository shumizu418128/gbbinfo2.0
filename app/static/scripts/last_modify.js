// '/last-commit' エンドポイントから最新のコミット情報を取得する
fetch('/last-commit')
  .then(response => {
    // レスポンスが正常でない場合はエラーをスロー
    if (!response.ok) {
      throw new Error('unable to fetch last commit');
    }
    // レスポンスをJSON形式に変換して返す
    return response.json();
  })
  .then(data => {
    // 取得したデータが存在する場合
    if (data.length > 0) {
      const lastCommit = data[0]; // 最後のコミット情報を取得
      const commitSha = lastCommit.sha.substring(0, 7); // SHAの最初の7文字を取得
      // HTML要素にコミットSHAを表示
      document.getElementById("last-deploy-hash").innerText = commitSha;
    } else {
      // データが存在しない場合はハイフンを表示
      document.getElementById("last-deploy-hash").innerText = "-";
    }
  })
  .catch((error) => {
    // エラーが発生した場合はコンソールにエラーメッセージを表示
    console.error("unable to fetch last commit:", error);
    // エラーメッセージをHTML要素に表示
    document.getElementById("last-deploy-hash").innerText =
      error.message || "unable to fetch last commit";
  });
