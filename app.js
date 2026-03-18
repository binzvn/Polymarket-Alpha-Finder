/* ═══════════════════════════════════════════════════════════════
   Polymarket Alpha Finder – Client-side Logic
   Handles API calls, filtering, sorting, and CSV export
   ═══════════════════════════════════════════════════════════════ */

// ── State ────────────────────────────────────────────────────
let allWallets = [];
let currentFilter = 'all';
let currentSort = { key: 'score', dir: 'desc' };

// ── DOM refs ─────────────────────────────────────────────────
const $  = id => document.getElementById(id);

// ── Analysis ─────────────────────────────────────────────────
async function startAnalysis() {
  const url = $('urlInput').value.trim();
  if (!url) return showError('Please enter a Polymarket URL');

  // UI: show progress, hide results
  $('analyzeBtn').disabled = true;
  $('btnLoader').classList.remove('hidden');
  $('btnText') && ($('analyzeBtn').querySelector('.btn-text').textContent = 'Analyzing…');
  $('progressContainer').classList.remove('hidden');
  $('emptyState').classList.add('hidden');
  $('errorToast').classList.add('hidden');
  setProgress(10, 'Resolving market data…');

  try {
    setProgress(20, 'Fetching trades & wallet addresses…');

    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    setProgress(70, 'Processing wallet metrics…');

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.error || 'Analysis failed');
    }

    setProgress(90, 'Rendering results…');

    allWallets = data.wallets || [];
    renderSummary(data.summary);
    renderTable();
    showResults(data.summary.event_title);

    setProgress(100, 'Done!');
    setTimeout(() => $('progressContainer').classList.add('hidden'), 800);

  } catch (err) {
    showError(err.message);
    $('progressContainer').classList.add('hidden');
  } finally {
    $('analyzeBtn').disabled = false;
    $('btnLoader').classList.add('hidden');
    $('analyzeBtn').querySelector('.btn-text').textContent = 'Analyze';
  }
}

// ── Progress helpers ─────────────────────────────────────────
function setProgress(pct, text) {
  $('progressBar').style.width = pct + '%';
  $('progressText').textContent = text;
}

function showResults(title) {
  $('eventTitle').textContent = title || '';
  $('eventTitle').classList.remove('hidden');
  $('summaryCards').classList.remove('hidden');
  $('toolbar').classList.remove('hidden');
  $('tableContainer').classList.remove('hidden');
  $('emptyState').classList.add('hidden');
}

function showError(msg) {
  const el = $('errorToast');
  el.textContent = msg;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 5000);
}

// ── Summary ──────────────────────────────────────────────────
function renderSummary(summary) {
  $('cardAnalyzed').textContent = summary.total_analyzed;
  $('cardSystematic').textContent = summary.systematic_count;
  $('cardWhale').textContent = summary.whale_count;
  $('cardScalper').textContent = summary.scalper_count;

  // Animate numbers
  animateValue($('cardAnalyzed'), summary.total_analyzed);
  animateValue($('cardSystematic'), summary.systematic_count);
  animateValue($('cardWhale'), summary.whale_count);
  animateValue($('cardScalper'), summary.scalper_count);
}

function animateValue(el, target) {
  let current = 0;
  const step = Math.max(1, Math.floor(target / 20));
  const interval = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current;
    if (current >= target) clearInterval(interval);
  }, 30);
}

// ── Filtering ────────────────────────────────────────────────
function setFilter(filter, btn) {
  currentFilter = filter;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  renderTable();
}

function getFilteredWallets() {
  if (currentFilter === 'all') return allWallets;
  if (currentFilter === 'passing') return allWallets.filter(w => w.passes_filter);
  return allWallets.filter(w => w.type === currentFilter);
}

// ── Sorting ──────────────────────────────────────────────────
function sortTable(key) {
  if (currentSort.key === key) {
    currentSort.dir = currentSort.dir === 'desc' ? 'asc' : 'desc';
  } else {
    currentSort = { key, dir: 'desc' };
  }

  // Update arrows
  document.querySelectorAll('.sort-arrow').forEach(a => {
    a.className = 'sort-arrow';
  });
  const arrow = $('sort-' + key);
  if (arrow) arrow.className = 'sort-arrow ' + currentSort.dir;

  renderTable();
}

