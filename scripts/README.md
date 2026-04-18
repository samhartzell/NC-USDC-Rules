# scripts/

Tooling for maintaining the judges layer. **The site itself has no build
step** — these scripts exist only to refresh `data/judges.json`. They do
not run on GitHub Pages.

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

### Editorial boundary

Do not add overlays from this script. Overlay wording must quote the
operative language from the standing order (see `CLAUDE.md` →
"Judges layer"), and that judgment call belongs to a human reviewer.
