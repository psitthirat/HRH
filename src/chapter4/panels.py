"""Shared analytical panels built from the canonical tables.

National series keep Bangkok (4.1, 4.2.1).  The provincial analytical panel drops Bangkok
from the outset (4.2.3, 4.3, 4.4).  Every join validates its cardinality; audit tables
record coverage, missingness, duplicates, joins and the sample flow.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from . import config as C
from .ingest import load

from .model_design import AGE_BANDS, BURDEN, BURDEN_GROUPS, DISEASE
MOPH_TIERS = C.CFG["services"]["moph_service_tiers"]


@lru_cache(maxsize=None)
def key() -> pd.DataFrame:
    return load("province_key")


def names() -> dict:
    return dict(zip(key().prov_code, key().province))


def _merge(left, right, on, how="left", validate="one_to_one", audit=None, label=""):
    """Merge with cardinality validation and an optional audit row."""
    out = left.merge(right, on=on, how=how, validate=validate, indicator=True)
    if audit is not None:
        audit.append(dict(join=label, left_rows=len(left), right_rows=len(right), result_rows=len(out),
                          matched=int((out._merge == "both").sum()),
                          left_only=int((out._merge == "left_only").sum()),
                          right_only=int((out._merge == "right_only").sum()), validate=validate))
    return out.drop(columns="_merge")


# ----------------------------------------------------------------------------- workforce

@lru_cache(maxsize=None)
def workforce_long(raw: bool = False) -> pd.DataFrame:
    """Workforce by province x year x cadre x sector.

    raw=True returns the source categories.  Otherwise, when
    cadres.nurse_includes_technical is set, technical nurses are added into professional
    nurses (per province, year and sector; zero in years the category is not published)."""
    w = load("workforce_province")
    if raw or not C.CFG["cadres"].get("nurse_includes_technical", False):
        return w
    tech = (w[w.cadre == "พยาบาลเทคนิค"][["year", "prov_code", "sector", "headcount"]]
            .rename(columns={"headcount": "technical"}))
    prof = w[w.cadre == "พยาบาลวิชาชีพ"].merge(tech, on=["year", "prov_code", "sector"], how="left",
                                                validate="one_to_one")
    prof["headcount"] = prof.headcount + prof.technical.fillna(0)
    prof["source_columns"] = prof.source_columns + " (+technical nurses)"
    return pd.concat([w[w.cadre != "พยาบาลวิชาชีพ"], prof.drop(columns="technical")], ignore_index=True)


def workforce_province(universe: str = "all_sectors", cadres=None) -> pd.DataFrame:
    """Province x year x cadre headcount for a named universe (sum of disjoint sectors).
    A universe value is missing only if every member sector is missing."""
    sectors = C.CFG["universes"]["workforce"][universe]
    w = workforce_long()
    w = w[w.sector.isin(sectors) & w.cadre.isin(cadres or C.CADRES)]
    out = (w.groupby(["year", "prov_code", "cadre"], as_index=False)
             .headcount.agg(lambda s: s.sum(min_count=1)))
    out["universe"] = universe
    return out


def workforce_national(universe: str = "all_sectors", cadres=None) -> pd.DataFrame:
    p = workforce_province(universe, cadres)
    return (p.groupby(["year", "cadre"], as_index=False).headcount.sum()
             .assign(universe=universe))


def workforce_sector_national(cadres=None, raw: bool = False) -> pd.DataFrame:
    w = workforce_long(raw)
    w = w[w.cadre.isin(cadres or C.CADRES)]
    return (w.groupby(["year", "cadre", "sector"], as_index=False)
             .headcount.agg(lambda s: s.sum(min_count=1)))


# ----------------------------------------------------------------------------- services

@lru_cache(maxsize=None)
def services_long() -> pd.DataFrame:
    return load("services_province")


def services_province(tier: str, metrics=None) -> pd.DataFrame:
    """Province x year x metric for a tier.  tier='moph_service' = rh + gh + ch, with the
    number of reporting components kept (a province without a regional hospital has no
    RH column value; that is structural absence, not a missing report)."""
    s = services_long()
    if metrics is not None:
        s = s[s.metric.isin(metrics)]
    if tier == "moph_service":
        s = s[s.tier.isin(MOPH_TIERS)]
        out = (s.groupby(["year", "prov_code", "metric"], as_index=False)
                 .agg(value=("value", lambda v: v.sum(min_count=1)),
                      components_reported=("value", "count")))
        out["tier"] = "moph_service"
        return out
    return s[s.tier == tier][["year", "prov_code", "metric", "value", "tier"]].copy()


def services_national(tier: str, metrics=None) -> pd.DataFrame:
    p = services_province(tier, metrics)
    return (p.groupby(["year", "metric"], as_index=False)
             .agg(value=("value", lambda v: v.sum(min_count=1)), provinces=("value", "count"))
             .assign(tier=tier))


# ----------------------------------------------------------------------------- population

@lru_cache(maxsize=None)
def registers() -> pd.DataFrame:
    return load("population_registers")


def population_national(register: str = "civil_age") -> pd.DataFrame:
    r = registers()
    r = r[r.register == register]
    return r.groupby("year", as_index=False).population.sum().assign(register=register)


@lru_cache(maxsize=None)
def age_shares() -> pd.DataFrame:
    """Province x year population and 3- and 6-group age counts/shares (civil_age register)."""
    p = load("population_single_age")
    out = p.groupby(["year", "prov_code"], as_index=False).n.sum().rename(columns={"n": "population"})
    for k, bands in AGE_BANDS.items():
        for lo, hi, lab in bands:
            z = (p[p.age.between(lo, hi)].groupby(["year", "prov_code"]).n.sum()
                 .rename(f"n{k}_{lab}").reset_index())
            out = out.merge(z, on=["year", "prov_code"], validate="one_to_one")
        tot = out[[f"n{k}_{b[2]}" for b in bands]].sum(axis=1)
        assert np.allclose(tot, out.population), "age groups do not add to the population"
        for _, _, lab in bands:
            out[f"s{k}_{lab}"] = out[f"n{k}_{lab}"] / out.population
    return out


# ----------------------------------------------------------------------------- burden of disease

@lru_cache(maxsize=None)
def burden_wide() -> pd.DataFrame:
    """One row per province (77, Bangkok included) of BOD 2022 age-standardized rates per 100,000.

    bod_<m>            structural burden: all Level-3 causes except burden.exclude_causes (COVID-19)
    bod_<m>_allcause   every cause (sensitivity)
    bod_daly_<group>   CMNN / NCD / INJ, structural
    bod_<m>_<prev_x>   the BOD cause matched to each HDC prevalence indicator (burden.hdc_match)
    Sums of cause ASRs are valid within a province (one standard population)."""
    b = load("bod_province")
    cfg = C.CFG["burden"]
    keep = ~b.cause_code.isin(cfg["exclude_causes"])
    out = pd.DataFrame(index=pd.Index(sorted(b.prov_code.unique()), name="prov_code"))
    for m in ["daly", "yll", "yld", "death"]:
        out[f"bod_{m}"] = b[keep].groupby("prov_code")[f"asr_{m}"].sum()
        out[f"bod_{m}_allcause"] = b.groupby("prov_code")[f"asr_{m}"].sum()
    for g in cfg["groups"]:
        out[f"bod_daly_{g.lower()}"] = b[keep & (b.cause_group == g)].groupby("prov_code").asr_daly.sum()
    for ind, cause in cfg["hdc_match"].items():
        z = b[b.cause_code == cause].set_index("prov_code")
        out[f"bod_daly_{ind}"] = z.asr_daly
        out[f"bod_yld_{ind}"] = z.asr_yld
    out["bod_yll_share"] = out.bod_yll / out.bod_daly
    # crude (not age-standardized) rates and counts from the age-specific file, same causes
    ar = burden_age_rates()
    cnt = ar.groupby("prov_code")[["daly", "yld", "yll", "mid_pop"]].sum()
    out["bod_daly_count_2022"] = cnt.daly
    out["bod_daly_crude"] = 1e5 * cnt.daly / cnt.mid_pop
    out["bod_yld_crude"] = 1e5 * cnt.yld / cnt.mid_pop
    out["bod_mid_pop_2022"] = cnt.mid_pop
    for c in ["bod_daly", "bod_daly_cmnn", "bod_daly_ncd", "bod_daly_inj", "bod_yll", "bod_yld", "bod_daly_allcause"]:
        assert (out[c] > 0).all(), f"{c} must be positive to enter in logs"
        out[f"log_{c}"] = np.log(out[c])
    assert len(out) == 77 and out.notna().all().all()
    return out.reset_index()


@lru_cache(maxsize=None)
def burden_age_rates() -> pd.DataFrame:
    """Province x age group (8 groups) structural rates per person-year of BOD 2022: DALY, YLD, YLL
    (COVID-19 excluded) and all-cause DALY, with the source mid-year population.  These are the
    rates held constant when burden is projected with a changing age structure."""
    b = load("bod_province_age")
    keep = ~b.cause_code.isin(C.CFG["burden"]["exclude_causes"])
    g = b[keep].groupby(["prov_code", "age_group", "age_lo", "age_hi"])[["daly", "yld", "yll"]].sum()
    out = g.join(b.groupby(["prov_code", "age_group", "age_lo", "age_hi"]).agg(daly_allcause=("daly", "sum"),
                                                                                 mid_pop=("mid_pop", "first")))
    for c in ["daly", "yld", "yll", "daly_allcause"]:
        out[f"rate_{c}"] = out[c] / out.mid_pop
    return out.reset_index()


def age_group_counts(single_age: pd.DataFrame, n_col: str = "n", keys=("year", "prov_code")) -> pd.DataFrame:
    """Single-year-of-age counts -> the 8 BOD age groups (wide: g1..g8)."""
    bands = C.CFG["burden"]["age_groups"]
    a = single_age.age.to_numpy()
    grp = np.zeros(len(a), int)
    for i, (lo, hi) in enumerate(bands, start=1):
        grp[(a >= lo) & (a <= hi)] = i
    assert (grp > 0).all(), "age outside the BOD groups"
    z = single_age.assign(g=grp).groupby(list(keys) + ["g"])[n_col].sum().unstack("g")
    return z.rename(columns=lambda i: f"g{i}").reset_index()


def expected_burden(groups: pd.DataFrame, measure: str = "daly") -> np.ndarray:
    """Expected annual burden = sum over the 8 age groups of persons x the province's 2022 rate
    (rates held constant; only the size and age structure of the population change)."""
    r = burden_age_rates().pivot(index="prov_code", columns="age_group", values=f"rate_{measure}")
    R = r.reindex(groups.prov_code).to_numpy(float)
    N = groups[[f"g{i}" for i in range(1, len(C.CFG["burden"]["age_groups"]) + 1)]].to_numpy(float)
    assert np.isfinite(R).all(), "province without BOD age-specific rates"
    return (N * R).sum(1)


@lru_cache(maxsize=None)
def burden_expected_panel() -> pd.DataFrame:
    """Province x year (2013-2025, civil register by single age) expected DALY / YLD at the 2022
    age-specific rates: the burden each year's population would carry at 2022 rates."""
    g = age_group_counts(load("population_single_age"))
    for m in ["daly", "yld"]:
        g[f"bod_{m}_expected"] = expected_burden(g, m)
    return g[["year", "prov_code", "bod_daly_expected", "bod_yld_expected"]]


