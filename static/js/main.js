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
    const data = await res.json();
    const elapsed = ((performance.now() - t0) / 1000).toFixed(3);

    if (!data.length) {
        metaEl.textContent = '';
        statusEl.textContent = `no results for "${query}"`;
        statusEl.classList.add('visible');
        return;
    }

    metaEl.textContent = `${data.length} result${data.length !== 1 ? 's' : ''} (${elapsed}s)`;
    resultsList.innerHTML = data.map(r => `
        <div class="result">
        <a class="result-title" href="${r.url}" target="_blank" rel="noopener">${escHtml(r.title || r.url)}</a>
        <div class="result-url">${escHtml(r.url)}</div>
        <div class="result-snippet">${escHtml(r.content)}</div>
        <div class="result-score">score: ${r.score}</div>
        </div>
    `).join('');
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
    autocompleteEl.innerHTML = suggestions
        .map(s => `<div class="suggestion">${escHtml(s)}</div>`)
        .join('');
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

function hideAutocomplete() {
    autocompleteEl.classList.remove('visible');
    acIndex = -1;
}

function escHtml(str) {
    return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
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

document.getElementById('rebuild-btn').addEventListener('click', async () => {
    const btn = document.getElementById('rebuild-btn');
    btn.disabled = true;
    btn.textContent = 'rebuilding...';
    try {
    const res = await fetch(`${API}/search/rebuild-index`, { method: 'POST' });
    const data = await res.json();
    showToast(data.message);
    } catch (_) {
    showToast('rebuild failed');
    } finally {
    btn.disabled = false;
    btn.textContent = 'rebuild index';
    }
});

document.getElementById('crawl-btn').addEventListener('click', async () => {
    const url = prompt('URL to crawl:');
    if (!url) return;
    const maxPages = prompt('Max pages (default 20):', '20');
    try {
    const res = await fetch(`${API}/crawler/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_url: url, max_pages: parseInt(maxPages) || 20 })
    });
    const data = await res.json();
    showToast(data.message || 'crawl started');
    } catch (_) {
    showToast('crawl failed');
    }
});