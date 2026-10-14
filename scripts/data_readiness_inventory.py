"""Readiness inventory of the data candidates for the next service modules (plan backlog item 3).

Facts (columns, years, provinces, strata, totals, coverage breaks) are measured from the files;
the readiness class and the module each file could serve are curated judgements recorded in
CANDIDATES below.  Classes:
    usable        measured, fit for the stated use with the noted limits
    unvalidated   present, but definition, coverage or strata are not yet checked enough to use
    missing       the variable the module needs is not in the repository

    .venv/bin/python scripts/data_readiness_inventory.py
writes outputs/shared/data_readiness_inventory.csv and outputs/shared/data_readiness_breaks.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "outputs" / "shared"

# path, value columns used for totals, readiness class, candidate modules, curated note
CANDIDATES = [
    ("data/processed/services_province.csv[tier=pc]", ["op_visits", "op_persons"], "unvalidated",
     "ageing/community care",
     "Health-promoting hospital (รพ.สต.) outpatient persons/visits only; no home visits, LTC, rehabilitation or "
     "palliative episodes; reporting falls after the 2023 transfer to provincial administrative organisations."),
    ("data/epi/s_palliative_com.csv", ["target1", "result1"], "unvalidated", "ageing/community care",
     "Coverage indicator (result/target) of community palliative care; targets are small counts; no episodes, "
     "visits, staff time or age."),
    ("data/epi/s_ckd_stage_typearea.csv", ["stage3", "stage4", "stage5"], "usable", "ESRD (screening only)",
     "Diagnosed CKD by stage among registered residents; used for Chapter 4 CKD 3–5 prevalence. Stage 5 is not "
     "treated kidney failure: no dialysis modality, incidence, transplant or deaths."),
    ("data/epi/s_ckd_stage_hosp.csv", ["stage3", "stage4", "stage5"], "unvalidated", "ESRD (screening only)",
     "Same indicator by hospital denominator (includes Bangkok); overlaps the type-area series."),
    ("data/epi/s_ca_breast_pop_age.csv", ["result"], "unvalidated", "cancer pathway",
     "Diagnosed-prevalence count with a population denominator; despite the file name there are no age strata; "
     "no incidence, stage or treatment."),
    ("data/epi/s_ca_cervix_pop_age.csv", ["result"], "unvalidated", "cancer pathway",
     "As breast: prevalence count only, no age strata, no incidence/stage/treatment."),
    ("data/epi/s_ca_lung_pop_age.csv", ["result"], "unvalidated", "cancer pathway",
     "As breast: prevalence count only, no age strata, no incidence/stage/treatment."),
    ("data/epi/BOD_2022_Province_Disease_Age.csv", ["DALY", "YLD_NEW", "deaths"], "usable",
     "all modules (burden context)",
     "Modeled 2022 burden by 8 age groups and 174 causes; reproduces the ASR file; not service volumes and "
     "not convertible to visits or FTE without a care-package bridge."),
    ("data/spc_aggregated.csv", ["total"], "unvalidated", "ESRD / cancer / spatial",
     "Facility-level physicians by 18 specialties 2015–2024 (GIS Health returns, the source rejected as an "
     "OPS stock for coverage breaks); no nephrology, medical/radiation oncology or geriatrics categories."),
    ("data/hrh_aggregated.csv", ["total"], "unvalidated", "task/FTE layer, spatial",
     "Facility-level headcount by 19 cadres 2015–2024 incl. physiotherapists, psychologists, Thai traditional "
     "medicine; headcount only, no FTE or working time; coverage breaks documented in Chapter 4."),
]

MISSING = [
    ("Dependency / functional status (ADL, frailty) by age and province", "ageing/community care"),
    ("Home-care, LTC care-manager and caregiver records (visits, packages, time)", "ageing/community care"),
    ("Activity–time standards by task and cadre (time-motion or WISN study)", "task/FTE layer"),
    ("Treated kidney failure: incident and prevalent dialysis by modality, transplant, deaths (registry/NHSO)", "ESRD"),
    ("Dialysis chairs/machines, operating hours, nephrology and HD-nursing staff", "ESRD"),
    ("Cancer registry incidence by site, age, stage and residence; treatment pathway activity", "cancer pathway"),
    ("Radiotherapy/oncology equipment and staff by centre", "cancer pathway"),
    ("Workforce origin–destination moves and patient referral flows; facility opening dates", "spatial / anchoring"),
]


def _read(spec: str) -> pd.DataFrame:
    path, _, filt = spec.partition("[")
    d = pd.read_csv(ROOT / path, low_memory=False)
    d.columns = [c.replace("﻿", "") for c in d.columns]
    if filt:
        k, v = filt.rstrip("]").split("=")
        d = d[d[k] == v]
        d = d.pivot_table(index=["year", "prov_code"], columns="metric", values="value").reset_index()
    return d


def measure(spec: str, cols: list[str]) -> tuple[dict, list[dict]]:
    d = _read(spec)
    prov = next((c for c in ["prov_code", "prov_id", "area_name", "hosp_id"] if c in d.columns), None)
    year = "year_ce" if "year_ce" in d.columns else ("year" if "year" in d.columns else None)
    strata = [c for c in d.columns if any(k in c.lower() for k in ["age", "sex", "stage", "spc", "hrh", "codv"])]
    fact = dict(source=spec, rows=len(d), columns=", ".join(map(str, d.columns))[:400],
                years=f"{d[year].min()}–{d[year].max()}" if year else "",
                units_entities=d[prov].nunique() if prov else np.nan, unit_type=prov or "",
                strata_columns=", ".join(strata), value_columns=", ".join(cols))
    breaks = []
    if year and prov and prov != "hosp_id":
        g = d.groupby(year)
        cover = g[prov].nunique()
        tot = g[cols[0]].sum(min_count=1)
        fact["province_coverage_by_year"] = ", ".join(f"{y}:{n}" for y, n in cover.items())
        for y in tot.index[1:]:
            prev = tot.index[tot.index.get_loc(y) - 1]
            ch = tot[y] / tot[prev] - 1 if tot[prev] else np.nan
            if np.isfinite(ch) and abs(ch) > 0.4:
                breaks.append(dict(source=spec, year=y, kind="national total change > 40%", value=round(100 * ch, 1),
                                   detail=f"{cols[0]} {tot[prev]:,.0f} -> {tot[y]:,.0f}"))
            if cover[y] < cover[prev]:
                breaks.append(dict(source=spec, year=y, kind="fewer reporting units", value=int(cover[y] - cover[prev]),
                                   detail=f"{cover[prev]} -> {cover[y]}"))
    elif year and prov == "hosp_id":
        cover = d[d[cols[0]] > 0].groupby(year)[prov].nunique()
        fact["province_coverage_by_year"] = "facilities with a positive count: " + ", ".join(f"{y}:{n}" for y, n in cover.items())
        for y in cover.index[1:]:
            prev = cover.index[cover.index.get_loc(y) - 1]
            ch = cover[y] / cover[prev] - 1
            if abs(ch) > 0.25:
                breaks.append(dict(source=spec, year=y, kind="reporting facilities change > 25%", value=round(100 * ch, 1),
                                   detail=f"{cover[prev]} -> {cover[y]}"))
    return fact, breaks


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, brk = [], []
    for spec, cols, cls, module, note in CANDIDATES:
        fact, b = measure(spec, cols)
        rows.append(dict(**fact, readiness=cls, candidate_module=module, note=note))
        brk += b
    for var, module in MISSING:
        rows.append(dict(source=var, readiness="missing", candidate_module=module,
                         note="not in the repository; request only if tied to a module decision or validation question"))
    inv = pd.DataFrame(rows)
    inv.to_csv(OUT / "data_readiness_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(brk).to_csv(OUT / "data_readiness_breaks.csv", index=False, encoding="utf-8-sig")
    print(inv[["source", "rows", "years", "units_entities", "readiness"]].to_string())
    print(pd.DataFrame(brk).to_string())


if __name__ == "__main__":
    main()
