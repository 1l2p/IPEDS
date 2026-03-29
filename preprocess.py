#!/usr/bin/env python3
"""Preprocess IPEDS CSV files (2014-2024) into a single multi-year JSON for the web explorer.

Produces a hybrid schema: static institution fields stored once, time-varying
fields nested under yearData[year].
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

YEARS = range(2014, 2025)
RAW_DIR = Path("data/raw")

SECTOR_LABELS = {
    "0": "Administrative Unit",
    "1": "Public, 4-year+",
    "2": "Private nonprofit, 4-year+",
    "3": "Private for-profit, 4-year+",
    "4": "Public, 2-year",
    "5": "Private nonprofit, 2-year",
    "6": "Private for-profit, 2-year",
    "7": "Public, <2-year",
    "8": "Private nonprofit, <2-year",
    "9": "Private for-profit, <2-year",
    "99": "Unknown",
}

CONTROL_LABELS = {
    "-3": "N/A",
    "1": "Public",
    "2": "Private nonprofit",
    "3": "Private for-profit",
}

LOCALE_LABELS = {
    "11": "City: Large",
    "12": "City: Midsize",
    "13": "City: Small",
    "21": "Suburb: Large",
    "22": "Suburb: Midsize",
    "23": "Suburb: Small",
    "31": "Town: Fringe",
    "32": "Town: Distant",
    "33": "Town: Remote",
    "41": "Rural: Fringe",
    "42": "Rural: Distant",
    "43": "Rural: Remote",
    "-3": "N/A",
}

INSTSIZE_LABELS = {
    "-1": "Not reported",
    "-2": "Not applicable",
    "1": "Under 1,000",
    "2": "1,000 - 4,999",
    "3": "5,000 - 9,999",
    "4": "10,000 - 19,999",
    "5": "20,000+",
}


def safe_int(val: str | None) -> int | None:
    """Convert to int, returning None for missing/invalid values."""
    if val is None or val.strip() in ("", ".", "-2", "-1"):
        return None
    try:
        return int(val)
    except ValueError:
        return None


def safe_int_keep_special(val: str | None) -> int | None:
    """Convert to int, returning None only for truly missing values.

    Unlike safe_int, does not treat -1/-2 as missing (used for codes).
    """
    if val is None or val.strip() in ("", "."):
        return None
    try:
        return int(val)
    except ValueError:
        return None


def safe_float(val: str | None) -> float | None:
    if val is None or val.strip() in ("", "."):
        return None
    try:
        return float(val)
    except ValueError:
        return None


def csv_path(year: int, component: str) -> Path:
    """Return the path to a CSV file for a given year and component."""
    return RAW_DIR / str(year) / f"{component}{year}.csv"


def load_hd(year: int) -> dict:
    """Load institutional directory data for a given year.

    Returns dict mapping UNITID -> {static_fields, year_fields}.
    """
    path = csv_path(year, "hd")
    if not path.exists():
        print(f"  [warn] {path} not found")
        return {}

    institutions = {}
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["UNITID"]
            institutions[uid] = {
                "static": {
                    "id": uid,
                    "name": row.get("INSTNM", ""),
                    "city": row.get("CITY", ""),
                    "state": row.get("STABBR", ""),
                    "lat": safe_float(row.get("LATITUDE")),
                    "lng": safe_float(row.get("LONGITUD")),
                    "webAddr": row.get("WEBADDR", ""),
                    "hbcu": row.get("HBCU", "") == "1",
                },
                "year": {
                    "sector": SECTOR_LABELS.get(row.get("SECTOR", ""), ""),
                    "sectorCode": row.get("SECTOR", ""),
                    "control": CONTROL_LABELS.get(row.get("CONTROL", ""), ""),
                    "locale": LOCALE_LABELS.get(
                        row.get("LOCALE", ""), row.get("LOCALE", "")
                    ),
                    "instSize": INSTSIZE_LABELS.get(row.get("INSTSIZE", ""), ""),
                },
            }
    return institutions


def load_enrollment(year: int) -> dict:
    """Load total enrollment from EFFY (EFFYALEV=1 or EFFYLEV=1, LSTUDY=999).

    Returns dict mapping UNITID -> enrollment fields.
    """
    path = csv_path(year, "effy")
    if not path.exists():
        print(f"  [warn] {path} not found")
        return {}

    enrollment = {}
    has_effyalev = year >= 2020

    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lstudy = row.get("LSTUDY", "").strip()

            if has_effyalev:
                alev = row.get("EFFYALEV", "").strip()
                if alev != "1" or lstudy != "999":
                    continue
            else:
                effylev = row.get("EFFYLEV", "").strip()
                if effylev != "1" or lstudy != "999":
                    continue

            uid = row["UNITID"]
            enrollment[uid] = {
                "totalEnroll": safe_int_keep_special(row.get("EFYTOTLT")),
                "enrollMen": safe_int_keep_special(row.get("EFYTOTLM")),
                "enrollWomen": safe_int_keep_special(row.get("EFYTOTLW")),
                "enrollWhite": safe_int_keep_special(row.get("EFYWHITT")),
                "enrollBlack": safe_int_keep_special(row.get("EFYBKAAT")),
                "enrollHispanic": safe_int_keep_special(row.get("EFYHISPT")),
                "enrollAsian": safe_int_keep_special(row.get("EFYASIAT")),
                "enrollAIAN": safe_int_keep_special(row.get("EFYAIANT")),
                "enrollNHPI": safe_int_keep_special(row.get("EFYNHPIT")),
                "enrollTwoMore": safe_int_keep_special(row.get("EFY2MORT")),
                "enrollUnknown": safe_int_keep_special(row.get("EFYUNKNT")),
                "enrollNonresident": safe_int_keep_special(row.get("EFYNRALT")),
            }
    return enrollment


def load_de_enrollment(year: int) -> dict:
    """Load distance education enrollment from dedicated DE files.

    Pre-2020: EF{year}A_DIST files with variables EFDELEV, EFDEEXC, EFDESOM, EFDENON
    2020+:    EFFY{year}_DIST files with variables EFFYDLEV, EFYDEEXC, EFYDESOM, EFYDENON

    Level code 1 = all students total. We extract:
      - deExclusive: enrolled exclusively in distance education
      - deSome: enrolled in some but not all DE courses
      - deNone: not enrolled in any DE courses
    """
    if year >= 2020:
        path = RAW_DIR / str(year) / f"effy{year}_dist.csv"
        lev_col = "EFFYDLEV"
        exc_col = "EFYDEEXC"
        some_col = "EFYDESOM"
        none_col = "EFYDENON"
    else:
        path = RAW_DIR / str(year) / f"ef{year}a_dist.csv"
        lev_col = "EFDELEV"
        exc_col = "EFDEEXC"
        some_col = "EFDESOM"
        none_col = "EFDENON"

    if not path.exists():
        print(f"  [warn] {path} not found")
        return {}

    de_data = {}
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lev = row.get(lev_col, "").strip()
            if lev != "1":
                continue
            uid = row["UNITID"]
            de_data[uid] = {
                "deExclusive": safe_int_keep_special(row.get(exc_col)),
                "deSome": safe_int_keep_special(row.get(some_col)),
                "deNone": safe_int_keep_special(row.get(none_col)),
            }
    return de_data


def load_graduation(year: int) -> dict:
    """Load graduation rates at 150% of normal time from the GR file.

    Covers all institution types:
      - 4-year: SECTION=1, GRTYPE=2 (cohort) / GRTYPE=3 (completers at 150%)
      - 2-year: SECTION=4, GRTYPE=29 (cohort) / GRTYPE=30 (completers at 150%)
      - <2-year: SECTION=3, GRTYPE=20 (cohort) / GRTYPE=21 (completers at 150%)
    All use LINE=999 (total across races).
    """
    path = csv_path(year, "gr")
    if not path.exists():
        print(f"  [warn] {path} not found")
        return {}

    # Each section has different GRTYPE codes and LINE values for totals:
    #   SECTION=1 (4-year): GRTYPE=2 (cohort, LINE=999), GRTYPE=3 (completers, LINE=999)
    #   SECTION=4 (2-year): GRTYPE=29 (cohort, LINE=50), GRTYPE=30 (completers, LINE=29A)
    #   SECTION=3 (<2-year): GRTYPE=20 (cohort, LINE=50), GRTYPE=21 (completers, LINE=29A)
    # We match on GRTYPE alone (LINE is implied by the GRTYPE).
    SECTIONS = {
        # section -> (cohort_grtype, completers_grtype)
        "1": ("2", "3"),       # 4-year at 150%
        "4": ("29", "30"),     # 2-year at 150%
        "3": ("20", "21"),     # <2-year at 150%
    }

    # Build a set of all relevant GRTYPEs for quick filtering
    relevant_grtypes = set()
    for cgt, compgt in SECTIONS.values():
        relevant_grtypes.add(cgt)
        relevant_grtypes.add(compgt)

    cohorts: dict[str, dict[str, int | None]] = {s: {} for s in SECTIONS}
    completers_map: dict[str, dict[str, int | None]] = {s: {} for s in SECTIONS}

    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            section = row.get("SECTION", "").strip()
            if section not in SECTIONS:
                continue

            gt = row.get("GRTYPE", "").strip()
            if gt not in relevant_grtypes:
                continue

            uid = row["UNITID"]
            total = safe_int_keep_special(row.get("GRTOTLT"))

            cohort_gt, comp_gt = SECTIONS[section]
            if gt == cohort_gt:
                cohorts[section][uid] = total
            elif gt == comp_gt:
                completers_map[section][uid] = total

    # Build graduation dict: prefer 4-year data, then 2-year, then <2-year
    graduation = {}
    for section in ("1", "4", "3"):
        for uid in cohorts[section]:
            if uid in graduation:
                continue  # already have data from a higher-priority section
            c = cohorts[section][uid]
            comp = completers_map[section].get(uid)
            if c and c > 0 and comp is not None:
                graduation[uid] = {
                    "gradCohort": c,
                    "gradCompleters": comp,
                    "gradRate": round(comp / c * 100, 1),
                }

    return graduation


def load_outcome_measures(year: int) -> dict:
    """Load 8-year completion rates from Outcome Measures (OM) as fallback.

    Uses OMCHRT=50 (all entering students) and OMAWDP8 (8-year award rate).
    OM data is available for 2015-2023.
    """
    path = RAW_DIR / str(year) / f"om{year}.csv"
    if not path.exists():
        return {}

    om_data = {}
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chrt = row.get("OMCHRT", "").strip()
            if chrt != "50":
                continue

            uid = row["UNITID"]
            rate = safe_float(row.get("OMAWDP8"))
            cohort = safe_int_keep_special(row.get("OMACHT"))

            if rate is not None and rate >= 0:
                om_data[uid] = {
                    "gradRate": round(rate, 1),
                    "gradCohort": cohort,
                    "gradSource": "OM",
                }
    return om_data


def load_admissions(year: int) -> dict:
    """Load admissions data."""
    path = csv_path(year, "adm")
    if not path.exists():
        print(f"  [warn] {path} not found")
        return {}

    admissions = {}
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["UNITID"]
            apps = safe_int_keep_special(row.get("APPLCN"))
            adm = safe_int_keep_special(row.get("ADMSSN"))
            enrl = safe_int_keep_special(row.get("ENRLT"))

            # SAT variables - same names across 2014-2024
            sat25 = safe_int_keep_special(row.get("SATVR25"))
            sat75 = safe_int_keep_special(row.get("SATVR75"))
            satm25 = safe_int_keep_special(row.get("SATMT25"))
            satm75 = safe_int_keep_special(row.get("SATMT75"))
            act25 = safe_int_keep_special(row.get("ACTCM25"))
            act75 = safe_int_keep_special(row.get("ACTCM75"))

            adm_rate = None
            if apps and apps > 0 and adm is not None:
                adm_rate = round(adm / apps * 100, 1)

            sat_mid = None
            if sat25 and sat75 and satm25 and satm75:
                sat_mid = round((sat25 + sat75 + satm25 + satm75) / 2)

            act_mid = None
            if act25 and act75:
                act_mid = round((act25 + act75) / 2)

            admissions[uid] = {
                "applications": apps,
                "admissions": adm,
                "enrolled": enrl,
                "admRate": adm_rate,
                "satMid": sat_mid,
                "actMid": act_mid,
            }
    return admissions


def load_ic(year: int) -> dict:
    """Load IC data: open admission flag + distance education flags."""
    path = csv_path(year, "ic")
    if not path.exists():
        print(f"  [warn] {path} not found")
        return {}

    ic_data = {}
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["UNITID"]
            record = {}

            # Open admission flag
            if row.get("OPENADMP") == "1":
                record["openAdmission"] = True

            # Distance education flags (available from ~2017+)
            # DISTCRS: offers DE courses, DISTPGS: offers DE programs
            distcrs = row.get("DISTCRS", "").strip()
            distpgs = row.get("DISTPGS", "").strip()
            if distcrs == "1":
                record["deOffersCourses"] = True
            if distpgs == "1":
                record["deOffersPrograms"] = True

            ic_data[uid] = record
    return ic_data


def strip_none(d: dict) -> dict:
    """Remove keys with None values to save space in JSON output."""
    return {k: v for k, v in d.items() if v is not None}


def main() -> None:
    print(f"Processing IPEDS data for {YEARS.start}-{YEARS.stop - 1}")
    print(f"Data directory: {RAW_DIR.resolve()}\n")

    # Master dict: UNITID -> {static fields, yearData: {year: fields}}
    institutions: dict[str, dict] = {}

    for year in YEARS:
        print(f"\n=== {year} ===")

        hd = load_hd(year)
        print(f"  HD: {len(hd)} institutions")

        enroll = load_enrollment(year)
        print(f"  Enrollment: {len(enroll)} institutions")

        de = load_de_enrollment(year)
        print(f"  Distance ed: {len(de)} institutions")

        grad = load_graduation(year)
        print(f"  Graduation (GR): {len(grad)} institutions")

        om = load_outcome_measures(year)
        print(f"  Outcome Measures (OM): {len(om)} institutions")

        adm = load_admissions(year)
        print(f"  Admissions: {len(adm)} institutions")

        ic = load_ic(year)
        print(f"  IC: {len(ic)} institutions")

        # Process each institution in HD for this year
        for uid, hd_data in hd.items():
            if uid not in institutions:
                institutions[uid] = {
                    **hd_data["static"],
                    "yearData": {},
                }
            else:
                # Update static fields with more recent year's data
                # (later years overwrite earlier, so most recent wins)
                for k, v in hd_data["static"].items():
                    if v is not None and v != "":
                        institutions[uid][k] = v

            # Build year-specific data
            yd = dict(hd_data["year"])

            if uid in enroll:
                yd.update(enroll[uid])
            if uid in de:
                yd.update(de[uid])
            if uid in grad:
                yd.update(grad[uid])
            elif uid in om:
                # Use OM data as fallback for institutions not in GR
                yd.update(om[uid])
            if uid in adm:
                yd.update(adm[uid])
            if uid in ic:
                yd.update(ic[uid])

            # Set admRate=100 for open admission institutions without admissions data
            if yd.get("openAdmission") and yd.get("admRate") is None:
                yd["admRate"] = 100.0

            # Only store year data if there's meaningful enrollment
            total = yd.get("totalEnroll")
            if total is not None and total > 0:
                institutions[uid]["yearData"][str(year)] = strip_none(yd)

    # Filter: only keep institutions with at least one year of data
    result = [
        inst for inst in institutions.values() if inst.get("yearData")
    ]

    # Sort by most recent year's enrollment (use latest available year)
    def sort_key(inst: dict) -> int:
        yd = inst.get("yearData", {})
        for y in reversed(list(YEARS)):
            if str(y) in yd:
                return yd[str(y)].get("totalEnroll", 0) or 0
        return 0

    result.sort(key=sort_key, reverse=True)

    # Determine the most recent year with data as default
    all_years = sorted(
        set(
            int(y)
            for inst in result
            for y in inst["yearData"]
        )
    )
    default_year = all_years[-1] if all_years else 2024

    # Collect unique states and sectors across all years
    states = set()
    sectors = set()
    for inst in result:
        if inst.get("state"):
            states.add(inst["state"])
        for yd in inst["yearData"].values():
            if yd.get("sector"):
                sectors.add(yd["sector"])

    print(f"\n{'='*50}")
    print(f"Total institutions: {len(result)}")
    print(f"Years with data: {all_years}")
    print(f"Default year: {default_year}")

    output = {
        "generated": "2014-2024",
        "years": all_years,
        "defaultYear": default_year,
        "count": len(result),
        "states": sorted(states),
        "sectors": sorted(sectors),
        "data": result,
    }

    out_path = Path("data.json")
    with open(out_path, "w") as f:
        json.dump(output, f, separators=(",", ":"))
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\nWritten {out_path} ({size_mb:.1f} MB)")

    # Also write data.js for local file:// usage
    js_path = Path("data.js")
    with open(js_path, "w") as f:
        f.write("var IPEDS_DATA = ")
        json.dump(output, f, separators=(",", ":"))
        f.write(";\n")
    size_mb = js_path.stat().st_size / (1024 * 1024)
    print(f"Written {js_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
