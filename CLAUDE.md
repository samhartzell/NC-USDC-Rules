# CLAUDE.md

Guidance for AI assistants (Claude Code and similar) working in this repository.

## What this project is

A single-page, zero-dependency web app that compares the **Local Civil Rules**
of the three U.S. District Courts in North Carolina — Eastern (**EDNC**),
Middle (**MDNC**), and Western (**WDNC**) — side by side. Lawyers and
paralegals use it to look up response deadlines, page/word limits, formatting
rules, filing procedures, motion practice, and discovery rules for all three
districts in one place instead of cross-referencing three PDFs.

It is a **reference content site**, not an application. The bulk of meaningful
work happens in `data/rules.json`, not in the JS.

## Repository layout

```
index.html                    Single-page UI shell. No templating, no build.
app.js                        Vanilla JS (IIFE). Loads rules.json, filters,
                              renders. ~220 lines, no dependencies.
styles.css                    Responsive + print styles. Sticky search bar.
data/
  rules.json                  Source of truth. One entry per topic; each entry
                              has cells for ednc / mdnc / wdnc + optional notes.
sources/
  EDNC-local-rules.md         Provenance: PDF link, effective date, and the
  MDNC-local-rules.md         index of which rule numbers were consulted when
  WDNC-local-rules.md         building rules.json. Update when amendments hit.
README.md                     User-facing docs (how to open / serve / search).
.gitignore                    Ignores .claude/, .DS_Store, *.log
```

There is **no build step, no package.json, no test suite, no CI**. Edits to
`rules.json` are immediately live on browser reload.

## Data model (`data/rules.json`)

```jsonc
{
  "meta": {
    "sources": {
      "ednc": { "name", "rulesTitle", "effective", "url", "landing" },
      "mdnc": { ... },
      "wdnc": { ... }
    },
    "disclaimer": "..."
  },
  "rules": [
    {
      "id": "stable-kebab-id",          // unique, used for hash links / diffs
      "category": "Deadlines",          // see canonical category list below
      "topic": "Short human-readable label shown as the row title",
      "ednc": { "value": "...", "cite": "L.Civ.R. 7.1(f)(1)" },
      "mdnc": { "value": "...", "cite": "LR 7.3(f)" },
      "wdnc": { "value": "...", "cite": "LCvR 7.1(e)" },
      "notes": "optional cross-district note rendered below the cells"
    }
  ]
}
```

### Canonical categories (in display order)

The chip filter is generated dynamically from the order categories first appear
in `rules.json`, so **keep entries grouped by category in the file**. Current
set:

1. `Deadlines`
2. `Page / Word Limits`
3. `Formatting`
4. `Filing & Service`
5. `Motion Practice`
6. `Discovery`

Add a new category only when an existing one truly doesn't fit. New rows in an
existing category should be inserted with the rest of that category's block.

### Per-district cite conventions

Each district has a different short citation form — match the district's own
usage; do not normalize across districts:

- EDNC: `L.Civ.R. 7.1(f)(1)`
- MDNC: `LR 7.3(f)` (sometimes `LR 56.1(d)–(e)` for ranges)
- WDNC: `LCvR 7.1(e)`

If a rule is genuinely unaddressed by a district, set `value` to a short
explanation (e.g. `"No separate rule; set by judge's standing order"`) and
either omit `cite` or cite the closest catch-all rule. Don't leave the cell
out — every entry should have all three of `ednc`, `mdnc`, `wdnc`.

### `id` rules

- Lowercase kebab-case, stable across edits. Don't rename without reason —
  ids may end up in URL hashes or external links once that's wired up.
- Make them descriptive: `response-sj`, `page-limits-briefs`, `rule-26f`.

## Rendering pipeline (how `app.js` works)

`app.js` is one IIFE with these stages — keep this shape if editing it:

1. **Boot:** `fetch('data/rules.json', { cache: 'no-store' })` → on success
   call `init()`; on error render an inline message that explains the
   `file://` + `fetch()` gotcha and recommends `python3 -m http.server`.
2. **`init()`:** `renderSources()` (footer source list), `renderChips()`
   (category filter), `restoreFromHash()` (hydrate `state` from
   `#cat=...&q=...`), `bindEvents()`, then `render()`.
3. **State** (`var state`): `{ rules, meta, category, query }`. There is no
   framework; mutate `state` and call `render()`.
4. **Filtering:** `matchesQuery` does a case-insensitive substring search
   across `topic`, `category`, `notes`, and every district's `value` + `cite`.
