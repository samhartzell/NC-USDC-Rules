# CLAUDE.md

Guidance for AI assistants working in this repository. Keep it up to date as
the codebase evolves.

## What this project is

A static, single-page web app that presents a searchable, side-by-side
comparison of the Local Rules of the three United States District Courts in
North Carolina: **EDNC** (Eastern), **MDNC** (Middle), and **WDNC** (Western).
The goal is one lookup instead of three PDFs — response deadlines, page/word
limits, formatting, filing procedures, motion practice, and discovery — each
row with citations to the governing local rule.

Hosted at <https://samhartzell.github.io/NC-USDC-Rules/> via GitHub Pages.

**This is a legal-reference tool.** Accuracy matters more than cleverness.
Do not invent, paraphrase, or "improve" rules without verifying against the
district's current PDF (linked in `sources/*.md` and `data/rules.json`).

## Stack and constraints

- **Vanilla JS, HTML, CSS. No dependencies. No build step.** The repo is
  uploaded as-is to GitHub Pages.
- Browser targets: modern evergreen browsers. `app.js` is intentionally ES5-ish
  (IIFE, `var`, `function` expressions) so it runs anywhere without a
  transpiler.
- Do not introduce npm, bundlers, frameworks, TypeScript, CSS preprocessors,
  or a `package.json`. If a task seems to require one, stop and ask.
- `scripts/` contains Python tooling (`validate-rules.py`,
  `sync-judges.py`) and the accuracy-sweep playbook (`verify-rules.md`).
  These are used offline to validate and refresh the data files. They
  are **not** shipped to Pages — only the static site is. Keep it that
  way.

## File layout

```
index.html                  single-page UI shell (header, search, chips, results, sources, footer)
app.js                      fetches data/rules.json + data/judges.json, filters, renders, hash routing
styles.css                  responsive + print styles (CSS variables at top)
data/
  rules.json                SOURCE OF TRUTH — one entry per topic, three district cells
  judges.json               per-district roster + chambers overlays, keyed by rule id
sources/
  EDNC-local-rules.md       provenance + index of rules cited in rules.json
  MDNC-local-rules.md
  WDNC-local-rules.md
  judges.md                 provenance for data/judges.json (roster URLs, per-judge review dates)
scripts/
  validate-rules.py         stdlib-only structural validator for data/
  verify-rules.md           LLM accuracy-sweep playbook (run per district)
  sync-judges.py            tooling: refreshes data/judges.json from chambers pages
  requirements.txt          Python deps for sync-judges.py only (not shipped)
  README.md                 how to run the scripts and the playbook
.github/workflows/pages.yml GitHub Pages deploy (push to main → redeploy)
README.md                   user-facing docs
```

## Data model (`data/rules.json`)

