# Accuracy-verification playbook

A step-by-step procedure for an LLM-assisted accuracy sweep of one
district in `data/rules.json`. Meant to be followed by a Claude Code
session; every step is explicit so a fresh session can execute without
reconstructing intent.

This file lives in `scripts/` (tooling-side, inert on Pages). If you
want a personal slash command, symlink it:

```
ln -s "$(pwd)/scripts/verify-rules.md" ~/.claude/commands/verify-district.md
```

(We intentionally do **not** check a command file into `.claude/`;
that directory is gitignored per `CLAUDE.md`.)

## When to run

- Once per district as a baseline accuracy pass.
- After a district amends its local rules (updated PDF at the URL in
  `meta.sources.<district>.url`).
- Before any release / announcement touting the tool's accuracy.

## Scope for one run

**One district at a time.** Same PDF gets reused across that district's
~38 cells, which is cheap; mixing districts multiplies PDF context and
invites confusion between `L.Civ.R. 7.1` and `LCvR 7.1`.

## Hard rules

1. **Do NOT edit `data/rules.json` during the sweep.** Findings go to
   `reports/accuracy-<district>-<YYYY-MM-DD>.md`. Humans apply edits
   after reviewing. This mirrors the `sync-judges.py` boundary for
   overlays.
2. **Quote the PDF, don't paraphrase.** Every `DISCREPANCY` verdict
   must include the exact rule text (or a tight excerpt) so the
   human reviewer can verify without re-opening the PDF.
3. **Cite-driven, not topic-driven.** Follow the `cite` field to the
   rule in the PDF, then judge whether `value` reflects what's
   actually there. Do not reason "what should the rule be?" — read
   what it is.
4. **Flag, don't fix.** Ambiguity is a verdict. If the cited rule is
   present but the `value` paraphrases loosely, mark `AMBIGUOUS` and
   move on; don't try to reword it yourself.
5. **No made-up rule numbers.** If you cannot locate the cited rule
   in the PDF, the verdict is `DISCREPANCY` with reason
   "cite does not resolve" — not a guess at what the correct cite
   should be.

## Procedure

### 0. Pre-flight

```
python3 scripts/validate-rules.py
```

Must PASS before starting. The semantic sweep presumes the structural
invariants hold.

### 1. Inputs

- **District code**: `ednc` | `mdnc` | `wdnc`.
- **PDF URL**: read `meta.sources.<district>.url` from
  `data/rules.json`.
- **Effective date**: read `meta.sources.<district>.effective` — if
  the PDF's own effective date (inside the document) differs, that
  is a `DISCREPANCY` on the sources metadata.

### 2. Fetch the PDF

Use `WebFetch` (or equivalent) against the PDF URL. Cache the fetched
content under `scripts/.pdf-cache/<district>.pdf` (gitignored). Reuse
the cache across cells in one run; invalidate between runs.

If the fetch fails, **stop**. A broken source URL is itself a finding
worth filing — but attempting the sweep without the PDF is worse than
not running it.

### 3. Enumerate cells

From `data/rules.json`, collect every rule as:

```
{
  "id":       "<rule id>",
  "topic":    "<topic>",
  "category": "<category>",
  "cite":     "<district cite>",
  "value":    "<district value>"
}
```

for the chosen district. Expect ~38 cells.

### 4. Per-cell verification

For each cell:

1. Locate the cited rule in the PDF. Follow every citation in the
   `cite` field — e.g., `LR 7.3(f); LR 56.1(d)-(e)` means read both.
2. Produce one of three verdicts:
   - **OK** — `value` faithfully reflects what the cited rule says.
     Paraphrasing is allowed if the paraphrase would not mislead a
     practitioner filing a paper.
   - **DISCREPANCY** — `value` is wrong, stale, or materially
     misleading. Note the actual rule text and a proposed edit.
     A cite that does not resolve to anything in the PDF is also
     `DISCREPANCY`.
   - **AMBIGUOUS** — cite resolves and `value` is defensible but a
     careful reader could read it the other way. Flag for human
     judgment; do not propose an edit.
3. Record: rule id, topic, cite, current value, verdict, PDF
   excerpt (verbatim), proposed edit (only on `DISCREPANCY`).

### 5. Write the report

Create `reports/accuracy-<district>-<YYYY-MM-DD>.md`:

```markdown
# Accuracy sweep — <DISTRICT> — <YYYY-MM-DD>

- PDF: <url>
- PDF effective date (from document): <date>
- meta.sources.<district>.effective: <date>
- Cells reviewed: <N>
- OK: <n>  DISCREPANCY: <n>  AMBIGUOUS: <n>

## Findings

### <rule-id> — <topic>
- Cite: `<cite>`
- Current value: "<value>"
- Verdict: OK | DISCREPANCY | AMBIGUOUS
- PDF excerpt: "<verbatim>"
- Proposed edit (only on DISCREPANCY): "<new value>" / "<new cite>"
- Notes: <optional>

... repeat for every cell ...
```

Every cell appears in the report, even `OK` ones. A silent omission
is indistinguishable from a skipped check.

### 6. Hand off

Tell the user:

- Total cells, counts by verdict.
- Top 3 most serious discrepancies (if any).
- Whether `meta.sources.<district>.effective` matches the PDF's own
  effective date.
- Whether the `sources/<DISTRICT>-local-rules.md` "Captured" date
  needs bumping.

The user then decides which discrepancies to apply. Re-run
`python3 scripts/validate-rules.py` after each batch of edits to
catch any structural regression the hand-edits introduced (wrong
cite prefix, missing field, duplicate id).

## Anti-patterns

- **Silent skips.** If a cell cannot be verified (e.g., the PDF page
  is unreadable), record a verdict of `AMBIGUOUS` with reason
  "could not locate cited rule" — do not omit it.
- **Reasoning from other districts' cells.** The whole point of the
  tool is that the three districts differ. "EDNC says 21 days so
  WDNC probably does too" is exactly the failure mode to avoid.
- **Editorializing.** `notes` fields and `value` fields belong to
  the humans who wrote them; don't rewrite voice just because you'd
  phrase it differently. Only flag substantive discrepancies.
- **Touching `data/judges.json` overlays.** Out of scope for this
  sweep. Overlays are hand-curated per CLAUDE.md.

## Related tooling

- `scripts/validate-rules.py` — structural validator (run before and
  after). Must pass before the sweep and after any edits the sweep
  surfaces.
- `scripts/sync-judges.py` — roster sync for `data/judges.json`.
  Independent of this playbook.