5. **Rendering:** group filtered rows by category in original order, then emit
   `<article class="rule-row">` blocks with three `.cell`s. The current query
   is wrapped in `<mark class="hit">` via `highlight()`.
6. **Hash sync:** `syncHash()` writes `#cat=...&q=...` via `replaceState`;
   `restoreFromHash()` reads it on load and on `hashchange`.
7. **Utils:** `escapeHtml`, `escapeAttr`, `highlight`, `debounce(fn, 80)`.

### JS conventions to preserve

- **Vanilla ES5-style.** `var`, function declarations, no arrow functions,
  no template literals, no `const`/`let`. The file targets "any modern
  browser" and uses `'use strict';` — keep it minimal so it works on
  `file://` with no toolchain.
- **No dependencies.** Don't add npm, bundlers, frameworks, or a `package.json`.
- **All HTML insertion goes through `escapeHtml` / `escapeAttr`** before
  hitting `innerHTML`. The only exception is `highlight()`, which escapes
  first and then inserts `<mark>` around the (regex-escaped) query. Preserve
  this discipline — the data is trusted today but may be user-editable later.
- **DOM lookups are cached in `els`** at the top. Add to `els` rather than
  re-querying in render functions.

## Common edit recipes

### A district amends a rule

1. Open the district's current PDF (links in `sources/<DISTRICT>-local-rules.md`
   or `meta.sources.<district>.url`).
2. Edit the matching row in `data/rules.json` — update `value`, `cite`, and
   any `notes`.
3. Bump `meta.sources.<district>.effective` to the new effective date.
4. Update the rule index table in `sources/<DISTRICT>-local-rules.md` if rule
   numbers changed; bump the **Captured:** date.
5. Commit with a message like `EDNC: update reply deadline per May 2026 amendments`.

### Adding a new topic / row

1. Pick the category. Insert the new object **inside that category's block** in
   `rules.json` so the on-page grouping stays clean.
2. Choose a stable kebab-case `id` not already in use.
3. Fill all three district cells. If a district truly has no rule on point,
   say so in the `value` and skip or note `cite`.
4. If there's a meaningful cross-district nuance, add a `notes` field.
5. Add the rule numbers you relied on to the table in each district's
   `sources/<DISTRICT>-local-rules.md`.

### Changing the UI

- Most adjustments are CSS-only — `styles.css` defines colors via `:root`
  custom properties (`--accent`, `--hit`, etc.) and includes a print block at
  the bottom (header collapses, chips hidden). Prefer tweaking variables.
- Functional changes go in `app.js`. Match the existing ES5-ish style.
- `index.html` is intentionally tiny; new sections should be added there and
  populated from JS, not hard-coded.

## Verifying changes locally

There is no test suite. To verify:

```sh
cd NC-USDC-Rules
python3 -m http.server 8000
# open http://localhost:8000
```

Sanity checks after editing `rules.json`:

- Page loads without the "Failed to load rules data" banner (no JSON syntax
  errors).
- The status line shows the expected total rule count.
- Each category chip filters as expected.
- A search for a distinctive token in your edit (e.g. `30 days`, the new
  cite) highlights in the right cell.
- `Ctrl/Cmd+P` print preview still looks clean.

If you can't open a browser in your environment, at minimum validate JSON:

```sh
python3 -c "import json; json.load(open('data/rules.json'))"
```

## Branch and commit conventions

- Default branch: `main`.
- Feature work happens on a branch; PRs merge into `main` (see PR #1).
- Existing commit style is short and descriptive (`Initial commit: NC federal
  local rules quick-reference`). For rule updates, prefer
  `<DISTRICT>: <what changed>` (e.g. `MDNC: page-limit increase, LR 7.3(d)`).
- Per session instructions, do not create a PR unless explicitly asked.

## Things to avoid

- Don't introduce a build step, framework, package manager, or transpiler.
  The "open `index.html` and it works" property is a deliberate feature.
- Don't reformat or reorder `rules.json` wholesale — the source order is the
  display order. Targeted edits only.
- Don't claim a rule without a `cite`. Every cell's `value` should be
  traceable to a numbered rule (or a clearly labeled judge's standing order
  / scheduling order caveat).
- Don't soften the disclaimer — this is a reference, not legal advice, and
  the README/footer/`meta.disclaimer` all say so on purpose.
- Don't add tracking, analytics, or external scripts. The site must work
  offline from `file://` (modulo the documented `fetch()` caveat).
