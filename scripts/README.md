# scripts/

Tooling for maintaining the data files. **The site itself has no build
step** — these scripts exist only to refresh `data/judges.json` and
validate `data/rules.json` / `data/judges.json` before commits. They
do not run on GitHub Pages.

Current tooling:

- `validate-rules.py` — stdlib-only structural validator for the two
  data files.
- `verify-rules.md` — playbook for an LLM-assisted accuracy sweep
  against each district's current PDF.
- `sync-judges.py` — roster refresh for `data/judges.json`.

## `validate-rules.py`

Checks the structure of `data/rules.json` and `data/judges.json`. No
dependencies beyond the Python standard library.

### Run

```
python3 scripts/validate-rules.py            # PASS/FAIL summary
python3 scripts/validate-rules.py --verbose  # list every check
```

Exit codes: `0` pass, `1` structural failures, `2` `rules.json` missing
or unparseable.

### What it catches

- Missing `value` or `cite` on any of the 114 district-rule cells.
- Citation prefixes that do not match the district's nomenclature
  (`L.Civ.R.` for EDNC, `LR` for MDNC, `LCvR`/`LCrR` for WDNC).
  Parenthetical cites such as `(judge preferences)` or
  `(Fed. R. Civ. P. 30)` are permitted on any district as explicit
  "no-local-rule" markers.
- Duplicate or non-kebab-case rule ids.
- Judge overlay keys that do not match any rule id (the "silent
  invisibility" trap called out in `CLAUDE.md`).
- Malformed `lastUpdated` dates on judges.

### What it does NOT catch

Whether a `value` is factually correct. That is semantic work and
belongs to the accuracy sweep described in `verify-rules.md`.

### When to run

- Before every commit that touches `data/`.
- After applying edits surfaced by an accuracy sweep.
- As a quick sanity check if the site starts rendering `—` in places
  it did not before.


## `verify-rules.md`

A step-by-step playbook for an LLM-assisted accuracy sweep of one
district. The sweep fetches the district's PDF, walks every cell,
and writes findings to `reports/accuracy-<district>-<date>.md` for
human review. **The sweep never edits `data/rules.json` directly** —
humans apply corrections.

See the file itself for the full procedure. Summary: run once per
district as a baseline, then again whenever a district amends its
local rules.

`reports/` and `scripts/.pdf-cache/` are gitignored; the signed-off
edits to `data/rules.json` are what lands in history, not the drafts.


## `sync-judges.py`

Refreshes `data/judges.json` against the three NC U.S. District Courts'
chambers pages.

### Install

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
```

### Run

```
python scripts/sync-judges.py            # writes data/judges.json
python scripts/sync-judges.py --dry-run  # prints diff, writes nothing
```

Exit codes: `0` on success, `2` if any court page failed to fetch
(roster is preserved in that case so a transient outage does not nuke
the file).

### What it does

1. Fetches the pinned roster-index URL for each district.
2. Parses out each judge's name, role (district vs. magistrate), status
   (active vs. senior), and chambers-page URL.
3. For each chambers page, scans for plausible standing-order links
   ("standing order", "individual practice", "scheduling", PDF files).
4. Merges into the existing `data/judges.json`, **preserving any
   hand-curated `overlays` and any explicitly-set `title`** on each
   judge. Roster metadata (name, role, status, chambersUrl,
   standingOrders, lastUpdated) is refreshed.
5. Bumps `meta.lastSync` to today.

### What it does NOT do

- It does **not** parse standing-order PDFs into structured `overlays`.
  Overlay entries are authored by hand after a human reads the relevant
  standing order. The script only surfaces the source-document URLs.
- It does **not** silently delete judges. A previous entry that no
  longer appears in the scrape is retained with a `_staleSince` date
  and logged to stderr; prune it manually during review.
- It does **not** auto-commit. Always diff `data/judges.json` before
  committing.

### Review checklist after running

1. `git diff data/judges.json` — scan for roster changes.
2. Spot-check any added judge against the court's site.
3. If any `_staleSince` keys appear, decide whether to prune that judge
   (retired / elevated / deceased) and remove the key once confirmed.
4. Commit with a message like `judges: sync roster YYYY-MM-DD`.

### When to run

- When a court announces a new appointment, confirmation, or senior-
  status transition.
- Quarterly as a hygiene pass.
- After updating `ROSTER_URLS` if a court restructures its site.

### Automation

`.github/workflows/sync-judges.yml` runs this script every Monday at
12:00 UTC and on manual dispatch, opening a PR (`judges: sync roster`)
when there is a diff. Local runs are still useful for (a) ad-hoc
verification before the next scheduled run, (b) testing changes to the
script itself, and (c) overlay-curation work where you want to surface
a newly published standing-order URL right now rather than waiting for
Monday.

### Editorial boundary

Do not add overlays from this script. Overlay wording must quote the
operative language from the standing order (see `CLAUDE.md` →
"Judges layer"), and that judgment call belongs to a human reviewer.
