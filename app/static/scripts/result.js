function redirect_year() {
    const year = document.getElementById("year").value;
    if (/^\d+$/.test(year)) {
        window.location.href = '/' + year + '/result';
    } else {
        console.error('Invalid year input');
    }
}
