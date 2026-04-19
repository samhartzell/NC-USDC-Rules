#!/usr/bin/env python3
"""
validate-rules.py — structural validation for data/rules.json and
data/judges.json.

What it checks (and why):
  rules.json
    1. meta.sources has ednc/mdnc/wdnc, each with name, rulesTitle,
       effective, url, landing. `url` ends in .pdf (the site's "open
       source" link is expected to land on the PDF).
    2. meta.disclaimer is present and non-empty.
    3. Every rule has id, category, topic, and all three of ednc/mdnc/
       wdnc with non-empty value + cite. A missing cell renders as "—"
       in the UI, which is legal-tool malpractice if unintended.
    4. rule ids are unique and kebab-case.
    5. Citation prefixes match each district's own nomenclature
       (CLAUDE.md "Editorial rules"):
         EDNC -> L.Civ.R. | L.Crim.R.
         MDNC -> LR
         WDNC -> LCvR | LCrR
       Multi-cite strings ("LR 7.3(f); LR 56.1(d)-(e)") are checked on
       the first token only; the forgiving stance is deliberate.
       A cite wrapped in parentheses (e.g., "(judge preferences)",
       "(Fed. R. Civ. P. 30)") is treated as an explicit
       "no-local-rule" marker and permitted on any district.
  judges.json (optional — missing file is not a failure)
    6. Every judge id is kebab-case.
    7. Every key in each judge's `overlays` matches some rule id in
       rules.json. An overlay whose key does not resolve is silently
       invisible in the UI — the "malpractice trap" called out in
       CLAUDE.md.
    8. Every overlay has value + cite.
    9. Each judge's `lastUpdated`, when present, parses as YYYY-MM-DD.

What it does NOT check:
  - Whether the `value` text is factually correct. That requires
    reading the PDF and is intentionally deferred to the LLM sweep
    (see scripts/verify-rules.md).
  - Whether URLs are reachable. Link-checking belongs in a separate
    job; we do not want a transient outage to fail a local validation.
  - Whether rule ordering within a category is "right". The UI
    preserves JSON order deliberately.

Usage:
  python3 scripts/validate-rules.py            # PASS/FAIL summary
  python3 scripts/validate-rules.py --verbose  # list every check

Exit codes:
  0  all checks passed
  1  one or more structural issues
  2  rules.json missing or unparseable
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
RULES_JSON = os.path.join(REPO_ROOT, "data", "rules.json")
JUDGES_JSON = os.path.join(REPO_ROOT, "data", "judges.json")

DISTRICTS: Tuple[str, ...] = ("ednc", "mdnc", "wdnc")

# First-token citation prefixes, per district. A cell's cite is valid
# if it starts with one of these tokens followed by whitespace or end.
CITE_PREFIXES: Dict[str, Tuple[str, ...]] = {
    "ednc": ("L.Civ.R.", "L.Crim.R."),
    "mdnc": ("LR",),
    "wdnc": ("LCvR", "LCrR"),
}

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_FIELDS = ("name", "rulesTitle", "effective", "url", "landing")


@dataclass
class Report:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checks_run: int = 0

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self) -> bool:
        return not self.errors


def _load_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        sys.stderr.write("{}: invalid JSON: {}\n".format(path, exc))
        sys.exit(2)


def _is_nonempty_str(v) -> bool:
    return isinstance(v, str) and v.strip() != ""


def _cite_has_valid_prefix(cite: str, district: str) -> bool:
    stripped = cite.strip()
    if not stripped:
        return False
    # Parenthetical cites mark cells where no local rule governs
    # (e.g. "(judge preferences)", "(Fed. R. Civ. P. 30)"). Permitted
    # on any district; the LLM sweep is responsible for checking that
    # the `value` honestly states the absence.
    if stripped.startswith("("):
        return True
    first = stripped.split()
    token = first[0]
    return any(token == p or token.startswith(p) for p in CITE_PREFIXES[district])


def validate_rules(data: dict, report: Report, verbose: bool) -> Set[str]:
    """Returns the set of rule ids (used later by judges validation)."""
    rule_ids: Set[str] = set()

    meta = data.get("meta")
    if not isinstance(meta, dict):
        report.fail("meta: missing or not an object")
        return rule_ids
    report.checks_run += 1

    sources = meta.get("sources")
    if not isinstance(sources, dict):
        report.fail("meta.sources: missing or not an object")
    else:
        for d in DISTRICTS:
            report.checks_run += 1
            src = sources.get(d)
            if not isinstance(src, dict):
                report.fail("meta.sources.{}: missing".format(d))
                continue
            for key in SOURCE_FIELDS:
                if not _is_nonempty_str(src.get(key)):
                    report.fail("meta.sources.{}.{}: missing or empty".format(d, key))
            url = src.get("url", "")
            if isinstance(url, str) and not url.lower().endswith(".pdf"):
                report.fail(
                    "meta.sources.{}.url: expected a .pdf URL, got {!r}".format(d, url)
                )

    report.checks_run += 1
    if not _is_nonempty_str(meta.get("disclaimer")):
        report.fail("meta.disclaimer: missing or empty")

    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        report.fail("rules: missing or empty")
        return rule_ids

    for idx, rule in enumerate(rules):
        report.checks_run += 1
        where = "rules[{}]".format(idx)
        if not isinstance(rule, dict):
            report.fail("{}: not an object".format(where))
            continue

        rid = rule.get("id")
        if not _is_nonempty_str(rid):
            report.fail("{}: missing id".format(where))
        else:
            where = "rules[{}] (id={})".format(idx, rid)
            if rid in rule_ids:
                report.fail("{}: duplicate id".format(where))
            rule_ids.add(rid)
            if not KEBAB_RE.match(rid):
                report.fail("{}: id must be kebab-case, got {!r}".format(where, rid))

        if not _is_nonempty_str(rule.get("category")):
            report.fail("{}: missing category".format(where))
        if not _is_nonempty_str(rule.get("topic")):
            report.fail("{}: missing topic".format(where))

        for d in DISTRICTS:
            cell = rule.get(d)
            if not isinstance(cell, dict):
                report.fail("{}.{}: missing cell".format(where, d))
                continue
            if not _is_nonempty_str(cell.get("value")):
                report.fail("{}.{}.value: missing or empty".format(where, d))
            cite = cell.get("cite")
            if not _is_nonempty_str(cite):
                report.fail("{}.{}.cite: missing or empty".format(where, d))
            elif not _cite_has_valid_prefix(cite, d):
                expected = " | ".join(CITE_PREFIXES[d])
                report.fail(
                    "{}.{}.cite: first token does not match {} (got {!r})".format(
                        where, d, expected, cite
                    )
                )
            if verbose and _is_nonempty_str(cite):
                sys.stdout.write("  ok  {}.{}  {}\n".format(rid, d, cite))

    return rule_ids


def validate_judges(data: dict, rule_ids: Set[str], report: Report, verbose: bool) -> None:
    judges_by_district = data.get("judges")
    if not isinstance(judges_by_district, dict):
        report.fail("judges: missing or not an object")
        return

    for d in DISTRICTS:
        roster = judges_by_district.get(d)
        if roster is None:
            report.warn("judges.{}: absent (roster expected)".format(d))
            continue
        if not isinstance(roster, list):
            report.fail("judges.{}: expected array".format(d))
            continue
        for idx, judge in enumerate(roster):
            report.checks_run += 1
            where = "judges.{}[{}]".format(d, idx)
            if not isinstance(judge, dict):
                report.fail("{}: not an object".format(where))
                continue
            jid = judge.get("id")
            if not _is_nonempty_str(jid):
                report.fail("{}: missing id".format(where))
            else:
                where = "judges.{}[{}] (id={})".format(d, idx, jid)
                if not KEBAB_RE.match(jid):
                    report.fail("{}: id must be kebab-case".format(where))

            last_updated = judge.get("lastUpdated")
            if _is_nonempty_str(last_updated):
                if not ISO_DATE_RE.match(last_updated):
                    report.fail(
                        "{}.lastUpdated: expected YYYY-MM-DD, got {!r}".format(
                            where, last_updated
                        )
                    )
                else:
                    try:
                        _dt.date.fromisoformat(last_updated)
                    except ValueError:
                        report.fail("{}.lastUpdated: not a real date".format(where))

            overlays = judge.get("overlays") or {}
            if not isinstance(overlays, dict):
                report.fail("{}.overlays: expected object".format(where))
                continue
            for key, overlay in overlays.items():
                if key not in rule_ids:
                    report.fail(
                        "{}.overlays[{!r}]: no rule with that id exists; "
                        "overlay will be silently invisible".format(where, key)
                    )
                if not isinstance(overlay, dict):
                    report.fail(
                        "{}.overlays[{!r}]: not an object".format(where, key)
                    )
                    continue
                if not _is_nonempty_str(overlay.get("value")):
                    report.fail(
                        "{}.overlays[{!r}].value: missing or empty".format(where, key)
                    )
                if not _is_nonempty_str(overlay.get("cite")):
                    report.fail(
                        "{}.overlays[{!r}].cite: missing or empty".format(where, key)
                    )
                if verbose:
                    sys.stdout.write(
                        "  ok  judges.{}/{}  overlay:{}\n".format(d, jid, key)
                    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--verbose", action="store_true", help="list each check")
    args = parser.parse_args(argv)

    report = Report()

    rules_data = _load_json(RULES_JSON)
    if rules_data is None:
        sys.stderr.write("{}: not found\n".format(RULES_JSON))
        return 2

    rule_ids = validate_rules(rules_data, report, args.verbose)

    judges_data = _load_json(JUDGES_JSON)
    if judges_data is None:
        report.warn("{}: not found (skipping judges checks)".format(JUDGES_JSON))
    else:
        validate_judges(judges_data, rule_ids, report, args.verbose)

    for w in report.warnings:
        sys.stdout.write("WARN  {}\n".format(w))
    for e in report.errors:
        sys.stdout.write("FAIL  {}\n".format(e))

    summary = "{} check(s) run; {} rule id(s); {} warning(s); {} error(s)".format(
        report.checks_run, len(rule_ids), len(report.warnings), len(report.errors)
    )
    sys.stdout.write(("PASS  " if report.ok() else "FAIL  ") + summary + "\n")
    return 0 if report.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
