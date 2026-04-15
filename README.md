# NC Federal Local Rules — Quick Reference

**Live site:** https://samhartzell.github.io/NC-USDC-Rules/

A searchable, side-by-side comparison of the Local Rules of the three United
States District Courts in North Carolina: the Eastern (**EDNC**), Middle
(**MDNC**), and Western (**WDNC**) Districts.

The site is deployed automatically to GitHub Pages on every push to `main` via
[`.github/workflows/pages.yml`](.github/workflows/pages.yml).

The goal is one lookup instead of three PDFs: response deadlines, page/word
limits, formatting specs, filing procedures, and motion practice — each row
compares all three courts with citations to the governing local rule.

## Use it

- **Hosted / offline:** open `index.html` in any modern browser.
- **If your browser blocks `fetch()` on `file://`** (some do), serve the
  directory locally:
  ```
  cd NC-USDC-Rules && python3 -m http.server 8000
  # then open http://localhost:8000
  ```
- **Search**: type any keyword (e.g. `reply`, `font`, `summary judgment`,
  `26(f)`, `LCvR 7.1`). Matches are highlighted and the row count updates live.
- **Filter**: click a category chip (Deadlines, Page / Word Limits,
  Formatting, Filing & Service, Motion Practice, Discovery).
- **Deep-link**: the URL hash reflects the current query + category; reload
  safe, shareable.
- **Print**: `Ctrl/Cmd+P` gives a clean print layout (header collapses,
  chips hidden).

## Structure

```
index.html          single-page UI
app.js              fetches data/rules.json; filter + render; no dependencies
styles.css          responsive + print styles
data/
  rules.json        source of truth — one entry per topic, three district cells
sources/
  EDNC-local-rules.md   provenance + rule index per district
  MDNC-local-rules.md
  WDNC-local-rules.md
```

## Data schema (`data/rules.json`)

```json
{
  "meta": {
    "sources": { "ednc": { "name": "...", "url": "...", "effective": "..." }, ... },
    "disclaimer": "..."
  },
  "rules": [
    {
      "id": "stable-kebab-id",
      "category": "Deadlines",
      "topic": "Short human-readable label",
      "ednc": { "value": "...", "cite": "L.Civ.R. 7.1(f)(1)" },
      "mdnc": { "value": "...", "cite": "LR 7.3(f)" },
      "wdnc": { "value": "...", "cite": "LCvR 7.1(e)" },
      "notes": "optional cross-district note"
    }
  ]
}
```

## Updating a rule when a district amends

1. Open the district's current local-rules PDF (links in `sources/*.md`).
2. Edit the matching row in `data/rules.json` — update `value`, `cite`, and
   any `notes`.
3. Bump the `meta.sources.<district>.effective` date.
4. Update the rule index in `sources/<DISTRICT>-local-rules.md` if rule
   numbers changed.
5. Commit. No build step — the change is live on reload.

## Current sources

- **EDNC** — Local Civil Rules of Practice and Procedure,
  [effective May 2023](https://www.nced.uscourts.gov/pdfs/Local%20Civil%20Rules%202023.pdf) ·
  [court rules page](https://www.nced.uscourts.gov/rules/default.aspx)
- **MDNC** — Rules of Practice and Procedure,
  [effective April 3, 2024](https://www.ncmd.uscourts.gov/sites/ncmd/files/CIV_LR_2024.pdf) ·
  [court rules page](https://www.ncmd.uscourts.gov/local-rules-and-orders)
- **WDNC** — Rules of Practice and Procedure (2017 ed.),
  [as revised effective Dec. 1, 2018](https://www.ncwd.uscourts.gov/sites/default/files/local_rules/Revised_Local_Rules_1.pdf) ·
  [court rules page](https://www.ncwd.uscourts.gov/court-info/local-rules-and-orders/local-rules)

## Disclaimer

This reference is a convenience summary, **not legal advice**. Local rules
change; judges' standing orders and case-specific scheduling orders may
supersede the defaults shown here. Always verify against the current rules
PDF and the assigned judge's standing order before filing.
