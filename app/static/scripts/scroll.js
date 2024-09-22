function smoothScroll(target, duration) {
  var targetElement = document.querySelector(target);
  var targetPosition = targetElement.getBoundingClientRect().top;
  var startPosition = window.pageYOffset;
  var startTime = null;

  function animation(currentTime) {
    if (startTime === null) startTime = currentTime;
    var timeElapsed = currentTime - startTime;
    var run = ease(timeElapsed, startPosition, targetPosition, duration);
    window.scrollTo(0, run);
    if (timeElapsed < duration) requestAnimationFrame(animation);
  }

  function ease(t, b, c, d) {
    t /= d / 2;
    if (t < 1) return (c / 2) * t * t + b;
    t--;
    return (-c / 2) * (t * (t - 2) - 1) + b;
  }

  requestAnimationFrame(animation);
}

document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    smoothScroll(this.getAttribute("href"), 500); // 500ms = 0.5秒

    // 少し遅延させてからスクロールする
    setTimeout(function () {
      window.scrollBy(0, -120); // 120px上にスクロール
    }, 700); // 700ms後にスクロール
  });
});

function parameterScroll() {
  var url = new URL(window.location.href);
  var target = url.searchParams.get("scroll");
  if (target) {
    var element = document.querySelector(`[name="${target}"]`);
    if (element) {
      smoothScroll(`[name="${target}"]`, 500);
      // 少し遅延させてから上へスクロールする
      setTimeout(function () {
        window.scrollBy(0, -120); // 120px上にスクロール
      }, 700); // 700ms後にスクロール
    }
  }
}

// ページ読み込み時に実行
parameterScroll();
