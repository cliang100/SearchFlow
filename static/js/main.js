const API = '';
const input = document.getElementById('search-input');
const hero = document.getElementById('hero');
const resultsSection = document.getElementById('results-section');
const resultsList = document.getElementById('results-list');
const metaEl = document.getElementById('meta');
const statusEl = document.getElementById('status');
const autocompleteEl = document.getElementById('autocomplete');
const toast = document.getElementById('toast');

let acIndex = -1;
let acTimer = null;
let searchTimer = null;

function showToast(msg, duration = 2500) {
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

async function doSearch(query) {
    if (!query.trim()) return;
    const t0 = performance.now();
    hero.classList.add('collapsed');
    resultsSection.classList.add('visible');
    statusEl.classList.remove('visible');
    resultsList.innerHTML = '';
    metaEl.textContent = 'searching...';

    try {
    const res = await fetch(`${API}/search/?q=${encodeURIComponent(query)}&limit=20`);
    if (!res.ok) throw new Error(`search returned ${res.status}`);
    const data = await res.json();
    const elapsed = ((performance.now() - t0) / 1000).toFixed(3);

    if (!data.length) {
        metaEl.textContent = '';
        statusEl.textContent = `no results for "${query}"`;
        statusEl.classList.add('visible');
        return;
    }

    metaEl.textContent = `${data.length} result${data.length !== 1 ? 's' : ''} (${elapsed}s)`;
    resultsList.replaceChildren(...data.map(renderResult));
    } catch (e) {
    metaEl.textContent = '';
    statusEl.textContent = 'search failed — is the API running?';
    statusEl.classList.add('visible');
    }
}

async function doAutocomplete(prefix) {
    if (prefix.length < 2) { hideAutocomplete(); return; }
    try {
    const res = await fetch(`${API}/search/autocomplete?q=${encodeURIComponent(prefix)}&limit=6`);
    const data = await res.json();
    const suggestions = data.suggestions || [];
    if (!suggestions.length) { hideAutocomplete(); return; }
    acIndex = -1;
    autocompleteEl.replaceChildren(...suggestions.map(s => {
        const option = el('div', 'suggestion', s);
        option.setAttribute('role', 'option');
        return option;
    }));
    autocompleteEl.classList.add('visible');
    autocompleteEl.querySelectorAll('.suggestion').forEach(el => {
        el.addEventListener('mousedown', e => {
        e.preventDefault();
        input.value = el.textContent;
        hideAutocomplete();
        doSearch(el.textContent);
        });
    });
    } catch (_) { hideAutocomplete(); }
}

function el(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    node.textContent = text;
    return node;
}

function renderResult(r) {
    const result = el('div', 'result', '');
    const title = el('a', 'result-title', r.title);
    // only link to web pages, never javascript: or data: URLs
    if (/^https?:\/\//i.test(r.url)) {
        title.href = r.url;
        title.target = '_blank';
        title.rel = 'noopener noreferrer';
    }
    result.append(
        title,
        el('div', 'result-url', r.url),
        el('div', 'result-snippet', r.content),
        el('div', 'result-score', `score: ${r.score}`),
    );
    return result;
}

function hideAutocomplete() {
    autocompleteEl.classList.remove('visible');
    acIndex = -1;
}

input.addEventListener('input', () => {
    const val = input.value;
    clearTimeout(acTimer);
    acTimer = setTimeout(() => doAutocomplete(val), 150);
});

input.addEventListener('keydown', e => {
    const items = autocompleteEl.querySelectorAll('.suggestion');
    if (e.key === 'ArrowDown') {
    e.preventDefault();
    acIndex = Math.min(acIndex + 1, items.length - 1);
    items.forEach((el, i) => el.classList.toggle('active', i === acIndex));
    if (items[acIndex]) input.value = items[acIndex].textContent;
    } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    acIndex = Math.max(acIndex - 1, -1);
    items.forEach((el, i) => el.classList.toggle('active', i === acIndex));
    if (acIndex >= 0 && items[acIndex]) input.value = items[acIndex].textContent;
    } else if (e.key === 'Enter') {
    hideAutocomplete();
    doSearch(input.value);
    } else if (e.key === 'Escape') {
    hideAutocomplete();
    }
});

document.getElementById('search-btn').addEventListener('click', () => {
    hideAutocomplete();
    doSearch(input.value);
});

document.addEventListener('click', e => {
    if (!e.target.closest('.search-wrap')) hideAutocomplete();
});

// Admin calls need the server's ADMIN_TOKEN. It is kept for this tab only.
function adminToken() {
    let token = sessionStorage.getItem('searchflow_admin_token');
    if (!token) {
        token = prompt('Admin token:');
        if (token) sessionStorage.setItem('searchflow_admin_token', token);
    }
    return token;
}

async function adminFetch(path, body) {
    const token = adminToken();
    if (!token) return null;
    const res = await fetch(`${API}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
        body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 401) sessionStorage.removeItem('searchflow_admin_token');
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const detail = Array.isArray(data.detail) ? data.detail[0].msg : data.detail;
        throw new Error(detail || `request failed (${res.status})`);
    }
    return data;
}

document.getElementById('rebuild-btn').addEventListener('click', async () => {
    const btn = document.getElementById('rebuild-btn');
    btn.disabled = true;
    btn.textContent = 'rebuilding...';
    try {
        const data = await adminFetch('/search/rebuild-index');
        if (data) showToast(data.message);
    } catch (e) {
        showToast(e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'rebuild index';
    }
});

document.getElementById('crawl-btn').addEventListener('click', async () => {
    const url = prompt('URL to crawl:');
    if (!url) return;
    const maxPages = parseInt(prompt('Max pages (1-200):', '20'), 10) || 20;
    try {
        const data = await adminFetch('/crawler/start', { start_url: url, max_pages: maxPages });
        if (data) showToast(data.message);
    } catch (e) {
        showToast(e.message);
    }
});
