function showPopup() {
  const backgroundPopup = document.querySelector(".background-popup");
  const popup = document.querySelector(".popup");
  if (backgroundPopup && popup) {
    backgroundPopup.style.display = "block";
    popup.style.display = "block";
  }
}

function closePopup() {
  document.querySelector(".background-popup").style.display = "none";
  document.querySelector(".popup").style.display = "none";
}
// ページが読み込まれたらポップアップを表示する
window.onload = function () {
  showPopup();
};

function toggleDropdown() {
  var dropdownContent = document.getElementById("dropdown-content");
  if (dropdownContent.style.display === "none") {
    dropdownContent.style.display = "block";
  } else {
    dropdownContent.style.display = "none";
  }
}

document.addEventListener('click', function (event) {
  var dropdownContent = document.getElementById("dropdown-content");
  var dropdownButton = document.getElementById("bottom-dropdown");
  if (dropdownContent.style.display === 'block' && !dropdownButton.contains(event.target)) {
    dropdownContent.style.display = 'none';
  }
});
