fetch("/last-commit")
  .then((response) => {
    if (!response.ok) {
      throw new Error("最終更新：取得失敗");
    }
    return response.json();
  })
  .then((data) => {
    const commitDate = data.length > 0 ?
      new Date(data[0].commit.author.date).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" }) :
      "-";

    document.getElementById("last-deploy-date").innerText = `最終更新：${commitDate}`;

    // last-deploy-date2が存在する場合のみ更新
    const lastDeployDate2 = document.getElementById("last-deploy-date2");
    if (lastDeployDate2) {
      lastDeployDate2.innerText = `最終更新：${commitDate}`;
    }
  })
  .catch((error) => {
    console.error("最終更新：取得失敗", error);
    document.getElementById("last-deploy-date").innerText = "最終更新：取得失敗";

    // last-deploy-date2が存在する場合のみ更新
    const lastDeployDate2 = document.getElementById("last-deploy-date2");
    if (lastDeployDate2) {
      lastDeployDate2.innerText = "最終更新：取得失敗";
    }
  });
