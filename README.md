# IPEDS Explorer

A single-page web application for exploring U.S. higher education data from [IPEDS](https://nces.ed.gov/ipeds/) (Integrated Postsecondary Education Data System), covering 2014-2024. Try it out [here](https://philippschmidt.org/IPEDS/).

Browse, filter, and compare ~4,000 colleges and universities that award Associate or Bachelor degrees. Includes enrollment, graduation rates, admissions, demographics, and distance education data with trend charts for historical comparison.

> **Note:** This is a prototype and may contain incorrect data. If you find problems, please [open an issue](https://github.com/1l2p/IPEDS/issues).

## Quick Start (Local Use)

Download these three files into the same folder:

1. [`index.html`](https://raw.githubusercontent.com/1l2p/IPEDS/main/index.html)
2. [`data.js`](https://raw.githubusercontent.com/1l2p/IPEDS/main/data.js)
3. [`lib/chart.umd.min.js`](https://raw.githubusercontent.com/1l2p/IPEDS/main/lib/chart.umd.min.js) (place in a `lib/` subfolder)

Your folder should look like:

```
ipeds-explorer/
  index.html
  data.js
  lib/
    chart.umd.min.js
```

Open `index.html` in your browser. No server required.

### Alternative: Clone the Repo

```bash
git clone https://github.com/1l2p/IPEDS.git
cd IPEDS
open index.html
```

Or serve it locally:

```bash
python3 -m http.server 8080
# Open http://localhost:8080
```

## Regenerating the Data

The repository includes pre-built data files. If you want to regenerate from source:

```bash
# 1. Download raw IPEDS CSVs (~350 MB)
python3 download_ipeds.py

# 2. Preprocess into data.json and data.js (~23 MB)
python3 preprocess.py
```

Requires Python 3.9+. No external dependencies.

## Data Sources

All data comes from the [IPEDS Data Center](https://nces.ed.gov/ipeds/datacenter/data/) at the National Center for Education Statistics (NCES).

| Component | Description |
|-----------|-------------|
| HD | Institutional directory (name, location, sector) |
| EFFY | 12-month enrollment and demographics |
| GR | Graduation rates at 150% of normal time |
| OM | Outcome Measures (8-year completion, fallback for GR) |
| ADM | Admissions, SAT/ACT scores |
| IC | Institutional characteristics, degree levels, open admission |
| EFFY_DIST / EF_A_DIST | Distance education enrollment |

## License

The underlying IPEDS data is public domain (U.S. government work). The application code in this repository is provided as-is.