```json
{
  "meta": {
    "sources": {
      "ednc": { "name": "...", "rulesTitle": "...", "effective": "...", "url": "...(PDF)...", "landing": "...(court page)..." },
      "mdnc": { ... },
      "wdnc": { ... }
    },
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

Conventions:

- **`id`**: stable kebab-case slug. Treat as permanent — it's effectively the
  row's identity. Don't rename unless truly necessary; if renamed, nothing
  links by id today but future deep links may.
- **`category`**: one of the existing values. Current categories (and their
  display order is the order of first appearance in `rules`):
  `Deadlines`, `Page / Word Limits`, `Formatting`, `Filing & Service`,
  `Motion Practice`, `Discovery`. Add a new category only if a rule genuinely
  doesn't fit; it will auto-appear as a chip and heading.
- **District keys**: always `ednc`, `mdnc`, `wdnc` (lowercase). All three are
  expected; if a district has no specific rule, still populate `value` with a
  brief explanation (e.g. "Set by the presiding judge's scheduling order") and
  a best-available `cite`. Missing cells render as `—`.
- **`cite` format**: use the district's own nomenclature — EDNC uses
  `L.Civ.R.`, MDNC uses `LR`, WDNC uses `LCvR` (and `LCrR` for criminal).
  Monospace styling is applied in CSS; don't add backticks.
- **`value`**: terse and concrete. Prefer "21 days after service of the
  motion" over a paragraph. If a number depends on a judge's standing order,
  say so.
- **`notes`**: optional, cross-district caveat. Appears once under the row.
- Preserve the existing ordering within each category unless there is a
  reason to reorder; the renderer groups by category but within a group it
  preserves JSON order.

## Judges layer (`data/judges.json`)

The judges layer sits on top of the base rule view. When a user picks a
judge from the per-district dropdown, each of that district's cells
gains a highlighted sub-block showing any known chambers-specific
deviation plus a `lastUpdated` date. When no judge is picked, the layer
is inert.

### Schema

```json
{
  "meta": {
    "lastSync": "2026-04-18",
    "rosterStatus": "…optional humans-only note…",
    "disclaimer": "…"
  },
  "judges": {
    "ednc": [
      {
        "id": "dever-james-c",
        "name": "James C. Dever III",
        "role": "district",            // "district" | "magistrate"
        "status": "active",            // "active" | "senior"
        "title": "Chief Judge",        // optional
        "chambersUrl": "https://...",  // court's page for this judge
        "standingOrders": [
          { "title": "Standing Order re: Courtesy Copies",
            "url": "https://...", "effective": "2024-01-15" }
        ],
        "lastUpdated": "2026-04-18",
        "overlays": {
          "courtesy-copies": {
            "value": "Paper courtesy copies required for motions > 25 pages.",
            "cite": "Dever Standing Order (Jan. 2024)",
            "url": "https://..."
          }
        }
      }
    ],
    "mdnc": [ ... ],
    "wdnc": [ ... ]
  }
}
```

### Conventions

- **`id`**: `lastname-firstname-middleinitial[-suffix]`. Stable. Don't
  rename unless truly necessary.
- **`overlays` keys must match `id` values in `data/rules.json`.** If
  the rule id changes there, update every judge's overlay accordingly.
  An overlay whose key doesn't match any rule id is silently invisible.
- **Overlay `value` must quote / paraphrase the standing order
  tightly.** Do not editorialize. If the standing order says "25 pages
  or more", write that, not "long motions".
- **Every overlay gets a `cite`**, ideally to a titled standing order
  with an effective date. A `url` is strongly preferred so users can
  open the source PDF.
- **`lastUpdated`** is user-visible (rendered as `upd. YYYY-MM-DD` in
  each overlay block). Bump it any time you touch that judge's
  `overlays` or `standingOrders`.
- **Senior judges still hear cases** — keep them in the roster.
- **Missing overlay ≠ "rule does not apply"**, it means "no
  chambers-specific deviation known". The site renders nothing in that
  case rather than a misleading reassurance.

### Sync script boundary

`scripts/sync-judges.py` refreshes roster metadata (name, role, status,
chambersUrl, standingOrders, lastUpdated) from the courts' sites. It
**preserves** the hand-curated `overlays` object and any explicit
`title` field. It does not attempt to parse standing-order PDFs into
overlays — that is a human judgment call.

## How `app.js` works (so you don't re-read it each time)

1. `fetch('data/rules.json', { cache: 'no-store' })` → parse → chain a
   second (non-fatal) fetch for `data/judges.json` → call `init()`. A
   missing or malformed `judges.json` hides the judge picker but
   leaves the base view working.
2. `init()` renders the sources block, builds category chips from the set of
   `r.category` values (first-occurrence order, with `All` prepended),
   renders the three per-district judge `<select>`s, restores `state`
   from `location.hash` (`#cat=...&q=...&j=ednc:dever-james-c`), binds
   events, and calls `render()`.
3. `render()` filters by `state.category` + lowercased `state.query` (matched
   against topic, category, notes, each district's `value`/`cite`, and
   any selected judge's overlay text for that rule), groups by category,
   and writes HTML into `#results`.
4. `renderCell` appends a `.cell-overlay` block per district whenever
   `state.selectedJudge[district]` resolves to a judge with an
   `overlays[rule.id]` entry. If there's no overlay for that rule, the
   cell renders unchanged.
5. Search is debounced 80ms. Query/category/judge changes write to the
   URL hash via `history.replaceState` (reload- and share-safe).
6. Every string that touches HTML goes through `escapeHtml` / `escapeAttr`.
   `highlight()` escapes first, then wraps matches in `<mark class="hit">`.
   **Preserve this**: any new field that ends up in rendered HTML must be
   escaped the same way. Do not build HTML from un-escaped user input.

If you add a new field to a rule, update `matchesQuery` if it should be
searchable, and update `renderRow` / `renderCell` to display it. If you
add a new field to a judge or overlay, mirror the same escape discipline
in `renderOverlay`.

## Styles (`styles.css`)

- CSS custom properties at the top of `:root` — change colors there, not
  scattered through the file.
- Layout is a 3-column CSS grid at ≥ 900px that collapses to a single column
  below that breakpoint.
- There is a dedicated `@media print` block: controls and footer are hidden,
  rows avoid break-inside. Verify print layout still works after any
  structural HTML change (Ctrl/Cmd+P in a browser is sufficient).

## Local development

No build. Serve the directory as static files:

```
cd NC-USDC-Rules
python3 -m http.server 8000
# open http://localhost:8000
```

Opening `index.html` directly over `file://` often works, but some browsers
block `fetch()` on local files, which breaks data loading. Use the HTTP
server when in doubt.

There is no test suite, linter, or type checker. After any change, smoke-test:

1. Page loads; "Loading rules…" is replaced by grouped rows.
2. Typing in the search box filters live and highlights matches.
3. Clicking a category chip filters; the URL hash updates.
4. Reloading with a hash (`#cat=Deadlines&q=reply`) restores state.
5. Print preview still looks clean.

## Verifying accuracy

Two-part check, both under `scripts/`:

1. **Structural validator** — `python3 scripts/validate-rules.py`.
   Catches missing cells, wrong citation prefixes, duplicate ids,
   orphaned judge overlays, and bad `lastUpdated` dates. Run before
   every commit that touches `data/`.

2. **LLM accuracy sweep** — `scripts/verify-rules.md`. A playbook a
   Claude Code session follows to verify one district's cells
   against its current PDF. Findings land in `reports/` (gitignored)
   for human review; the sweep never edits `data/rules.json`
   directly. Run once per district as a baseline, and again after
   any district amends its local rules.

The validator is fast and objective. The sweep is slow and requires
judgment. Neither replaces the other.

## Updating rules when a district amends its local rules

1. Open the district's current local-rules PDF (links in `sources/<DISTRICT>-local-rules.md`
   and in `data/rules.json` under `meta.sources`).
