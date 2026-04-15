/* NC Federal Local Rules — Quick Reference
   Vanilla JS, no dependencies. Loads data/rules.json, renders a grouped
   comparison table, and filters live by category + keyword.
*/
(function () {
  'use strict';

  var state = {
    rules: [],
    meta: null,
    category: 'All',
    query: ''
  };

  var els = {
    search: document.getElementById('search'),
    clear: document.getElementById('clear'),
    chips: document.getElementById('chips'),
    status: document.getElementById('status'),
    results: document.getElementById('results'),
    sourcesList: document.getElementById('sources-list'),
    disclaimer: document.getElementById('disclaimer')
  };

  // ---------- Boot ----------
  fetch('data/rules.json', { cache: 'no-store' })
    .then(function (r) {
      if (!r.ok) throw new Error('Could not load rules.json (HTTP ' + r.status + ')');
      return r.json();
    })
    .then(function (data) {
      state.rules = data.rules || [];
      state.meta = data.meta || {};
      init();
    })
    .catch(function (err) {
      els.results.innerHTML = '<div class="empty">Failed to load rules data: ' +
        escapeHtml(err.message) + '<br><br>If you are opening this via <code>file://</code>, ' +
        'some browsers block <code>fetch()</code> on local files. Try serving the directory ' +
        'with <code>python3 -m http.server</code>.</div>';
    });

  function init() {
    renderSources();
    renderChips();
    restoreFromHash();
    bindEvents();
    render();
  }

  // ---------- Event wiring ----------
  function bindEvents() {
    var debounced = debounce(function () {
      state.query = els.search.value.trim();
      syncHash();
      render();
    }, 80);
    els.search.addEventListener('input', debounced);
    els.clear.addEventListener('click', function () {
      els.search.value = '';
      state.query = '';
      state.category = 'All';
      highlightChip();
      syncHash();
      render();
      els.search.focus();
    });
    window.addEventListener('hashchange', function () {
      restoreFromHash();
      render();
    });
  }

  // ---------- Hash state ----------
  function syncHash() {
    var parts = [];
    if (state.category && state.category !== 'All') parts.push('cat=' + encodeURIComponent(state.category));
    if (state.query) parts.push('q=' + encodeURIComponent(state.query));
    var h = parts.length ? '#' + parts.join('&') : ' ';
    history.replaceState(null, '', location.pathname + location.search + (h === ' ' ? '' : h));
  }
  function restoreFromHash() {
    var h = location.hash.replace(/^#/, '');
    if (!h) return;
    h.split('&').forEach(function (kv) {
      var i = kv.indexOf('=');
      if (i < 0) return;
      var k = kv.slice(0, i), v = decodeURIComponent(kv.slice(i + 1));
      if (k === 'cat') state.category = v;
      else if (k === 'q') { state.query = v; els.search.value = v; }
    });
    highlightChip();
  }

  // ---------- Chips ----------
  function renderChips() {
    var cats = ['All'];
    state.rules.forEach(function (r) { if (cats.indexOf(r.category) < 0) cats.push(r.category); });
    els.chips.innerHTML = cats.map(function (c) {
      return '<button class="chip" role="tab" data-cat="' + escapeAttr(c) + '" aria-pressed="' +
        (state.category === c ? 'true' : 'false') + '">' + escapeHtml(c) + '</button>';
    }).join('');
    Array.prototype.forEach.call(els.chips.querySelectorAll('.chip'), function (btn) {
      btn.addEventListener('click', function () {
        state.category = btn.getAttribute('data-cat');
        highlightChip();
        syncHash();
        render();
      });
    });
  }
  function highlightChip() {
    Array.prototype.forEach.call(els.chips.querySelectorAll('.chip'), function (btn) {
      btn.setAttribute('aria-pressed', btn.getAttribute('data-cat') === state.category ? 'true' : 'false');
    });
  }

  // ---------- Sources ----------
  function renderSources() {
    var s = state.meta && state.meta.sources;
    if (!s) return;
    var order = ['ednc', 'mdnc', 'wdnc'];
    els.sourcesList.innerHTML = order.map(function (k) {
      var src = s[k]; if (!src) return '';
      return '<div class="source-item"><span class="name">' + escapeHtml(src.name) + '</span> — ' +
        '<a href="' + escapeAttr(src.url) + '" target="_blank" rel="noopener">' + escapeHtml(src.rulesTitle) + '</a> ' +
        '<span class="effective">(eff. ' + escapeHtml(src.effective) + ')</span> · ' +
        '<a href="' + escapeAttr(src.landing) + '" target="_blank" rel="noopener">court rules page</a></div>';
    }).join('');
    if (state.meta.disclaimer) els.disclaimer.textContent = state.meta.disclaimer;
  }

  // ---------- Filtering + rendering ----------
  function render() {
    var q = state.query.toLowerCase();
    var cat = state.category;
    var filtered = state.rules.filter(function (r) {
      if (cat !== 'All' && r.category !== cat) return false;
      if (!q) return true;
      return matchesQuery(r, q);
    });

    if (filtered.length === 0) {
      els.results.innerHTML = '<div class="empty">No matching rules. Try a different search term or clear the filter.</div>';
    } else {
      els.results.innerHTML = groupByCategory(filtered).map(renderGroup).join('');
    }
    els.status.textContent = filtered.length + (filtered.length === 1 ? ' rule' : ' rules') +
      (q ? ' matching “' + state.query + '”' : '') +
      (cat !== 'All' ? ' in ' + cat : '') + '.';
  }

  function matchesQuery(r, q) {
    var parts = [r.topic, r.category, r.notes || '',
      r.ednc && r.ednc.value, r.ednc && r.ednc.cite,
      r.mdnc && r.mdnc.value, r.mdnc && r.mdnc.cite,
      r.wdnc && r.wdnc.value, r.wdnc && r.wdnc.cite];
    for (var i = 0; i < parts.length; i++) {
      if (parts[i] && String(parts[i]).toLowerCase().indexOf(q) >= 0) return true;
    }
    return false;
  }

  function groupByCategory(rows) {
    var order = [];
    var bucket = {};
    rows.forEach(function (r) {
      if (!bucket[r.category]) { bucket[r.category] = []; order.push(r.category); }
      bucket[r.category].push(r);
    });
    return order.map(function (c) { return { category: c, rows: bucket[c] }; });
  }

  function renderGroup(g) {
    return '<h2 class="category-heading">' + escapeHtml(g.category) + '</h2>' +
      g.rows.map(renderRow).join('');
  }

  function renderRow(r) {
    var q = state.query;
    return '<article class="rule-row">' +
      '<div class="topic"><span>' + highlight(r.topic, q) + '</span>' +
      '<span class="tag">' + escapeHtml(r.category) + '</span></div>' +
      '<div class="cells">' +
      renderCell('EDNC', r.ednc, q) +
      renderCell('MDNC', r.mdnc, q) +
      renderCell('WDNC', r.wdnc, q) +
      '</div>' +
      (r.notes ? '<div class="notes">' + highlight(r.notes, q) + '</div>' : '') +
      '</article>';
  }

  function renderCell(label, c, q) {
    if (!c) return '<div class="cell"><div class="district">' + label + '</div><div class="value">—</div></div>';
    return '<div class="cell">' +
      '<div class="district">' + label + '</div>' +
      '<div class="value">' + highlight(c.value, q) + '</div>' +
      (c.cite ? '<div class="cite">' + highlight(c.cite, q) + '</div>' : '') +
      '</div>';
  }

  // ---------- Utils ----------
  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function escapeAttr(s) { return escapeHtml(s); }
  function highlight(text, q) {
    var safe = escapeHtml(text);
    if (!q) return safe;
    var re = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
    return safe.replace(re, '<mark class="hit">$1</mark>');
  }
  function debounce(fn, ms) {
    var t; return function () {
      var ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }
})();
