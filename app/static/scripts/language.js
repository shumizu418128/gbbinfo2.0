const currentUrl = window.location.pathname;
const JA = document.querySelectorAll('.linkJA');
const EN = document.querySelectorAll('.linkEN');
const ZH_TW = document.querySelectorAll('.linkZH_TW');
const KO = document.querySelectorAll('.linkKO');
const ZH_CN = document.querySelectorAll('.linkZH_CN');
const DE = document.querySelectorAll('.linkDE');
const MS = document.querySelectorAll('.linkMS');
const ID = document.querySelectorAll('.linkID');

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

ZH_CN.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=zh_Hans_CN`;
});

DE.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=de`;
});

MS.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=ms`;
});

ID.forEach(link => {
    link.href = `/lang?referrer=${currentUrl}&lang=id`;
});