2. For each affected row in `data/rules.json`, update the district's
   `value`, `cite`, and any `notes`. Keep `id` stable.
3. Bump `meta.sources.<district>.effective` to the new effective date.
4. If rule numbers changed, update the rule-index table in
   `sources/<DISTRICT>-local-rules.md` and the "Captured" date at the top.
5. Commit with a message describing the amendment (e.g. "EDNC: update reply
   deadline to 14 days per 2026 amendments").

No build, no cache-busting — a push to `main` redeploys.

## Deploy

`.github/workflows/pages.yml` publishes the repo as-is to GitHub Pages on
every push to `main`, and supports manual `workflow_dispatch`. There is no
build step; `path: .` uploads the whole repo. Do not add secrets, server-side
logic, or large binary assets — everything here is shipped to end users.

`.github/workflows/sync-judges.yml` runs `scripts/sync-judges.py` on a
weekly schedule (Mondays 12:00 UTC) and on `workflow_dispatch`. When the
script produces a diff it opens a PR titled `judges: sync roster` from
the stable branch `bot/sync-judges` against `main`. The workflow only
touches roster metadata — `overlays` are still hand-curated, and the
"don't fabricate overlays" rule below applies to anything merged from
that PR.

## Branching and commits

- Development branches follow the pattern `claude/<short-topic>-<suffix>`
  when created by an AI assistant (see current session guidance).
- Never force-push, never push to `main` directly without explicit
  instruction, and never create a PR unless the user explicitly asks.
- Commit messages: imperative, concise, explain the "why" when not obvious.
  Existing history uses short subjects like "Upgrade actions/checkout to v5"
  and "Publish to GitHub Pages".

## Editorial and legal-accuracy rules

- **Cite every substantive claim.** Every `value` gets a `cite`. If you
  truly can't find one, say so in `value` rather than leaving `cite` blank.
- **Don't generalize across districts.** Each district's cell reflects only
  that district's rule. Differences belong in separate cells; cross-district
  commentary goes in `notes`.
- **Don't invent numbers.** Page, word, and day limits must come from the
  PDF. If a number isn't in the local rules (e.g. no cap on interrogatories
  in EDNC/WDNC), say so explicitly.
- **Judges' standing orders can override local rules** (notably in WDNC).
  Where that matters, mention it in the cell or in `notes`.
- Preserve the "Not legal advice" disclaimer in `meta.disclaimer` and the
  footer of `index.html`.

## What not to do

- Don't add build tooling, dependencies, or a package manager.
- Don't rewrite `app.js` to use modern syntax "for cleanliness" — the ES5
  style is intentional.
- Don't reorganize `data/rules.json` just to tidy it; downstream ordering is
  visible to users.
- Don't add tracking, analytics, or external scripts to `index.html`.
- Don't change `id` values without a deliberate reason.
- Don't fabricate overlays in `data/judges.json`. If a chambers page
  has no standing order on a topic, leave the overlay absent. An empty
  object is correct; a guessed value is a malpractice trap.
- Don't ship `scripts/` outputs or Python deps to the site. The sync
  script is a tooling-side utility; GitHub Pages uploads the repo but
  the Python files are inert there.
- Don't commit `.DS_Store`, editor files, or `.claude/` (already gitignored).
