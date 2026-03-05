#!/usr/bin/env python3
"""Preprocess IPEDS 2024 CSV files into a single JSON for the web explorer."""

import csv
import json
import sys

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


def safe_int(val):
    """Convert to int, returning None for missing/invalid values."""
    if val is None or val == "" or val == ".":
        return None
    try:
        return int(val)
    except ValueError:
        return None


def safe_float(val):
    if val is None or val == "" or val == ".":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def load_hd(path="hd2024.csv"):
    """Load institutional directory data."""
    institutions = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["UNITID"]
            institutions[uid] = {
                "id": uid,
                "name": row["INSTNM"],
                "city": row["CITY"],
                "state": row["STABBR"],
                "sector": SECTOR_LABELS.get(row.get("SECTOR", ""), ""),
                "sectorCode": row.get("SECTOR", ""),
                "control": CONTROL_LABELS.get(row.get("CONTROL", ""), ""),
                "locale": LOCALE_LABELS.get(row.get("LOCALE", ""), row.get("LOCALE", "")),
                "hbcu": row.get("HBCU", "") == "1",
                "instSize": INSTSIZE_LABELS.get(row.get("INSTSIZE", ""), ""),
                "lat": safe_float(row.get("LATITUDE")),
                "lng": safe_float(row.get("LONGITUD")),
                "webAddr": row.get("WEBADDR", ""),
            }
    return institutions


def load_enrollment(path="effy2024.csv"):
    """Load total enrollment (EFFYALEV=1 = all students, all levels)."""
    enrollment = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["EFFYALEV"] != "1":
                continue
            uid = row["UNITID"]
            enrollment[uid] = {
                "totalEnroll": safe_int(row.get("EFYTOTLT")),
                "enrollMen": safe_int(row.get("EFYTOTLM")),
                "enrollWomen": safe_int(row.get("EFYTOTLW")),
                "enrollWhite": safe_int(row.get("EFYWHITT")),
                "enrollBlack": safe_int(row.get("EFYBKAAT")),
                "enrollHispanic": safe_int(row.get("EFYHISPT")),
                "enrollAsian": safe_int(row.get("EFYASIAT")),
                "enrollAIAN": safe_int(row.get("EFYAIANT")),
                "enrollNHPI": safe_int(row.get("EFYNHPIT")),
                "enrollTwoMore": safe_int(row.get("EFY2MORT")),
                "enrollUnknown": safe_int(row.get("EFYUNKNT")),
                "enrollNonresident": safe_int(row.get("EFYNRALT")),
            }
    return enrollment


def load_graduation(path="gr2024.csv"):
    """Load graduation rates. Rate = completers 150% / adjusted cohort."""
    # Collect SECTION=1, LINE=999 rows for GRTYPE 2 and 3
    cohorts = {}  # GRTYPE=2: adjusted cohort
    completers = {}  # GRTYPE=3: completers within 150%

    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["SECTION"] != "1" or row["LINE"] != "999":
                continue
            uid = row["UNITID"]
            gt = row["GRTYPE"]
            total = safe_int(row.get("GRTOTLT"))
            if gt == "2":
                cohorts[uid] = total
            elif gt == "3":
                completers[uid] = total

    graduation = {}
    for uid in cohorts:
        c = cohorts[uid]
        comp = completers.get(uid)
        if c and c > 0 and comp is not None:
            graduation[uid] = {
                "gradCohort": c,
                "gradCompleters": comp,
                "gradRate": round(comp / c * 100, 1),
            }
    return graduation


def load_admissions(path="adm2024.csv"):
    """Load admissions data."""
    admissions = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["UNITID"]
            apps = safe_int(row.get("APPLCN"))
            adm = safe_int(row.get("ADMSSN"))
            enrl = safe_int(row.get("ENRLT"))
            sat25 = safe_int(row.get("SATVR25"))
            sat75 = safe_int(row.get("SATVR75"))
            satm25 = safe_int(row.get("SATMT25"))
            satm75 = safe_int(row.get("SATMT75"))
            act25 = safe_int(row.get("ACTCM25"))
            act75 = safe_int(row.get("ACTCM75"))

            adm_rate = None
            if apps and apps > 0 and adm is not None:
                adm_rate = round(adm / apps * 100, 1)

            # Compute SAT composite midpoint (average of 25th and 75th for R+M)
            sat_mid = None
            if sat25 and sat75 and satm25 and satm75:
                sat_mid = round((sat25 + sat75 + satm25 + satm75) / 2)

            admissions[uid] = {
                "applications": apps,
                "admissions": adm,
                "enrolled": enrl,
                "admRate": adm_rate,
                "satMid": sat_mid,
                "actMid": round((act25 + act75) / 2) if act25 and act75 else None,
            }
    return admissions


def main():
    print("Loading institutional directory...")
    institutions = load_hd()
    print(f"  {len(institutions)} institutions")

    print("Loading enrollment...")
    enrollment = load_enrollment()
    print(f"  {len(enrollment)} institutions with enrollment data")

    print("Loading graduation rates...")
    graduation = load_graduation()
    print(f"  {len(graduation)} institutions with graduation data")

    print("Loading admissions...")
    admissions = load_admissions()
    print(f"  {len(admissions)} institutions with admissions data")

    # Merge all data
    print("Merging data...")
    result = []
    for uid, inst in institutions.items():
        record = {**inst}
        if uid in enrollment:
            record.update(enrollment[uid])
        if uid in graduation:
            record.update(graduation[uid])
        if uid in admissions:
            record.update(admissions[uid])
        # Only include institutions with some enrollment data
        if record.get("totalEnroll") and record["totalEnroll"] > 0:
            result.append(record)

    # Sort by total enrollment descending
    result.sort(key=lambda x: x.get("totalEnroll", 0) or 0, reverse=True)
    print(f"  {len(result)} institutions with enrollment > 0")

    # Collect unique states for filter
    states = sorted(set(r["state"] for r in result if r.get("state")))
    sectors = sorted(set(r["sector"] for r in result if r.get("sector")))

    output = {
        "generated": "2024",
        "count": len(result),
        "states": states,
        "sectors": sectors,
        "data": result,
    }

    out_path = "data.json"
    with open(out_path, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    import os
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"Written {out_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
