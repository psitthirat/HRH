# Data acquisition (re-run only when refreshing source data)

These scripts produced the raw files under `data/`. The analysis pipeline (`src/chapter4`, `src/chapter5`) never calls them. It reads the files registered in `config/source_registry.toml`.

| Script | Source | Writes |
|---|---|---|
| `scrp_hrh.py` | GIS Health Map: facility workforce returns | `data/raw_scraped/hrh.csv` (then cleaned into `data/hrh_aggregated.csv`) |
| `scrp_spc.py` | GIS Health Map: physicians by specialty per facility | `data/raw_scraped/spc.csv` (then `data/spc_aggregated.csv`) |
| `scrp_serv.py` | facility service pages (Playwright) | `data/raw_scraped/serv.csv` |
| `scrp_epi.ipynb` | MOPH open-data API (`opendata.moph.go.th`): HDC surveillance tables | `data/raw_scraped/s_*.csv` |
| `pivot_epi.py` | the HDC tables above | year × province tables in `data/epi/` |
| `process.py` | — | cleaning, data dictionaries and crosswalk helpers (writes crosswalks to `data/map/`) |

## Running

- Run from the repository root, e.g. `.venv/bin/python scripts/acquisition/pivot_epi.py`. Dependencies are listed in `requirements.txt`.
- **Raw scrapes are not in the repository.** The copy taken up to September 2026 (about 1.9 GB) is kept off-repo in `../HRH_offrepo/raw_scraped/` (see `MANIFEST.csv` there). A new run writes to `data/raw_scraped/`, which is git-ignored.
- **After refreshing a file in `data/`:**
  1. register any new file in `config/source_registry.toml`;
  2. rebuild with `make chapter4` and `make chapter5` (the source hash changes, so caches rebuild);
  3. record the refresh in `PROJECT_LOG.md`.
