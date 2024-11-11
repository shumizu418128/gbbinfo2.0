const currentUrl = window.location.pathname;
const JA = document.querySelectorAll('.linkJA');
const EN = document.querySelectorAll('.linkEN');
const ZH = document.querySelectorAll('.linkZH');

JA.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=ja`;
});

EN.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=en`;
});
ZH.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=zh`;
});
