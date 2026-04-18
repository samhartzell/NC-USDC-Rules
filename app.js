/* NC Federal Local Rules — Quick Reference
   Vanilla JS, no dependencies. Loads data/rules.json, renders a grouped
   comparison table, and filters live by category + keyword.
*/
(function () {
  'use strict';

  var DISTRICTS = ['ednc', 'mdnc', 'wdnc'];
  var DISTRICT_LABEL = { ednc: 'EDNC', mdnc: 'MDNC', wdnc: 'WDNC' };

  var state = {
    rules: [],
    meta: null,
    category: 'All',
    query: '',
    districts: DISTRICTS.slice(),
    diffsOnly: false,
    target: ''
  };

  var els = {
    search: document.getElementById('search'),
    reset: document.getElementById('reset'),
    chips: document.getElementById('chips'),
    districts: document.getElementById('districts'),
    diffsOnly: document.getElementById('diffs-only'),
    status: document.getElementById('status'),
    results: document.getElementById('results'),
    sourcesList: document.getElementById('sources-list'),
    disclaimer: document.getElementById('disclaimer'),
    controls: document.querySelector('.controls')
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
    renderDistrictToggles();
    restoreFromHash();
    bindEvents();
    render();
    updateStickyOffset();
    if (state.target) focusTarget(state.target);
  }

  // ---------- Event wiring ----------
  function bindEvents() {
    var debounced = debounce(function () {
      state.query = els.search.value.trim();
      state.target = '';
      syncHash();
      render();
    }, 80);
    els.search.addEventListener('input', debounced);
    els.reset.addEventListener('click', function () {
      els.search.value = '';
      state.query = '';
      state.category = 'All';
      state.districts = DISTRICTS.slice();
      state.diffsOnly = false;
      state.target = '';
      highlightChip();
      highlightDistrictToggles();
      highlightDiffsToggle();
      syncHash();
      render();
      els.search.focus();
    });
    if (els.diffsOnly) {
      els.diffsOnly.addEventListener('click', function () {
        state.diffsOnly = !state.diffsOnly;
        state.target = '';
        highlightDiffsToggle();
        syncHash();
        render();
      });
    }
    window.addEventListener('hashchange', function () {
      restoreFromHash();
      render();
      if (state.target) focusTarget(state.target);
    });
    els.results.addEventListener('click', function (e) {
      var btn = e.target.closest ? e.target.closest('.copy-link') : null;
      if (!btn) return;
      var id = btn.getAttribute('data-rule-id');
      if (id) copyRuleLink(id, btn);
    });
    document.addEventListener('keydown', handleShortcut);
    window.addEventListener('resize', debounce(updateStickyOffset, 120));
  }

  function handleShortcut(e) {
    // Esc inside the search clears the query.
    if (e.key === 'Escape' && document.activeElement === els.search && els.search.value) {
      els.search.value = '';
      state.query = '';
      state.target = '';
      syncHash();
      render();
      e.preventDefault();
      return;
    }
    // Ignore shortcuts while typing in another editable surface.
    var t = e.target;
    var tag = t && t.tagName;
    var editable = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' ||
      (t && t.isContentEditable);
    var metaK = (e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey);
    if (metaK) {
      els.search.focus();
      els.search.select();
      e.preventDefault();
      return;
    }
    if (editable) return;
    if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
      els.search.focus();
      els.search.select();
      e.preventDefault();
    }
  }

  function updateStickyOffset() {
    if (!els.controls) return;
    var h = els.controls.offsetHeight || 0;
    document.documentElement.style.setProperty('--sticky-offset', h + 'px');
  }

  // ---------- Hash state ----------
  function syncHash() {
    var parts = [];
    if (state.category && state.category !== 'All') parts.push('cat=' + encodeURIComponent(state.category));
    if (state.query) parts.push('q=' + encodeURIComponent(state.query));
    if (state.districts.length !== DISTRICTS.length) parts.push('d=' + state.districts.join(','));
    if (state.diffsOnly) parts.push('diffs=1');
    if (state.target) parts.push('rule=' + encodeURIComponent(state.target));
    var url = location.pathname + location.search + (parts.length ? '#' + parts.join('&') : '');
    history.replaceState(null, '', url);
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
      else if (k === 'd') {
        var picked = v.split(',').filter(function (x) { return DISTRICTS.indexOf(x) >= 0; });
        if (picked.length) state.districts = picked;
      }
      else if (k === 'diffs') state.diffsOnly = v === '1';
      else if (k === 'rule') state.target = v;
    });
    highlightChip();
    highlightDistrictToggles();
    highlightDiffsToggle();
  }

  function highlightDiffsToggle() {
    if (!els.diffsOnly) return;
    els.diffsOnly.setAttribute('aria-pressed', state.diffsOnly ? 'true' : 'false');
    if (state.districts.length < 2) els.diffsOnly.setAttribute('aria-disabled', 'true');
    else els.diffsOnly.removeAttribute('aria-disabled');
  }

  // ---------- Chips ----------
  function renderChips() {
    var counts = { All: state.rules.length };
    state.rules.forEach(function (r) { counts[r.category] = (counts[r.category] || 0) + 1; });
    var cats = ['All'];
    state.rules.forEach(function (r) { if (cats.indexOf(r.category) < 0) cats.push(r.category); });
    els.chips.innerHTML = cats.map(function (c) {
      return '<button class="chip" role="tab" data-cat="' + escapeAttr(c) + '" aria-pressed="' +
        (state.category === c ? 'true' : 'false') + '">' + escapeHtml(c) +
        ' <span class="count">(' + counts[c] + ')</span></button>';
    }).join('');
    Array.prototype.forEach.call(els.chips.querySelectorAll('.chip'), function (btn) {
      btn.addEventListener('click', function () {
        state.category = btn.getAttribute('data-cat');
        state.target = '';
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

  // ---------- District toggles ----------
  function renderDistrictToggles() {
    els.districts.innerHTML = DISTRICTS.map(function (d) {
      var active = state.districts.indexOf(d) >= 0;
      return '<button class="chip chip-dist" type="button" data-dist="' + d + '" aria-pressed="' +
        (active ? 'true' : 'false') + '">' + DISTRICT_LABEL[d] + '</button>';
    }).join('');
    Array.prototype.forEach.call(els.districts.querySelectorAll('.chip-dist'), function (btn) {
      btn.addEventListener('click', function () {
        var d = btn.getAttribute('data-dist');
        var idx = state.districts.indexOf(d);
        if (idx >= 0) {
          if (state.districts.length === 1) return; // keep at least one visible
          state.districts.splice(idx, 1);
        } else {
          // Preserve canonical order (ednc, mdnc, wdnc).
          state.districts = DISTRICTS.filter(function (x) {
            return state.districts.indexOf(x) >= 0 || x === d;
          });
        }
        state.target = '';
        highlightDistrictToggles();
        highlightDiffsToggle();
        syncHash();
        render();
      });
    });
  }
  function highlightDistrictToggles() {
    Array.prototype.forEach.call(els.districts.querySelectorAll('.chip-dist'), function (btn) {
      var d = btn.getAttribute('data-dist');
      var active = state.districts.indexOf(d) >= 0;
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      if (active && state.districts.length === 1) btn.setAttribute('aria-disabled', 'true');
      else btn.removeAttribute('aria-disabled');
    });
  }

  // ---------- Sources ----------
  function renderSources() {
    var s = state.meta && state.meta.sources;
    if (!s) return;
    els.sourcesList.innerHTML = DISTRICTS.map(function (k) {
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
    var diffsActive = state.diffsOnly && state.districts.length >= 2;
    var filtered = state.rules.filter(function (r) {
      if (cat !== 'All' && r.category !== cat) return false;
      if (q && !matchesQuery(r, q)) return false;
      if (diffsActive && !rowDiffers(r, state.districts)) return false;
      return true;
    });

    if (filtered.length === 0) {
      els.results.innerHTML = '<div class="empty">No matching rules. Try a different search term or reset the filters.</div>';
    } else {
      els.results.innerHTML = groupByCategory(filtered).map(renderGroup).join('');
    }
    els.status.textContent = filtered.length + (filtered.length === 1 ? ' rule' : ' rules') +
      (q ? ' matching \u201C' + state.query + '\u201D' : '') +
      (cat !== 'All' ? ' in ' + cat : '') +
      (state.districts.length !== DISTRICTS.length ? ' · showing ' +
        state.districts.map(function (d) { return DISTRICT_LABEL[d]; }).join(' + ') : '') +
      (diffsActive ? ' · differences only' : '') + '.';
  }

  function rowDiffers(r, districts) {
    if (!districts || districts.length < 2) return false;
    var first = normCell(r[districts[0]]);
    for (var i = 1; i < districts.length; i++) {
      if (normCell(r[districts[i]]) !== first) return true;
    }
    return false;
  }

  function normCell(c) {
    if (!c || c.value == null) return '';
    return String(c.value).toLowerCase().replace(/\s+/g, ' ').trim();
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
    var n = state.districts.length;
    var gridStyle = 'grid-template-columns:repeat(' + n + ',1fr)';
    var cells = state.districts.map(function (d) {
      return renderCell(d, r[d], q);
    }).join('');
    var rid = escapeAttr(r.id || '');
    // Show the Differs badge only when the user has narrowed the district set
    // (at 3-wide, every row differs textually and the badge adds no signal).
    var showDiffBadge = n < DISTRICTS.length && rowDiffers(r, state.districts);
    return '<article class="rule-row" id="rule-' + rid + '">' +
      '<div class="topic">' +
        '<span class="topic-text">' + highlight(r.topic, q) + '</span>' +
        '<span class="topic-meta">' +
          '<span class="tag">' + escapeHtml(r.category) + '</span>' +
          (showDiffBadge ? '<span class="tag tag-diff" title="The visible districts disagree on this rule">Differs</span>' : '') +
          (r.id ? '<button class="copy-link" type="button" data-rule-id="' + rid +
            '" aria-label="Copy link to this rule" title="Copy link to this rule">#</button>' : '') +
        '</span>' +
      '</div>' +
      '<div class="cells" style="' + gridStyle + '">' + cells + '</div>' +
      (r.notes ? '<div class="notes">' + highlight(r.notes, q) + '</div>' : '') +
      '</article>';
  }

  function renderCell(district, c, q) {
    var label = DISTRICT_LABEL[district] || String(district).toUpperCase();
    if (!c) return '<div class="cell"><div class="district">' + label + '</div><div class="value">—</div></div>';
    var src = state.meta && state.meta.sources && state.meta.sources[district];
    var citeHtml = '';
    if (c.cite) {
      var inner = highlight(c.cite, q);
      if (src && src.url) {
        citeHtml = '<a class="cite cite-link" href="' + escapeAttr(src.url) +
          '" target="_blank" rel="noopener" title="Open ' + escapeAttr(label) +
          ' ' + escapeAttr(src.rulesTitle || 'local rules') + ' (PDF)">' + inner + '</a>';
      } else {
        citeHtml = '<div class="cite">' + inner + '</div>';
      }
    }
    return '<div class="cell">' +
      '<div class="district">' + label + '</div>' +
      '<div class="value">' + highlight(c.value, q) + '</div>' +
      citeHtml +
      '</div>';
  }

  // ---------- Rule target ----------
  function focusTarget(id) {
    var el = document.getElementById('rule-' + id);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.classList.remove('is-target');
    // Re-trigger animation.
    void el.offsetWidth;
    el.classList.add('is-target');
  }

  function copyRuleLink(id, btn) {
    var url = location.origin + location.pathname + location.search + '#rule=' + encodeURIComponent(id);
    var done = function () {
      var original = btn.textContent;
      btn.textContent = 'Copied';
      btn.classList.add('copied');
      setTimeout(function () {
        btn.textContent = original;
        btn.classList.remove('copied');
      }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(done, function () { fallbackCopy(url, done); });
    } else {
      fallbackCopy(url, done);
    }
  }

  function fallbackCopy(text, cb) {
    try {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      cb();
    } catch (e) {
      window.prompt('Copy this link:', text);
    }
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
