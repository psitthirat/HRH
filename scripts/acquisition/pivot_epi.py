"""Pivot the MOPH epidemiological surveillance tables (data/raw_scraped/s_*.csv)
to year x province level and write the results to data/epi/.

Source tables are scraped one row per (year, province, facility) from the
MOPH open-data API (see scrp_epi.ipynb). Buddhist-era `query_year` is
converted to the Christian era (`year = query_year - 543`) throughout.

Five groups, each aggregated by (year, prov_id, prov):

- NCD screening (dm, ht, copd, coronary, stroke, emphysema, ca_breast,
  ca_lung, ca_cervix): pop_group1-5 and result_group1-5 are summed across
  age groups; prevalence is result / pop, in percent.
- Dental (s_dental_2, s_dental_4): the `result` column (already a per-row
  annual total) is summed to get visits, then divided by a population
  denominator from the NHSO registration extract (data/pop/nhso/pop.csv,
  December snapshot) -- all schemes for s_dental_2, UCS+WEL only for
  s_dental_4 -- to get visits per 1,000 population.
- Pharmacy (s_pharm1, s_pharm2): monthly r1m*/r2m* columns are summed.
  s_pharm1's r1m* series is the OP prescription count; s_pharm2's r2m*
  series is the length-of-stay count. Other r-series and the `visits`/
  `target` columns are not part of this metric.
- Palliative (s_palliative_com): target1 and result1 are summed; the
  other target/result pairs are per-disease breakdowns and are ignored.
  Coverage is result1 / target1, in percent.
- CKD (s_ckd_stage_typearea, s_ckd_stage_hosp): stage1-5 are summed and
  each divided by the total NHSO registration population, in percent.
"""

import re
from pathlib import Path

import pandas as pd

SCRAPED_DIR = Path("data/raw_scraped")
OUT_DIR = Path("data/epi")
NHSO_POP_PATH = Path("data/pop/nhso/pop.csv")

BE_OFFSET = 543

# See scripts/ch4x.py `_SCHEME_GROUP` for the fuller scheme taxonomy; here we
# only need the literal UC + welfare codes the task asks for.
UC_WEL_CODES = {"UCS", "WEL"}


def load_nhso_population() -> pd.DataFrame:
    """December-snapshot registration population by (year, prov_id).

    Returns columns ['year', 'prov_id', 'total_pop', 'uc_wel_pop'].
    """
    raw = pd.read_csv(
        NHSO_POP_PATH,
        usecols=["month_no", "right_code", "province_code", "m_population"],
        low_memory=False,
    )
    raw["year"] = pd.to_numeric(raw["month_no"], errors="coerce") // 100
    raw["prov_id"] = pd.to_numeric(raw["province_code"], errors="coerce") // 100
    raw = raw.dropna(subset=["year", "prov_id"])
    raw["year"] = raw["year"].astype(int)
    raw["prov_id"] = raw["prov_id"].astype(int)

    total = raw.groupby(["year", "prov_id"])["m_population"].sum().rename("total_pop")
    uc_wel = (
        raw[raw["right_code"].isin(UC_WEL_CODES)]
        .groupby(["year", "prov_id"])["m_population"]
        .sum()
        .rename("uc_wel_pop")
    )
    return pd.concat([total, uc_wel], axis=1).fillna(0.0).reset_index()


def load_scraped(table_name: str) -> pd.DataFrame:
    df = pd.read_csv(SCRAPED_DIR / f"{table_name}.csv", low_memory=False)
    df["year"] = df["query_year"].astype(int) - BE_OFFSET
    df = df.rename(columns={"query_province_code": "prov_id", "query_province_name": "prov"})
    df["prov_id"] = df["prov_id"].astype(int)
    return df


def province_names(df: pd.DataFrame) -> pd.DataFrame:
    return df[["prov_id", "prov"]].drop_duplicates()


NCD_TABLES = [
    "s_dm_pop_age",
    "s_ht_pop_age",
    "s_copd_pop_age",
    "s_coronary_pop_age",
    "s_stroke_pop_age",
    "s_emphysema_pop_age",
    "s_ca_breast_pop_age",
    "s_ca_lung_pop_age",
    "s_ca_cervix_pop_age",
]


def pivot_ncd(table_name: str) -> pd.DataFrame:
    df = load_scraped(table_name)
    pop_cols = [f"pop_group{i}" for i in range(1, 6)]
    result_cols = [f"result_group{i}" for i in range(1, 6)]
    df["pop"] = df[pop_cols].sum(axis=1)
    df["result"] = df[result_cols].sum(axis=1)

    out = df.groupby(["year", "prov_id"], as_index=False)[["pop", "result"]].sum()
    out = out.merge(province_names(df), on="prov_id", how="left")
    out["prevalence_pct"] = out["result"] / out["pop"] * 100
    return out[["year", "prov_id", "prov", "pop", "result", "prevalence_pct"]].sort_values(
        ["year", "prov_id"]
    )


