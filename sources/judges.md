# Judges — provenance

Source URLs and review dates for the roster in `data/judges.json`.

> **Roster status (2026-04-18):** initial seed. Entries were drawn from
> the court sites listed below but have **not yet been verified by a
> run of `scripts/sync-judges.py`**. Treat this file and
> `data/judges.json` as best-effort until the first sync pass. Overlay
> blocks on every judge are deliberately empty; they get populated by
> hand as standing orders are reviewed.

## Roster-index URLs

The sync script (`scripts/sync-judges.py`) pins these URLs. If a court
restructures its site, update the constant there and the corresponding
entry below.

| District | Roster index | Captured |
|---|---|---|
| EDNC | https://www.nced.uscourts.gov/judges/default.aspx | 2026-04-18 |
| MDNC | https://www.ncmd.uscourts.gov/judges | 2026-04-18 |
| WDNC | https://www.ncwd.uscourts.gov/judges | 2026-04-18 |

## EDNC — Eastern District of North Carolina

| Judge | Role | Status | Last reviewed |
|---|---|---|---|
| Richard E. Myers II | District (Chief) | active | 2026-04-18 |
| James C. Dever III | District | active | 2026-04-18 |
| Louise W. Flanagan | District | active | 2026-04-18 |
| Terrence W. Boyle | District | senior | 2026-04-18 |
| Malcolm J. Howard | District | senior | 2026-04-18 |
| Robert B. Jones, Jr. | Magistrate | active | 2026-04-18 |
| Kimberly A. Swank | Magistrate | active | 2026-04-18 |
| Robert T. Numbers, II | Magistrate | active | 2026-04-18 |
| Brian S. Meyers | Magistrate | active | 2026-04-18 |

## MDNC — Middle District of North Carolina

| Judge | Role | Status | Last reviewed |
|---|---|---|---|
| Catherine C. Eagles | District (Chief) | active | 2026-04-18 |
| Loretta C. Biggs | District | active | 2026-04-18 |
| William L. Osteen, Jr. | District | active | 2026-04-18 |
| Thomas D. Schroeder | District | active | 2026-04-18 |
| N. Carlton Tilley, Jr. | District | senior | 2026-04-18 |
| James A. Beaty, Jr. | District | senior | 2026-04-18 |
| L. Patrick Auld | Magistrate (Chief) | active | 2026-04-18 |
| Joe L. Webster | Magistrate | active | 2026-04-18 |
| Joi Elizabeth Peake | Magistrate | active | 2026-04-18 |

## WDNC — Western District of North Carolina

| Judge | Role | Status | Last reviewed |
|---|---|---|---|
| Robert J. Conrad, Jr. | District (Chief) | active | 2026-04-18 |
| Frank D. Whitney | District | active | 2026-04-18 |
| Max O. Cogburn, Jr. | District | active | 2026-04-18 |
| Martin Reidinger | District | active | 2026-04-18 |
| Kenneth D. Bell | District | active | 2026-04-18 |
| Graham C. Mullen | District | senior | 2026-04-18 |
| David S. Cayer | Magistrate | active | 2026-04-18 |
| Dennis L. Howell | Magistrate | active | 2026-04-18 |
| W. Carleton Metcalf | Magistrate | active | 2026-04-18 |
| Susan C. Rodriguez | Magistrate | active | 2026-04-18 |

## Notes / pitfalls

- **WDNC leans heavily on scheduling orders.** Many of the entries in
  `data/rules.json` that read "Set by the presiding judge's scheduling
  order" will get their real answer here once overlays are filled in.
- **Senior judges still hear cases.** Do not filter them out of the
  picker; a case can absolutely be assigned to a senior judge.
- **Magistrate pairing matters for discovery.** In EDNC in particular,
  the magistrate assigned to a case often has a distinct meet-and-confer
  format for discovery disputes; record these under the magistrate
  judge's entry, not the district judge's.
- **Standing orders vs. individual practices.** Some judges publish a
  single "standing order"; others publish a set of "individual practices"
  or "chambers procedures". Treat both as source material; record the
  actual title verbatim in `standingOrders[].title`.
- **Case-specific scheduling orders override both.** This layer is
  chambers-wide defaults only; a Rule 16 scheduling order in a given
  case controls for that case.
