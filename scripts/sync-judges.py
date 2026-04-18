#!/usr/bin/env python3
"""
sync-judges.py — refresh data/judges.json against the three NC U.S. District
Courts' chambers pages.

What it does:
  1. Fetches the judge-index page for each district (URLs pinned below).
  2. Extracts each judge's display name, role (district vs. magistrate),
     status (active vs. senior), and chambers-page URL.
  3. For each chambers page, tries to discover standing-order /
     individual-practices links (heuristic: link text contains
     "standing order", "individual practice", "scheduling", or the URL
     is a PDF on the same host).
  4. Merges results into data/judges.json. HAND-CURATED fields on each
     judge (anything under `overlays`, plus a manually set `title`) are
     preserved; the script overwrites only roster metadata
     (name, role, status, chambersUrl, standingOrders, lastUpdated) and
     the top-level meta.lastSync field.
  5. Emits a short diff summary to stdout.

Usage:
  pip install -r scripts/requirements.txt
  python scripts/sync-judges.py            # writes data/judges.json
  python scripts/sync-judges.py --dry-run  # prints the diff, writes nothing

Non-goals:
  - This script does NOT parse standing-order PDFs into structured
    overlays. Overlay entries are authored by hand after a human reads
    the standing order. See CLAUDE.md ("Judges layer") for the editorial
    rules.
  - The script does not hit the Internet Archive or any cache; if a court
    restructures its site the pinned URL fails loudly. That is intentional
    — silent roster changes would be worse than a CI failure.

Exit codes:
  0 on success (even if zero diff); non-zero on any fetch failure or
  parse failure. That way CI can be scheduled nightly and alert on
  broken URLs.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.stderr.write(
        "Missing dependency. Run:  pip install -r scripts/requirements.txt\n"
    )
    raise


# --- Config -----------------------------------------------------------------

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
JUDGES_JSON = os.path.join(REPO_ROOT, "data", "judges.json")

# Pinned roster-index URLs. When a court restructures its site the
# corresponding scrape throws; do NOT add silent fallbacks.
ROSTER_URLS: Dict[str, str] = {
    "ednc": "https://www.nced.uscourts.gov/judges/default.aspx",
    "mdnc": "https://www.ncmd.uscourts.gov/judges",
    "wdnc": "https://www.ncwd.uscourts.gov/judges",
}

# Words in a judge's display name or heading that identify their role.
MAGISTRATE_TOKENS = ("magistrate",)
SENIOR_TOKENS = ("senior",)

# Link-text heuristics for discovering standing orders on a chambers page.
STANDING_ORDER_PATTERNS = [
    re.compile(r"standing\s+order", re.I),
    re.compile(r"individual\s+(practice|rule)", re.I),
    re.compile(r"scheduling(?!\s+conference)", re.I),
    re.compile(r"courtesy\s+cop", re.I),
    re.compile(r"chambers\s+(rule|procedure|preference)", re.I),
]

# Name-to-ID normalization.  "James C. Dever III" -> "dever-james-c".
_SUFFIX_RE = re.compile(r"^(jr|sr|ii|iii|iv|v)\.?$", re.I)


# --- Types ------------------------------------------------------------------

@dataclass
class StandingOrder:
    title: str
    url: str
    effective: Optional[str] = None


@dataclass
class Judge:
    id: str
    name: str
    role: str  # "district" | "magistrate"
    status: str  # "active" | "senior"
    chambersUrl: str = ""
    title: Optional[str] = None
    standingOrders: List[StandingOrder] = field(default_factory=list)
    lastUpdated: str = ""
    overlays: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def to_json(self) -> dict:
        out: Dict = {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
        }
        if self.title:
            out["title"] = self.title
        out["chambersUrl"] = self.chambersUrl
        out["standingOrders"] = [
            {k: v for k, v in vars(so).items() if v is not None}
            for so in self.standingOrders
        ]
        out["lastUpdated"] = self.lastUpdated
        out["overlays"] = self.overlays
        return out


# --- Utilities --------------------------------------------------------------

def slugify_name(name: str) -> str:
    """'James C. Dever III' -> 'dever-james-c'."""
    cleaned = re.sub(r"[.,]", "", name).strip()
    parts = cleaned.split()
    if not parts:
        return ""
    # Strip trailing suffixes (III, Jr, etc.) from the last-name slot
    # but retain them as a trailing token so they stay distinct
    # (e.g. Osteen Jr. vs. Osteen Sr.).
    suffixes: List[str] = []
    while len(parts) > 1 and _SUFFIX_RE.match(parts[-1]):
        suffixes.insert(0, parts.pop().rstrip("."))
    last = parts[-1]
    rest = parts[:-1]
    tokens = [last] + rest + suffixes
    tokens = [t.lower() for t in tokens]
    tokens = [re.sub(r"[^a-z0-9]+", "", t) for t in tokens if t]
    return "-".join(t for t in tokens if t)


def classify_role(heading: str) -> str:
    low = heading.lower()
    if any(t in low for t in MAGISTRATE_TOKENS):
        return "magistrate"
    return "district"


def classify_status(heading: str) -> str:
    low = heading.lower()
    if any(t in low for t in SENIOR_TOKENS):
        return "senior"
    return "active"


def fetch(url: str, *, session: requests.Session) -> str:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


# --- Scrapers ---------------------------------------------------------------

def scrape_roster(district: str, html: str, base_url: str) -> List[Judge]:
    """Best-effort roster parse.

    Court websites differ; this parser looks for common patterns —
    anchor tags whose text looks like a judge's name, grouped under a
    heading that identifies district vs. magistrate and active vs.
    senior.  It intentionally errs toward including plausible names
    and reporting mismatches in stdout; a human should review the diff
    before committing.
    """
    soup = BeautifulSoup(html, "html.parser")
    today = _dt.date.today().isoformat()

    judges: Dict[str, Judge] = {}
    current_heading = ""

    # Walk the document flatly; pick up headings (h1/h2/h3) to classify,
    # and anchor tags whose text looks like "Hon. Jane A. Doe" or
    # "Jane A. Doe".
    for el in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
        if el.name in {"h1", "h2", "h3", "h4"}:
            current_heading = el.get_text(" ", strip=True)
            continue
        href = el.get("href") or ""
        text = el.get_text(" ", strip=True)
        if not text or len(text) > 80:
            continue
        # Strip salutation
        name = re.sub(r"^\s*(the\s+)?hon(orable|\.)?\s+", "", text, flags=re.I).strip()
        # Heuristic: a plausible judge name has at least two capitalized
        # tokens and no digits other than roman-numeral suffixes.
        tokens = name.split()
        if len(tokens) < 2:
            continue
        if any(tok[:1].islower() for tok in tokens if tok.isalpha()):
            continue
        if re.search(r"\d", name) and not re.search(r"(II|III|IV)\b", name):
            continue

        jid = slugify_name(name)
        if not jid:
            continue

        chambers_url = urllib.parse.urljoin(base_url, href) if href else ""
        role = classify_role(current_heading)
        status = classify_status(current_heading)
        judges.setdefault(jid, Judge(
            id=jid,
            name=name,
            role=role,
            status=status,
            chambersUrl=chambers_url,
            lastUpdated=today,
        ))
    return list(judges.values())


def scrape_standing_orders(
    chambers_url: str, *, session: requests.Session
) -> List[StandingOrder]:
    if not chambers_url:
        return []
    try:
        html = fetch(chambers_url, session=session)
    except Exception as exc:
        sys.stderr.write(f"  ! chambers fetch failed ({chambers_url}): {exc}\n")
        return []
    soup = BeautifulSoup(html, "html.parser")
    orders: List[StandingOrder] = []
    seen: set = set()
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        text = a.get_text(" ", strip=True)
        if not text:
            continue
        matches_text = any(p.search(text) for p in STANDING_ORDER_PATTERNS)
        is_pdf = href.lower().endswith(".pdf")
        if not (matches_text or (is_pdf and "standing" in text.lower())):
            continue
        abs_url = urllib.parse.urljoin(chambers_url, href)
        key = (text.strip().lower(), abs_url)
        if key in seen:
            continue
        seen.add(key)
        orders.append(StandingOrder(title=text.strip(), url=abs_url))
    return orders


# --- Merge ------------------------------------------------------------------

def load_existing() -> dict:
    if not os.path.exists(JUDGES_JSON):
        return {"meta": {}, "judges": {"ednc": [], "mdnc": [], "wdnc": []}}
    with open(JUDGES_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def existing_overlay_for(old_entries: Iterable[dict], jid: str) -> Optional[dict]:
    for e in old_entries:
        if e.get("id") == jid:
            return e
    return None


def merge_district(
    district: str,
    scraped: List[Judge],
    previous: List[dict],
) -> List[dict]:
    """Merge scraped roster onto previous entries, preserving overlays."""
    prev_by_id = {e.get("id"): e for e in previous}
    out: List[dict] = []

    for j in scraped:
        prev = prev_by_id.get(j.id)
        if prev:
            # Preserve hand-curated fields.
            j.overlays = prev.get("overlays") or {}
            # Preserve an explicit title (e.g., "Chief Judge") if set.
            if prev.get("title") and not j.title:
                j.title = prev["title"]
            # If chambersUrl already pointed at a deeper page, keep it
            # unless the scrape surfaced a more specific link.
            if not j.chambersUrl and prev.get("chambersUrl"):
                j.chambersUrl = prev["chambersUrl"]
        out.append(j.to_json())

    # Report any previous judges we didn't re-find (possible removals).
    prev_ids = set(prev_by_id)
    new_ids = {j.id for j in scraped}
    dropped = prev_ids - new_ids
    for jid in sorted(dropped):
        sys.stderr.write(
            f"  - {district.upper()}: previous entry {jid!r} not re-scraped. "
            "Review manually before committing.\n"
        )
        # Carry the stale entry forward so we never silently delete data.
        # The human review step can prune it.
        stale = dict(prev_by_id[jid])
        stale.setdefault("status", stale.get("status", "unknown"))
        stale["_staleSince"] = _dt.date.today().isoformat()
        out.append(stale)

    # Sort: district first, then magistrate; alphabetical by last name
    # (assuming the id prefix is the last name).
    def sort_key(e: dict):
        role_rank = 0 if e.get("role") == "district" else 1
        return (role_rank, e.get("id", ""))

    out.sort(key=sort_key)
    return out


# --- Diff reporting ---------------------------------------------------------

def diff_summary(before: dict, after: dict) -> str:
    lines = []
    for d in ("ednc", "mdnc", "wdnc"):
        old = {e["id"] for e in before.get("judges", {}).get(d, [])}
        new = {e["id"] for e in after.get("judges", {}).get(d, [])}
        added = sorted(new - old)
        removed = sorted(old - new)
        dist_ct = sum(
            1 for e in after["judges"][d] if e.get("role") == "district"
        )
        mag_ct = sum(
            1 for e in after["judges"][d] if e.get("role") == "magistrate"
        )
        lines.append(
            f"{d.upper()}: {dist_ct} district + {mag_ct} magistrate"
            + (f"; added {added}" if added else "")
            + (f"; no-longer-scraped {removed}" if removed else "")
        )
    return "\n".join(lines)


# --- Main -------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the diff summary but do not write data/judges.json.",
    )
    args = ap.parse_args()

    before = load_existing()
    after_judges: Dict[str, List[dict]] = {}

    session = requests.Session()
    session.headers["User-Agent"] = (
        "NC-USDC-Rules sync-judges.py "
        "(+https://github.com/samhartzell/nc-usdc-rules)"
    )

    failures = 0
    for district, url in ROSTER_URLS.items():
        print(f"[{district}] fetching roster: {url}", file=sys.stderr)
        try:
            html = fetch(url, session=session)
        except Exception as exc:
            sys.stderr.write(f"  ! roster fetch failed: {exc}\n")
            failures += 1
            # Keep the old roster intact so one broken URL does not
            # nuke the whole file.
            after_judges[district] = before.get("judges", {}).get(district, [])
            continue
        scraped = scrape_roster(district, html, url)
        for j in scraped:
            j.standingOrders = scrape_standing_orders(
                j.chambersUrl, session=session
            )
        previous = before.get("judges", {}).get(district, [])
        after_judges[district] = merge_district(district, scraped, previous)

    after = {
        "meta": {
            **(before.get("meta") or {}),
            "lastSync": _dt.date.today().isoformat(),
        },
        "judges": after_judges,
    }

    print(diff_summary(before, after))

    if args.dry_run:
        print("(dry-run) data/judges.json not modified.", file=sys.stderr)
        return 0 if failures == 0 else 2

    with open(JUDGES_JSON, "w", encoding="utf-8") as fh:
        json.dump(after, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    print(f"wrote {JUDGES_JSON}", file=sys.stderr)
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