# ----------------------------------------------------------------------------- the provincial panel

@lru_cache(maxsize=None)
def province_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per province-year (Bangkok excluded), 2013-2025, with every variable the
    provincial analyses need and eligibility flags.  Returns (panel, join_audit)."""
    audit: list[dict] = []
    k = key()
    base = age_shares()
    base = base[~base.prov_code.isin(k.loc[k.is_bangkok, "prov_code"])].copy()
    # services: MOPH hospital block and the all-reporting block
    ms = services_province("moph_service", ["op_visits", "ip_days", "beds", "op_persons", "ip_admissions"])
    msw = ms.pivot_table(index=["year", "prov_code"], columns="metric", values="value").add_prefix("moph_").reset_index()
    comp = ms.pivot_table(index=["year", "prov_code"], columns="metric", values="components_reported").add_prefix("components_").reset_index()
    al = services_province("all_reporting", ["op_visits", "ip_days", "beds"])
    alw = al.pivot_table(index=["year", "prov_code"], columns="metric", values="value").add_prefix("all_").reset_index()
    d = _merge(base, msw, ["year", "prov_code"], audit=audit, label="population x moph_service")
    d = _merge(d, comp[["year", "prov_code", "components_op_visits", "components_ip_days", "components_beds"]],
               ["year", "prov_code"], audit=audit, label="x moph_service components")
    d = _merge(d, alw, ["year", "prov_code"], audit=audit, label="x all_reporting services")
    # case mix (fiscal year paired with the report/calendar year of the same number)
    cm = load("casemix_province").rename(columns={"fiscal_year": "year", "beds": "cmx_beds",
                                                   "ip_days": "cmx_ip_days"})
    d = _merge(d, cm[["year", "prov_code", "hospitals", "cmx_beds", "cases_calculated", "cmx_ip_days",
                      "sum_adjrw", "cmi"]], ["year", "prov_code"], audit=audit, label="x casemix (FY)")
    # morbidity
    h = load("hdc_indicators")
    hw = h[h.indicator.isin(DISEASE)].pivot_table(index=["year", "prov_code"], columns="indicator",
                                                   values="value").reset_index()
    d = _merge(d, hw, ["year", "prov_code"], audit=audit, label="x HDC prevalence")
    act = h[h.indicator.isin(["dental_visits", "op_prescriptions", "pharm_ip_days"])].pivot_table(
        index=["year", "prov_code"], columns="indicator", values="value").reset_index()
    d = _merge(d, act, ["year", "prov_code"], audit=audit, label="x HDC activity")
    # GPP of the preceding calendar year, joined by exact year (no row shift)
    g = load("gpp_province")
    gl = g.assign(year=g.year + 1).rename(columns={"gpp_per_capita": "gpp_lag1", "gpp_status": "gpp_lag1_status"})
    d = _merge(d, gl[["year", "prov_code", "gpp_lag1", "gpp_lag1_status"]], ["year", "prov_code"],
               audit=audit, label="x GPP(t-1)")
    # workforce, three universes
    for u in ["moph", "all_sectors", "public_total"]:
        w = workforce_province(u).pivot_table(index=["year", "prov_code"], columns="cadre",
                                              values="headcount").reset_index()
        w = w.rename(columns={c: f"{u}_{C.CADRE_EN[c]}" for c in C.CADRES})
        d = _merge(d, w, ["year", "prov_code"], audit=audit, label=f"x workforce {u}")
    # registers
    r = registers().pivot_table(index=["year", "prov_code"], columns="register", values="population").reset_index()
    r = r.rename(columns={"civil_grand": "pop_civil_grand", "nhso_rights": "pop_nhso", "civil_age": "pop_civil_age"})
    d = _merge(d, r, ["year", "prov_code"], audit=audit, label="x population registers")
    # modeled burden of disease 2022: one value per province, repeated over years (time-invariant)
    d = _merge(d, burden_wide(), ["prov_code"], validate="many_to_one", audit=audit, label="x BOD 2022 (time-invariant)")
    d = _merge(d, burden_expected_panel(), ["year", "prov_code"], audit=audit, label="x expected burden at 2022 age-specific rates")
    assert np.allclose(d.population, d.pop_civil_age)
    d = d.merge(k[["prov_code", "province", "province_en", "health_region"]], on="prov_code", validate="many_to_one")
    d = d.sort_values(["prov_code", "year"]).reset_index(drop=True)

    # outcomes and log densities (units stated in the variable names)
    d["op_moph_pc"] = d.moph_op_visits / d.population          # visits per person per year
    d["ip_moph_pc"] = d.moph_ip_days / d.population            # inpatient days per person per year
    d["adjrw_pc"] = d.sum_adjrw / d.population                 # AdjRW per person per fiscal year
    d["log_beds_moph_per1000"] = np.log(1000 * d.moph_beds / d.population)
    d["log_beds_cmx_per1000"] = np.log(1000 * d.cmx_beds / d.population)
    d["log_gpp_lag1"] = np.log(d.gpp_lag1)
    for u in ["moph", "all_sectors"]:
        for c in ["physicians", "professional_nurses"]:
            d[f"log_{u}_{c}_per100k"] = np.log(100_000 * d[f"{u}_{c}"] / d.population)

    # eligibility flags
    yrs_m = range(C.CFG["years"]["morbidity_first"], C.CFG["years"]["morbidity_last"] + 1)
    need_common = DISEASE + ["log_gpp_lag1", "log_beds_moph_per1000", "log_beds_cmx_per1000",
                             "log_moph_physicians_per100k", "log_moph_professional_nurses_per100k",
                             "op_moph_pc", "ip_moph_pc", "adjrw_pc", "s3_0-14", "s3_60+"]
    fin = np.isfinite(d[need_common].astype(float)).all(axis=1)
    d["elig_m5_common"] = d.year.isin(yrs_m) & fin
    d["elig_long_moph"] = np.isfinite(d[["op_moph_pc", "ip_moph_pc", "log_beds_moph_per1000",
                                         "log_moph_physicians_per100k",
                                         "log_moph_professional_nurses_per100k"]].astype(float)).all(axis=1)
    d["elig_casemix"] = np.isfinite(d[["adjrw_pc", "log_beds_cmx_per1000"]].astype(float)).all(axis=1)
    return d, pd.DataFrame(audit)


def m5_exclusions(d: pd.DataFrame) -> pd.DataFrame:
    """Every expected 76 x morbidity-year row that is not in the common M5 sample, with reasons."""
    yrs = range(C.CFG["years"]["morbidity_first"], C.CFG["years"]["morbidity_last"] + 1)
    need = DISEASE + ["log_gpp_lag1", "log_beds_moph_per1000", "log_beds_cmx_per1000",
                      "log_moph_physicians_per100k", "log_moph_professional_nurses_per100k",
                      "op_moph_pc", "ip_moph_pc", "adjrw_pc"]
    z = d[d.year.isin(yrs)]
    rows = []
    for _, r in z[~z.elig_m5_common].iterrows():
        miss = [c for c in need if not np.isfinite(float(r[c]))]
        rows.append(dict(prov_code=r.prov_code, province=r.province, year=r.year,
                         missing_fields=",".join(miss)))
    return pd.DataFrame(rows, columns=["prov_code", "province", "year", "missing_fields"])


# ----------------------------------------------------------------------------- audits

def audit_tables() -> dict[str, pd.DataFrame]:
    """coverage_by_year, missingness, duplicate_keys, join_audit, sample_flow, national_76_bridge,
    workforce_reconciliation, service_nesting, casemix_identity."""
    out = {}
    d, joins = province_panel()
    out["join_audit"] = joins
    w = workforce_long(raw=True)          # reconcile the source categories against published totals
    # coverage by year (source x year: provinces with a non-missing value)
    cov = []
    for src, t, cols in [("workforce", w, "headcount"), ("services", services_long(), "value")]:
        z = t.dropna(subset=[cols]).groupby("year").prov_code.nunique()
        cov += [dict(source=src, year=y, provinces=n) for y, n in z.items()]
    cm = load("casemix_province")
    cov += [dict(source="casemix", year=y, provinces=n) for y, n in cm.groupby("fiscal_year").prov_code.nunique().items()]
    h = load("hdc_indicators")
    for ind, g in h.groupby("indicator"):
        cov += [dict(source=f"hdc:{ind}", year=y, provinces=n)
                for y, n in g.dropna(subset=["value"]).groupby("year").prov_code.nunique().items()]
    bd = load("bod_province_age")
    cov += [dict(source="bod_age:daly", year=y, provinces=n) for y, n in bd.groupby("year").prov_code.nunique().items()]
    bd = load("bod_province")
    cov += [dict(source="bod:asr_daly", year=y, provinces=n) for y, n in bd.groupby("year").prov_code.nunique().items()]
    g = load("gpp_province")
    cov += [dict(source="gpp", year=y, provinces=n) for y, n in g.dropna(subset=["gpp_per_capita"]).groupby("year").prov_code.nunique().items() if y >= 2010]
    out["coverage_by_year"] = pd.DataFrame(cov)
    # missingness in the provincial panel
    cols = [c for c in d.columns if c not in ("province", "province_en")]
    out["missingness"] = (d.groupby("year")[cols].apply(lambda g: g.isna().sum())
                          .T.rename_axis("variable").reset_index())
    # duplicate keys in canonical tables
    dups = []
    for name, keys_ in [("workforce_province", ["year", "prov_code", "cadre", "sector"]),
                        ("services_province", ["year", "prov_code", "tier", "metric"]),
                        ("casemix_province", ["fiscal_year", "prov_code"]),
                        ("population_registers", ["year", "prov_code", "register"]),
                        ("hdc_indicators", ["year", "prov_code", "indicator"]),
                        ("gpp_province", ["year", "prov_code"]),
                        ("bod_province", ["year", "prov_code", "cause_code"]),
                        ("bod_province_age", ["year", "prov_code", "cause_code", "age_group"])]:
        t = load(name)
        dups.append(dict(table=name, key=",".join(keys_), rows=len(t), duplicate_keys=int(t.duplicated(keys_).sum())))
    out["duplicate_keys"] = pd.DataFrame(dups)
    # workforce parts vs published total
    parts = (w[w.sector.isin(C.CFG["universes"]["workforce"]["all_sectors"])]
             .groupby(["year", "cadre"]).headcount.sum())
    pub = w[w.sector == "published_total"].groupby(["year", "cadre"]).headcount.sum()
    rec = pd.concat([parts.rename("parts_sum"), pub.rename("published_total")], axis=1).reset_index()
    rec["gap"] = rec.parts_sum - rec.published_total
    out["workforce_reconciliation"] = rec
    # service nesting: MOPH hospital block within the all-reporting block
    ms = services_national("moph_service").rename(columns={"value": "moph_service"})
    al = services_national("all_reporting").rename(columns={"value": "all_reporting"})
    nest = ms[["year", "metric", "moph_service"]].merge(al[["year", "metric", "all_reporting"]], on=["year", "metric"])
    nest["moph_share_pct"] = 100 * nest.moph_service / nest.all_reporting
    out["service_nesting"] = nest
    sp = (services_province("moph_service", ["op_visits", "ip_days"])
          .merge(services_province("all_reporting", ["op_visits", "ip_days"]), on=["year", "prov_code", "metric"],
                 suffixes=("_moph", "_all")))
    out["service_nesting_province_anomalies"] = sp[sp.value_moph > sp.value_all]
    # case-mix identity
    hosp = load("casemix_hospital")
    out["casemix_identity"] = (hosp.groupby("fiscal_year")
                               .agg(hospitals=("hospital_code", "nunique"),
                                    max_abs_cmi_gap=("cmi_identity_gap", lambda s: s.abs().max()),
                                    hospitals_partial_year=("months_sent", lambda s: int((s < 12).sum())))
                               .reset_index())
    # sample flow for the common M5 panel
    k = key()
    yrs = list(range(C.CFG["years"]["morbidity_first"], C.CFG["years"]["morbidity_last"] + 1))
    flow = [dict(step="provinces x morbidity years, all 77 provinces", rows=77 * len(yrs)),
            dict(step="drop Bangkok before sampling", rows=76 * len(yrs))]
    z = d[d.year.isin(yrs)]
    flow.append(dict(step="rows present in the joined panel", rows=len(z)))
    flow.append(dict(step="complete cases for all M5 covariates and the three outcomes", rows=int(z.elig_m5_common.sum())))
    out["analysis_sample_flow"] = pd.DataFrame(flow)
    out["m5_exclusions"] = m5_exclusions(d)
    # national (77) vs 76-province bridge for key series
    br = []
    bk = int(k.loc[k.is_bangkok, "prov_code"].iloc[0])
    for u in ["all_sectors", "moph"]:
        wp = workforce_province(u)
        for (y, c), g in wp.groupby(["year", "cadre"]):
            br.append(dict(series=f"workforce_{u}", cadre=c, year=y, national=g.headcount.sum(),
                           bangkok=g.loc[g.prov_code == bk, "headcount"].sum(),
                           provinces_76=g.loc[g.prov_code != bk, "headcount"].sum()))
    pn = registers()
    for (y, reg), g in pn.groupby(["year", "register"]):
        br.append(dict(series=f"population_{reg}", cadre="", year=y, national=g.population.sum(),
                       bangkok=g.loc[g.prov_code == bk, "population"].sum(),
                       provinces_76=g.loc[g.prov_code != bk, "population"].sum()))
    for tier in ["moph_service", "all_reporting"]:
        sp = services_province(tier, ["op_visits", "ip_days"])
        for (y, m), g in sp.groupby(["year", "metric"]):
            br.append(dict(series=f"services_{tier}_{m}", cadre="", year=y, national=g.value.sum(),
                           bangkok=g.loc[g.prov_code == bk, "value"].sum(),
                           provinces_76=g.loc[g.prov_code != bk, "value"].sum()))
    b = pd.DataFrame(br)
    b["bangkok_share_pct"] = 100 * b.bangkok / b.national
    out["national_76_bridge"] = b
    return out
