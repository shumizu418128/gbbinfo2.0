function redirect_year() {
    const year = document.getElementById("year").value;
    window.location.href = '/' + year + '/result';
}