// ── Table Rendering ──────────────────────────────────────────
function renderTable() {
  const wallets = getFilteredWallets();

  // Sort
  const sorted = [...wallets].sort((a, b) => {
    let va = a[currentSort.key];
    let vb = b[currentSort.key];

    // String sort for name/type
    if (typeof va === 'string' && typeof vb === 'string') {
      return currentSort.dir === 'asc'
        ? va.localeCompare(vb)
        : vb.localeCompare(va);
    }

    va = Number(va) || 0;
    vb = Number(vb) || 0;
    return currentSort.dir === 'asc' ? va - vb : vb - va;
  });

  const tbody = $('tableBody');
  tbody.innerHTML = '';

  sorted.forEach((w, i) => {
    const tr = document.createElement('tr');
    tr.style.animationDelay = Math.min(i * 0.02, 0.3) + 's';

    const pnlClass = w.total_pnl > 0 ? 'pnl-positive' : w.total_pnl < 0 ? 'pnl-negative' : 'pnl-neutral';
    const pnlPctClass = w.pnl_pct > 0 ? 'pnl-positive' : w.pnl_pct < 0 ? 'pnl-negative' : 'pnl-neutral';
    const wrClass = w.win_rate >= 0.6 ? 'wr-high' : w.win_rate >= 0.4 ? 'wr-mid' : 'wr-low';
    const typeLabel = w.type === 'whale_gambler' ? 'whale gambler' : w.type;
    const filterClass = w.passes_filter ? 'filter-pass' : 'filter-fail';
    const filterLabel = w.passes_filter ? 'pass' : 'fail';

    const profileLink = w.profile_url
      ? `<a href="${w.profile_url}" target="_blank" class="profile-link">view</a>`
      : `<a href="https://polymarket.com/profile/${w.address}" target="_blank" class="profile-link">view</a>`;

    tr.innerHTML = `
      <td class="col-name" title="${w.address}">${escHtml(w.name)}</td>
      <td class="col-num">${w.score}</td>
      <td><span class="badge badge-${w.type}">${typeLabel}</span></td>
      <td class="col-num ${pnlClass}">$${formatNum(w.total_pnl)}</td>
      <td class="col-num ${pnlPctClass}">${w.pnl_pct.toFixed(1)}%</td>
      <td class="col-num ${wrClass}">${(w.win_rate * 100).toFixed(1)}%</td>
      <td class="col-num">${w.total_positions}</td>
      <td class="col-num">${w.num_markets}</td>
      <td class="col-num">${w.cv.toFixed(2)}</td>
      <td class="col-num">${(w.concentration * 100).toFixed(1)}%</td>
      <td><span class="filter-dot ${filterClass}">${filterLabel}</span></td>
      <td>${profileLink}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── CSV Export ────────────────────────────────────────────────
function exportCSV() {
  const wallets = getFilteredWallets();
  if (!wallets.length) return showError('No data to export');

  const cols = [
    'address','name','type','score','passes_filter',
    'total_pnl','pnl_pct','win_rate','total_positions',
    'num_markets','avg_bet_size','cv','concentration',
    'diversification','trade_frequency','num_trades'
  ];

  let csv = cols.join(',') + '\n';
  wallets.forEach(w => {
    csv += cols.map(c => {
      let v = w[c];
      if (typeof v === 'string') v = '"' + v.replace(/"/g, '""') + '"';
      return v ?? '';
    }).join(',') + '\n';
  });

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'polymarket_alpha.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// ── Helpers ──────────────────────────────────────────────────
function formatNum(n) {
  if (n === 0) return '0.00';
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return sign + (abs / 1_000_000).toFixed(2) + 'M';
  if (abs >= 1_000) return sign + abs.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return sign + abs.toFixed(2);
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ── Enter key submits ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  $('urlInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') startAnalysis();
  });
});
