"""
Compiles output/analyse/hrh/*.csv into a single compact JSON file the
static web/ dashboard reads client-side. Also copies the level boundary
files into web/data/. Re-run whenever the underlying analysis tables change.

Usage:
    python scripts/build_dashboard_data.py
"""

import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ANALYSE_DIR = ROOT / "output/analyse/hrh"
MAP_DIR = ROOT / "output/map"
WEB_DATA_DIR = ROOT / "web/data"

HRH_TYPES = ["doctor", "nurse-prof", "dentist", "pharmacist", "pt", "rt", "ph-practictioner", "psychologist-clinic"]
HRH_LABELS = {
    "doctor": "Doctor",
    "nurse-prof": "Nurse",
    "dentist": "Dentist",
    "pharmacist": "Pharmacist",
    "pt": "Physiotherapist",
    "rt": "Radiologic Tech.",
    "ph-practictioner": "PH Practitioner",
    "psychologist-clinic": "Clinical Psychologist",
}


def hregion_label(hregion_th: str) -> str:
    # "เขตสุขภาพที่ 1" -> "Region 1"
    num = hregion_th.split()[-1]
    return f"Region {num}"


def load_prov_en_map():
    with open(MAP_DIR / "geo_prov.geojson", encoding="utf-8") as f:
        geo = json.load(f)
    return {feat["properties"]["prov"]: feat["properties"]["prov_en"] for feat in geo["features"]}


LEVELS = [
    {
        "key": "hregion",
        "label": "Health Region",
        "table": "Table 2 Density in health region level.csv",
        "id_col": "hregion",
        "gini_col": "G_hregion",
        "geojson": "geo_hregion.geojson",
        "sort_key": lambda r: int(r.split()[-1]),
        "region_label": hregion_label,
    },
    {
        "key": "prov",
        "label": "Province",
        "table": "Table 3 Density in provincial level.csv",
        "id_col": "prov",
        "gini_col": "G_prov",
        "geojson": "geo_prov.geojson",
        "sort_key": lambda r: r,
        "region_label": None,  # filled in below via load_prov_en_map()
    },
]


def build_level(level, ineq):
    df = pd.read_csv(ANALYSE_DIR / level["table"])
    df = df[df["hrh"].isin(HRH_TYPES)]
    id_col = level["id_col"]

    years = sorted(df["year"].unique().tolist())
    year_min, year_max = years[0], years[-1]
    region_ids = sorted(df[id_col].unique().tolist(), key=level["sort_key"])
    label_fn = level["region_label"]

    density, change, gini = {}, {}, {}

    for hrh in HRH_TYPES:
        sub = df[df["hrh"] == hrh]

        density[hrh] = {}
        for year in years:
            year_sub = sub[sub["year"] == year]
            density[hrh][str(year)] = dict(zip(year_sub[id_col], year_sub["den"].round(3)))

        first = sub[sub["year"] == year_min].set_index(id_col)["den"]
        last = sub[sub["year"] == year_max].set_index(id_col)["den"]
        change[hrh] = {}
        for region in region_ids:
            v_from = float(first.get(region, 0.0))
            v_to = float(last.get(region, 0.0))
            abs_change = v_to - v_from
            pct_change = (abs_change / v_from * 100) if v_from > 0 else None
            change[hrh][region] = {
                "from": round(v_from, 3),
                "to": round(v_to, 3),
                "abs": round(abs_change, 3),
                "pct": round(pct_change, 1) if pct_change is not None else None,
            }

        ineq_sub = ineq[ineq["hrh"] == hrh].set_index("year")[level["gini_col"]]
        gini[hrh] = {str(y): round(float(ineq_sub.get(y)), 4) for y in years if y in ineq_sub.index}

    return {
        "label": level["label"],
        "key": id_col,
        "regions": [{"id": r, "label": label_fn(r)} for r in region_ids],
        "density": density,
        "change": change,
        "gini": gini,
    }, years


def main():
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    prov_en = load_prov_en_map()
    for level in LEVELS:
        if level["key"] == "prov":
            level["region_label"] = lambda r: prov_en.get(r, r)

    total = pd.read_csv(ANALYSE_DIR / "Table 1A Total Numbers of Physician and Specilist.csv")
    ineq = pd.read_csv(ANALYSE_DIR / "Table 6 Inequity distribution of HRH.csv")
    total = total[total["hrh"].isin(HRH_TYPES)]
    ineq = ineq[ineq["hrh"].isin(HRH_TYPES)]

    levels_out = {}
    all_years = None
    for level in LEVELS:
        levels_out[level["key"]], years = build_level(level, ineq)
        all_years = years  # identical across levels (same source years)

    ratio = {}
    for hrh in HRH_TYPES:
        total_sub = total[total["hrh"] == hrh].set_index("year")["ratio"]
        ratio[hrh] = {str(y): round(float(total_sub.get(y)), 2) for y in all_years if y in total_sub.index}

    data = {
        "years": all_years,
        "hrh_types": [{"code": h, "label": HRH_LABELS[h]} for h in HRH_TYPES],
        "ratio": ratio,
        "levels": levels_out,
    }

    out_path = WEB_DATA_DIR / "dashboard_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")

    for level in LEVELS:
        src = MAP_DIR / level["geojson"]
        dst = WEB_DATA_DIR / level["geojson"]
        shutil.copy(src, dst)
        print(f"Copied {level['geojson']} ({dst.stat().st_size / 1024:.1f} KB)")

    print(f"Years: {all_years}")
    for level in LEVELS:
        n = len(levels_out[level["key"]]["regions"])
        print(f"{level['label']}: {n} regions")


if __name__ == "__main__":
    main()
