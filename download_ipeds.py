#!/usr/bin/env python3
"""Download IPEDS complete data files (CSV) for years 2014-2024.

Downloads zip files from NCES, extracts the main CSV for each component/year
into data/raw/{year}/{component}{year}.csv.

Components downloaded:
  HD   - Institutional Directory
  EFFY - 12-Month Enrollment
  GR   - Graduation Rates
  ADM  - Admissions
  IC   - Institutional Characteristics
  EFxD - Fall Enrollment by Distance Education Status
"""

import io
import sys
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

BASE_URL = "https://nces.ed.gov/ipeds/datacenter/data"
YEARS = range(2014, 2025)
RAW_DIR = Path("data/raw")

# Components and their zip file name patterns.
# Most follow {COMPONENT}{YEAR}.zip; the distance education fall enrollment
# file uses ef{YEAR}d.zip.
COMPONENTS = [
    ("HD", lambda y: f"HD{y}"),
    ("EFFY", lambda y: f"EFFY{y}"),
    ("GR", lambda y: f"GR{y}"),
    ("ADM", lambda y: f"ADM{y}"),
    ("IC", lambda y: f"IC{y}"),
    ("EFD", lambda y: f"EF{y}D"),
]


def download_and_extract(component_label: str, zip_name: str, year: int) -> bool:
    """Download a single IPEDS zip file and extract its main CSV.

    Returns True on success, False on failure.
    """
    dest_dir = RAW_DIR / str(year)
    # The CSV inside the zip is typically lowercase
    expected_csv = f"{zip_name.lower()}.csv"
    dest_file = dest_dir / expected_csv

    if dest_file.exists():
        print(f"  [skip] {dest_file} already exists")
        return True

    url = f"{BASE_URL}/{zip_name}.zip"
    print(f"  Downloading {url} ...")

    try:
        resp = urlopen(url, timeout=60)
        data = resp.read()
    except HTTPError as e:
        print(f"  [FAIL] HTTP {e.code} for {url}")
        return False
    except Exception as e:
        print(f"  [FAIL] {e} for {url}")
        return False

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        print(f"  [FAIL] Bad zip file from {url}")
        return False

    # Find the main CSV (not the _rv revision file, not the _Dict file)
    csv_names = [
        n for n in zf.namelist()
        if n.lower().endswith(".csv") and "_rv" not in n.lower() and "_dict" not in n.lower()
    ]

    if not csv_names:
        print(f"  [FAIL] No CSV found in {url}. Contents: {zf.namelist()}")
        return False

    # Pick the first matching CSV
    csv_name = csv_names[0]
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Extract with the expected name
    with zf.open(csv_name) as src, open(dest_file, "wb") as dst:
        dst.write(src.read())

    size_kb = dest_file.stat().st_size / 1024
    print(f"  [OK] {dest_file} ({size_kb:.0f} KB)")
    return True


def main() -> None:
    print(f"Downloading IPEDS data for {YEARS.start}-{YEARS.stop - 1}")
    print(f"Output directory: {RAW_DIR.resolve()}\n")

    results: dict[str, list[int]] = {"success": [], "fail": []}

    for year in YEARS:
        print(f"\n=== {year} ===")
        for label, name_fn in COMPONENTS:
            zip_name = name_fn(year)
            ok = download_and_extract(label, zip_name, year)
            if not ok:
                results["fail"].append((year, label, zip_name))
            else:
                results["success"].append((year, label))

    print(f"\n{'='*50}")
    print(f"Done. {len(results['success'])} files OK, {len(results['fail'])} failed.")
    if results["fail"]:
        print("\nFailed downloads:")
        for year, label, name in results["fail"]:
            print(f"  {year} {label} ({name}.zip)")
        sys.exit(1)


if __name__ == "__main__":
    main()
