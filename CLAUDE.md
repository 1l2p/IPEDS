# IPEDS Explorer — Project Notes

## Overview
Single-page static web app exploring IPEDS (Integrated Postsecondary Education Data System) data for U.S. higher education institutions, 2014-2024. Vanilla JS, no frameworks. Runs locally via `python3 -m http.server 8080` or `file://`.

## Data Pipeline

### Step 1: Download raw CSVs
```bash
python3 download_ipeds.py
```
Downloads zip files from `https://nces.ed.gov/ipeds/datacenter/data/{COMPONENT}{YEAR}.zip` into `data/raw/{year}/`. Idempotent — skips existing files. ~346 MB total.

### Step 2: Preprocess into JSON
```bash
python3 preprocess.py
```
Reads all CSVs, merges by UNITID, outputs `data.json` and `data.js` (~33 MB). The `data.js` wrapper (`var IPEDS_DATA = ...`) enables `file://` usage without a server.

## Data Schema (Hybrid)
Static institution fields (name, city, state, lat/lng, hbcu, webAddr) stored once per institution. Time-varying fields nested under `yearData[year]`:
- Enrollment: totalEnroll, enrollMen/Women, enrollWhite/Black/Hispanic/Asian/AIAN/NHPI/TwoMore/Unknown/Nonresident
- Graduation: gradCohort, gradCompleters, gradRate
- Admissions: applications, admissions, enrolled, admRate, satMid, actMid, openAdmission
- Distance education: deExclusive, deSome, deNone
- Institutional: sector, sectorCode, control, locale, instSize

## IPEDS Data Sources by Component

| Component | File pattern | Key variables |
|-----------|-------------|---------------|
| HD | `hd{year}.csv` | UNITID, INSTNM, CITY, STABBR, SECTOR, HBCU, LATITUDE, LONGITUD |
| EFFY | `effy{year}.csv` | EFYTOTLT, demographic breakdowns. Filter: EFFYALEV=1/LSTUDY=999 (2020+) or EFFYLEV=1/LSTUDY=999 (pre-2020). LSTUDY means "level of study" NOT distance education. |
| GR | `gr{year}.csv` | GRTOTLT. Filter: SECTION=1, LINE=999, GRTYPE=2 (cohort) and 3 (completers). Values are whitespace-padded — must strip. |
| ADM | `adm{year}.csv` | APPLCN, ADMSSN, ENRLT, SATVR25/75, SATMT25/75, ACTCM25/75 |
| IC | `ic{year}.csv` | OPENADMP (open admission flag), DISTCRS/DISTPGS (DE offering flags) |
| EFFY_DIST | `effy{year}_dist.csv` (2020+) | EFYDEEXC, EFYDESOM, EFYDENON. Filter: EFFYDLEV=1 |
| EF_A_DIST | `ef{year}a_dist.csv` (2014-2019) | EFDEEXC, EFDESOM, EFDENON. Filter: EFDELEV=1 |

## Known Gotchas

- **LSTUDY in EFFY is NOT distance education.** It means level of study (1=Undergrad, 3=Graduate, 999=All). Distance education enrollment lives in separate EFFY_DIST / EF_A_DIST files.
- **EFFY_DIST only exists from 2020.** Pre-2020 uses EF_A_DIST (fall snapshot), which won't sum to the 12-month totalEnroll. The three DE categories are still correct, just measured over a different window.
- **GR/ADM values have whitespace padding** in downloaded CSVs. Always `.strip()` before comparing GRTYPE, SECTION, LINE, etc.
- **CSV encoding varies.** Some years use UTF-8 BOM, others latin-1. Use `encoding="utf-8-sig", errors="replace"` to handle both.
- **SAT scale changed in 2017.** Pre-2017 scores used the old 2400 scale; 2017+ uses the 1600 scale. Raw values are stored without conversion.
- **ADM and GR files for 2024** were not available on NCES at time of download (404). The local copies were from a prior manual download.
- **COVID impact on DE data.** 2020-2021 DE numbers may appear inflated — NCES guidance says pandemic remote instruction should be included in DE reporting.

## Frontend Architecture

- `fullData[]` holds the raw nested data; `allData[]` is a flat view for the currently selected year
- `flattenForYear(data, year)` spreads `yearData[year]` into flat records — all existing filter/sort/pagination/selection code works unchanged on `allData`
- Year switching calls `flattenForYear` then `applyFilters()`
- Trend charts use Chart.js (`lib/chart.umd.min.js`, local copy for offline use)
- Two chart modes: individual institution comparison (select 2-5 via checkboxes) and group average (for current filtered set)
