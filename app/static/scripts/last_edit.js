fetch("/last-commit")
  .then((response) => {
    if (!response.ok) {
      throw new Error("最終更新：取得失敗");
    }
    return response.json();
  })
  .then((data) => {
    if (data.length > 0) {
      const lastCommit = data[0];
      const commitDate = new Date(lastCommit.commit.author.date).toLocaleString(
        "ja-JP",
        { timeZone: "Asia/Tokyo" }
      );
      document.getElementById("last-deploy-date").innerText = `最終更新：${commitDate}`;
    } else {
      document.getElementById("last-deploy-date").innerText = "-";
    }
  })
  .catch((error) => {
    console.error("最終更新：取得失敗", error);
    document.getElementById("last-deploy-date").innerText =
      error.message || "最終更新：取得失敗";
  });
