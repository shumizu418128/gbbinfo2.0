// 検索フォームの送信処理
function handleSearchFormSubmit(event) {
    event.preventDefault();
    const formData = new FormData(this);
    const question = formData.get('question');
    const loadingElement = document.getElementById('loading');

    loadingElement.innerHTML = `<div>検索中：${question}</div><br>`;
    loadingElement.style.display = 'block';

    fetch(this.action, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(Object.fromEntries(formData))
    })
    .then(response => response.json())
    .then(data => {
        window.location.href = data.url;
    });
}

// ナビゲーションメニューの開閉処理
function toggleSearchMenu() {
    const searchMenu = document.getElementById('search-menu-nav');
    searchMenu.style.display = (searchMenu.style.display === 'none' || searchMenu.style.display === '') ? 'block' : 'none';

    const searchIcon = document.getElementById('search-icon');
    const closeIcon = document.getElementById('close-icon');
    const searchMsg = document.getElementById('search-msg');

    if (searchMenu.style.display === 'block') {
        searchMsg.textContent = 'とじる';
        searchIcon.style.display = 'none';
        closeIcon.style.display = 'block';
    } else {
        searchMsg.textContent = 'さがす';
        searchIcon.style.display = 'block';
        closeIcon.style.display = 'none';
    }
}

// 参加者検索処理
function searchParticipants(year) {
    const input = document.getElementById('keyword').value;
    const loadingElement = document.getElementById('loading');

    if (input) {
        loadingElement.textContent = `検索中：${input}`;
        loadingElement.style.display = 'block';

        fetch(`/${year}/search_participants`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({keyword: input})
        })
        .then(response => response.json())
        .then(data => {
            const table = data.map(participant =>
                `<tr>
                    <td>
                        ${participant.is_cancelled ? '【辞退】<br><s>' : ''}
                        ${participant.name}
                        <div id="small-text">${participant.members}</div>
                        ${participant.is_cancelled ? '</s>' : ''}
                    </td>
                    <td>
                        ${participant.is_cancelled ? `<s>${participant.category}</s>` : participant.category}
                    </td>
                    <td style="${participant.ticket_class.length > 11 ? 'font-size: 12px;' : ''}">
                        ${participant.is_cancelled ? `<s>${participant.ticket_class}</s>` : participant.ticket_class}
                    </td>
                </tr>`
            ).join('');

            const resultElement = document.getElementById('participants-search-result');
            resultElement.innerHTML = table ? table : '<p>-</p>';
            loadingElement.style.display = 'none';
        })
        .catch(error => console.error('Error:', error));
    } else {
        document.getElementById('participants-search-result').innerHTML = '<p>-</p>';
        loadingElement.style.display = 'none';
    }
}

// 検索候補の表示処理
function setupSearchSuggestions(searchForm) {
    const suggestionsContainer = searchForm.closest('.search-form-1').nextElementSibling;

    searchForm.addEventListener('input', function() {
        const query = this.querySelector('input').value;

        if (query.length > 0) {
            fetch('/search_suggestions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ input: query })
            })
            .then(response => response.json())
            .then(data => {
                suggestionsContainer.innerHTML = '';
                suggestionsContainer.style.display = 'block';

                if (data.suggestions.length > 0) {
                    data.suggestions.forEach(item => {
                        const suggestionItem = document.createElement('div');
                        suggestionItem.classList.add('suggestion-item');
                        suggestionItem.textContent = item;
                        suggestionItem.addEventListener('click', function() {
                            searchForm.querySelector('input').value = item;
                            suggestionsContainer.style.display = 'none';
                            searchForm.querySelector('button').click();
                        });
                        suggestionsContainer.appendChild(suggestionItem);
                    });
                } else {
                    suggestionsContainer.style.display = 'none';
                }
            })
            .catch(error => console.error('Error:', error));
        } else {
            suggestionsContainer.style.display = 'none';
        }
    });
}

// メニューの外側をクリックしたときにメニューを非表示にする処理
function handleClickOutside(event) {
    const searchMenu = document.getElementById('search-menu-nav');
    const bottomNav = document.querySelector('.bottom-navigation');
    const hamburger = document.querySelector('.hamburger-menu');
    const menu = document.querySelector('.menu');

    if (searchMenu && searchMenu.style.display === 'block' && !bottomNav.contains(event.target)) {
        toggleSearchMenu();
    }
    if (menu && menu.style.display === 'block' && !hamburger.contains(event.target)) {
        menu.style.display = 'none';
    }
}

function toggleMenu() {
    const menu = document.querySelector('.menu');
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
}

// イベントリスナーの登録
document.addEventListener('DOMContentLoaded', function() {
    // 検索フォーム
    const searchForms = document.querySelectorAll('.search-form-1');
    searchForms.forEach(setupSearchSuggestions);

    const topSearchForm = document.getElementById('search-form-top');
    const bottomSearchForm = document.getElementById('search-form-bottom');
    const navSearchForm = document.getElementById('search-form-nav');

    if (topSearchForm) topSearchForm.onsubmit = handleSearchFormSubmit;
    if (bottomSearchForm) bottomSearchForm.onsubmit = handleSearchFormSubmit;
    if (navSearchForm) navSearchForm.onsubmit = handleSearchFormSubmit;

    // ナビゲーションメニュー
    const bottomNavigationSearch = document.getElementById('bottom-navigation-search');
    bottomNavigationSearch.addEventListener('click', toggleSearchMenu);

    // メニューの外側をクリック
    document.addEventListener('click', handleClickOutside);
});
