const currentUrl = window.location.pathname;
const JA = document.querySelectorAll('.linkJA');
const EN = document.querySelectorAll('.linkEN');
const ZH_TW = document.querySelectorAll('.linkZH_TW');
const KO = document.querySelectorAll('.linkKO');

JA.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=ja`;
});

EN.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=en`;
});

ZH_TW.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=zh_Hant_TW`;
});

KO.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=ko`;
});
