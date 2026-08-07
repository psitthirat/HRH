"""
Extends Table 5 (coverage) and Table 6 (inequity) with an additional HRH
cadre that already exists in Tables 2-4 (density) but was excluded from the
curated `hrh_types` list used in hrh.ipynb section 4. Uses the same
scripts.analyse.coverage/gini/theil_T functions as the notebook so results
are computed identically -- this avoids re-running the full notebook (in
particular the slow outlier-detection loop in section 3.2, which Tables 2-4
already reflect) just to add one more cadre to the summary tables.

Usage:
    python scripts/add_hrh_cadre.py psychologist-clinic
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import analyse

ANALYSE_DIR = ROOT / "output/analyse/hrh"


def main(hrh):
    df_hregion = pd.read_csv(ANALYSE_DIR / "Table 2 Density in health region level.csv")
    df_prov = pd.read_csv(ANALYSE_DIR / "Table 3 Density in provincial level.csv")
    df_dist = pd.read_csv(ANALYSE_DIR / "Table 4 Density in district level.csv")

    for name, df in [("Table 2", df_hregion), ("Table 3", df_prov), ("Table 4", df_dist)]:
        if hrh not in df["hrh"].unique():
            raise SystemExit(f"'{hrh}' not found in {name} -- nothing to add")

    years = range(2015, 2025)
    cov_rows, ineq_rows = [], []
    for year in years:
        cov_rows.append({
            "year": year,
            "hrh": hrh,
            "n_hrh": df_hregion.query("year==@year & hrh==@hrh")["total"].sum(),
            "cov_hregion": analyse.coverage(df_hregion.query("year==@year & hrh==@hrh"), "total", "hregion"),
            "cov_prov": analyse.coverage(df_prov.query("year==@year & hrh==@hrh"), "total", "prov"),
            "cov_dist": analyse.coverage(df_dist.query("year==@year & hrh==@hrh"), "total", "dist"),
        })
        ineq_rows.append({
            "year": year,
            "hrh": hrh,
            "G_hregion": analyse.gini(df_hregion.query("year==@year & hrh==@hrh"), "total", "pop"),
            "G_prov": analyse.gini(df_prov.query("year==@year & hrh==@hrh"), "total", "pop"),
            "G_dist": analyse.gini(df_dist.query("year==@year & hrh==@hrh"), "total", "pop"),
            "T_hregion": analyse.theil_T(df_hregion.query("year==@year & hrh==@hrh"), "total", "pop"),
            "T_prov": analyse.theil_T(df_prov.query("year==@year & hrh==@hrh"), "total", "pop"),
            "T_dist": analyse.theil_T(df_dist.query("year==@year & hrh==@hrh"), "total", "pop"),
        })

    for fname, new_rows in [
        ("Table 5 Coverage of HRH.csv", cov_rows),
        ("Table 6 Inequity distribution of HRH.csv", ineq_rows),
    ]:
        path = ANALYSE_DIR / fname
        existing = pd.read_csv(path, index_col=0)
        existing = existing[existing["hrh"] != hrh]  # replace if already present
        updated = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
        updated = updated.sort_values(["year", "hrh"]).reset_index(drop=True)
        updated.to_csv(path)
        print(f"Updated {path} ({len(updated)} rows, {updated['hrh'].nunique()} cadres)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/add_hrh_cadre.py <hrh-code>")
    main(sys.argv[1])
