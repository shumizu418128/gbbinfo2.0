document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();

    document.querySelector(this.getAttribute("href")).scrollIntoView({
      behavior: "smooth",
      block: "start", // 'start', 'center', 'end', or 'nearest'
    });

    // 少し遅延させてからスクロールする
    setTimeout(function () {
      window.scrollBy(0, -120); // 100px上にスクロール
    }, 500); // 500ms後にスクロール
  });
});