def pivot_dental(table_name: str, pop: pd.DataFrame, pop_col: str) -> pd.DataFrame:
    df = load_scraped(table_name)
    out = df.groupby(["year", "prov_id"], as_index=False)["result"].sum()
    out = out.rename(columns={"result": "visits"})
    out = out.merge(province_names(df), on="prov_id", how="left")
    out = out.merge(pop[["year", "prov_id", pop_col]], on=["year", "prov_id"], how="left")
    out = out.rename(columns={pop_col: "pop"})
    out["visits_per_1000"] = out["visits"] / out["pop"] * 1000
    return out[["year", "prov_id", "prov", "visits", "pop", "visits_per_1000"]].sort_values(
        ["year", "prov_id"]
    )


def pivot_pharm(table_name: str, series_prefix: str, value_name: str) -> pd.DataFrame:
    df = load_scraped(table_name)
    series_cols = [c for c in df.columns if re.fullmatch(rf"{series_prefix}m\d+", c)]
    df[value_name] = df[series_cols].sum(axis=1)

    out = df.groupby(["year", "prov_id"], as_index=False)[value_name].sum()
    out = out.merge(province_names(df), on="prov_id", how="left")
    return out[["year", "prov_id", "prov", value_name]].sort_values(["year", "prov_id"])


def pivot_palliative() -> pd.DataFrame:
    df = load_scraped("s_palliative_com")
    out = df.groupby(["year", "prov_id"], as_index=False)[["target1", "result1"]].sum()
    out = out.merge(province_names(df), on="prov_id", how="left")
    out["coverage_pct"] = out["result1"] / out["target1"] * 100
    return out[["year", "prov_id", "prov", "target1", "result1", "coverage_pct"]].sort_values(
        ["year", "prov_id"]
    )


def pivot_ckd(table_name: str, pop: pd.DataFrame) -> pd.DataFrame:
    df = load_scraped(table_name)
    stage_cols = [f"stage{i}" for i in range(1, 6)]
    out = df.groupby(["year", "prov_id"], as_index=False)[stage_cols].sum()
    out = out.merge(province_names(df), on="prov_id", how="left")
    out = out.merge(pop[["year", "prov_id", "total_pop"]], on=["year", "prov_id"], how="left")
    out = out.rename(columns={"total_pop": "pop"})
    out["stage_all"] = out[stage_cols].sum(axis=1)
    for c in stage_cols + ["stage_all"]:
        out[f"{c}_prevalence_pct"] = out[c] / out["pop"] * 100
    cols = ["year", "prov_id", "prov", "pop", *stage_cols, "stage_all"]
    cols += [f"{c}_prevalence_pct" for c in stage_cols + ["stage_all"]]
    return out[cols].sort_values(["year", "prov_id"])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pop = load_nhso_population()

    for table_name in NCD_TABLES:
        pivot_ncd(table_name).to_csv(OUT_DIR / f"{table_name}.csv", index=False)
        print(f"wrote {table_name}")

    pivot_dental("s_dental_2", pop, "total_pop").to_csv(OUT_DIR / "s_dental_2.csv", index=False)
    pivot_dental("s_dental_4", pop, "uc_wel_pop").to_csv(OUT_DIR / "s_dental_4.csv", index=False)
    print("wrote s_dental_2, s_dental_4")

    pivot_pharm("s_pharm1", "r1", "op_prescriptions").to_csv(
        OUT_DIR / "s_pharm1.csv", index=False
    )
    pivot_pharm("s_pharm2", "r2", "length_of_stay").to_csv(
        OUT_DIR / "s_pharm2.csv", index=False
    )
    print("wrote s_pharm1, s_pharm2")

    pivot_palliative().to_csv(OUT_DIR / "s_palliative_com.csv", index=False)
    print("wrote s_palliative_com")

    pivot_ckd("s_ckd_stage_typearea", pop).to_csv(
        OUT_DIR / "s_ckd_stage_typearea.csv", index=False
    )
    pivot_ckd("s_ckd_stage_hosp", pop).to_csv(OUT_DIR / "s_ckd_stage_hosp.csv", index=False)
    print("wrote s_ckd_stage_typearea, s_ckd_stage_hosp")


if __name__ == "__main__":
    main()
