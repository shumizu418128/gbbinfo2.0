function redirect_year(page_name) {
    const year = document.getElementById("year").value;
    if (/^\d+$/.test(year)) {
        window.location.href = '/' + year + '/' + page_name;
    } else {
        console.error('Invalid year input');
    }
}
