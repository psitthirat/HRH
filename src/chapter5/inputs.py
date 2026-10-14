"""The Chapter 5 input contract.

Everything numerical comes from the Chapter 4 canonical tables and fitted artifacts:

* baseline physician stock  = MOPH physicians (Health Resource Report) in 76 provinces, 2025
* entries/exits             = HROPS recorded events (FY), Chapter 4.4 parsing
* M5                        = refitted with chapter4.models on the chapter4 common sample and
                              checked against the exported T423_M5_COEFFICIENTS (must match)
* reference profile         = exported T423_REFERENCE_PROFILE (checked against a recomputation)

`artifact_register()` records the SHA-256 of every Chapter 4 artifact read, so a Chapter 5
run can be traced to the exact upstream state.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from chapter4 import config as C4
from chapter4 import models as MD
from chapter4 import panels as P4
from chapter4.ingest import load as load4

CH4_ARTIFACTS = [
    "data/processed/province_key.csv", "data/processed/workforce_province.csv",
    "data/processed/population_single_age.csv", "data/processed/population_registers.csv",
    "data/processed/services_province.csv", "data/processed/casemix_province.csv",
    "data/processed/hdc_indicators.csv", "data/processed/gpp_province.csv",
    "data/processed/flow_events.csv", "data/processed/bod_province.csv", "data/processed/bod_province_age.csv", "data/processed/_build_meta.json",
    "outputs/chapter4_2/tables/T423_M5_COEFFICIENTS.csv",
    "outputs/chapter4_2/tables/T423_REFERENCE_PROFILE.csv",
    "outputs/chapter4_2/tables/T423_M5_ACCEPTABILITY.csv",
    "outputs/chapter4_2/tables/T423_M5_SUPPORT.csv",
    "outputs/chapter4_2/tables/T423_TEMPORAL_VALIDATION.csv",
    "outputs/chapter4_2/run_manifest.json",
    "outputs/chapter4_4/tables/T44_WORKLOAD_ASSOCIATIONS.csv",
    "outputs/chapter4_4/tables/T44_STOCK_FLOW_NATIONAL.csv",
    "outputs/chapter4_4/tables/T44_FUTURE_MODEL_PARAMETERS.csv",
    "outputs/chapter4_4/run_manifest.json",
    "config/analysis.toml", "config/source_registry.toml",
]

M5_BLOCKS = ["age", "disease", "gpp", "beds", "physicians", "nurses"]
OUTCOMES = ["op_moph", "ip_moph", "adjrw"]
CAD = "แพทย์"


def artifact_register() -> pd.DataFrame:
    rows = []
    for rel in CH4_ARTIFACTS:
        p = C4.ROOT / rel
        rows.append(dict(artifact=rel, exists=p.exists(), sha256=C4.file_sha256(p),
                         bytes=p.stat().st_size if p.exists() else np.nan))
    rows.append(dict(artifact="src/chapter4/*.py (code_hash)", exists=True, sha256=C4.code_hash(), bytes=np.nan))
    return pd.DataFrame(rows)


def inputs_fingerprint() -> str:
    import hashlib
    h = hashlib.sha256()
    for r in artifact_register().itertuples():
        h.update(f"{r.artifact}:{r.sha256}".encode())
    return h.hexdigest()[:16]


# ----------------------------------------------------------------------------- provinces and baseline

def provinces() -> pd.DataFrame:
    k = P4.key()
    k = k[~k.is_bangkok].sort_values("prov_code").reset_index(drop=True)
    assert len(k) == 76
    return k[["prov_code", "province", "province_en", "health_region"]]


def panel() -> pd.DataFrame:
    d, _ = P4.province_panel()
    return d


def baseline(S) -> pd.DataFrame:
    """One row per province: 2025 stock, populations, services, beds, nurses, GPP."""
    y = S.base_year
    d = panel()
    b = d[d.year == y].set_index("prov_code")
    k = provinces().set_index("prov_code")
    out = k.join(b[["population", "pop_nhso", "pop_civil_grand", "moph_physicians", "moph_professional_nurses",
                    "moph_beds", "cmx_beds", "moph_op_visits", "moph_ip_days", "sum_adjrw", "gpp_lag1",
                    "s3_0-14", "s3_60+"] + P4.DISEASE], validate="one_to_one")
    out = out.rename(columns={"population": "pop_civil", "moph_physicians": "H0"})
    assert out.H0.notna().all() and (out.H0 > 0).all(), "baseline physician stock missing for a province"
    assert len(out) == 76
    return out.reset_index()


# ----------------------------------------------------------------------------- flows

EXIT_CAUSES = ["resignation", "retirement", "transfer_out", "death", "disciplinary"]
REENTRY = ["reinstatement", "transfer_in"]


def flow_events_province() -> pd.DataFrame:
    f = load4("flow_events")
    f = f[(f.cadre == CAD) & (f.row_type == "province")]
    g = (f.groupby(["fiscal_year", "prov_code", "direction", "category"], as_index=False)
           .events.sum(min_count=1))
    g["prov_code"] = g.prov_code.astype(int)
    return g


def stock_series(universe: str = "moph") -> pd.DataFrame:
    w = P4.workforce_province(universe, [CAD])
    k = provinces()
    return w[w.prov_code.isin(k.prov_code)][["year", "prov_code", "headcount"]]


def _eb(E: np.ndarray, N: np.ndarray, prior_mean: np.ndarray, floor_rel: float = 0.05):
    """Gamma-Poisson empirical-Bayes pooling toward prior_mean (per unit).

    Between-unit variance by the method of moments on the exposure-weighted squared
    deviations minus expected Poisson noise, floored at (floor_rel * national mean)^2 so
    a sparse cause is never pooled completely."""
    r = np.where(N > 0, E / N, 0.0)
    w = N / N.sum()
    S = float((w * (r - prior_mean) ** 2).sum())
    noise = float((w * prior_mean / np.maximum(N, 1e-9)).sum())
    m_nat = E.sum() / N.sum()
    var_b = max(S - noise, (floor_rel * m_nat) ** 2, 1e-12)
    alpha = prior_mean ** 2 / var_b
    beta = prior_mean / var_b
    post_a, post_b = alpha + E, beta + N
    return dict(raw=r, prior_mean=prior_mean, alpha=alpha, beta=beta, post_a=post_a, post_b=post_b,
                post_mean=post_a / post_b, var_between=var_b, shrinkage=beta / (beta + N))


def flow_rates(S) -> pd.DataFrame:
    """Province event rates per opening-stock person-year, raw and pooled, by cause.

    Exposure: MOPH stock of report year FY-1 (Chapter 4.4 convention: events per 100 prior-year
    staff).  Window: departures.estimation_fy (post-2020-break, complete fiscal years only)."""
    fy0, fy1 = S.cfg["departures"]["estimation_fy"]
    ev = flow_events_province()
    ev = ev[ev.fiscal_year.between(fy0, fy1)]
    st = stock_series()
    k = provinces()
    expo = (st.assign(fiscal_year=st.year + 1)[lambda z: z.fiscal_year.between(fy0, fy1)]
              .groupby("prov_code").headcount.sum().reindex(k.prov_code))
    expo_same = st[st.year.between(fy0, fy1)].groupby("prov_code").headcount.sum().reindex(k.prov_code)
    rows = []
    for cause, direction in [(c, "exit") for c in EXIT_CAUSES] + [(c, "entry") for c in REENTRY] + \
                            [("recruitment_hiring", "entry")]:
        e = (ev[(ev.direction == direction) & (ev.category == cause)].groupby("prov_code").events.sum()
               .reindex(k.prov_code).fillna(0.0))
        E, N = e.to_numpy(float), expo.to_numpy(float)
        if cause in ("resignation", "recruitment_hiring"):
            reg = k.health_region.to_numpy()
            prior = np.array([E[reg == g].sum() / N[reg == g].sum() for g in reg])
            level = "health_region"
        else:
            prior = np.full(len(E), E.sum() / N.sum())
            level = "national"
        eb = _eb(E, N, prior)
        for i, p in enumerate(k.prov_code):
            rows.append(dict(prov_code=int(p), cause=cause, direction=direction, events=E[i], exposure=N[i],
                             exposure_same_year_stock=float(expo_same.iloc[i]),
                             rate_raw=eb["raw"][i], prior_level=level, prior_mean=eb["prior_mean"][i],
                             post_a=eb["post_a"][i], post_b=eb["post_b"][i], rate_pooled=eb["post_mean"][i],
                             shrinkage=eb["shrinkage"][i],
                             rate_national=E.sum() / N.sum(),
                             rate_same_year_exposure=E[i] / float(expo_same.iloc[i])))
    return pd.DataFrame(rows)


def recruitment_shares(S, fy=(2021, 2025)) -> pd.DataFrame:
    ev = flow_events_province()
    ev = ev[(ev.direction == "entry") & (ev.category == "recruitment_hiring") & ev.fiscal_year.between(*fy)]
    k = provinces()
    e = ev.groupby("prov_code").events.sum().reindex(k.prov_code).fillna(0)
    return pd.DataFrame({"prov_code": k.prov_code, "recruitment_events": e.to_numpy(),
                         "share": (e / e.sum()).to_numpy()})


def national_stock_flow(S) -> pd.DataFrame:
    """Recorded national (76-province) stock-flow identity for physicians, FY2017-2025."""
    ev = flow_events_province()
    st = stock_series().groupby("year").headcount.sum()
    rows = []
    for fy in sorted(ev.fiscal_year.unique()):
        if fy - 1 not in st.index or fy not in st.index:
            continue
        e = ev[ev.fiscal_year == fy]
        rows.append(dict(fiscal_year=int(fy), stock_prev=st[fy - 1], stock=st[fy],
                         recruitment=e[(e.direction == "entry") & (e.category == "recruitment_hiring")].events.sum(),
                         reentry=e[(e.direction == "entry") & e.category.isin(REENTRY)].events.sum(),
                         exits=e[e.direction == "exit"].events.sum()))
    d = pd.DataFrame(rows)
    d["d_stock"] = d.stock - d.stock_prev
    d["net_recorded"] = d.recruitment + d.reentry - d.exits
    d["residual"] = d.d_stock - d.net_recorded
    return d


# ----------------------------------------------------------------------------- M5 package

def _cr1_cov(X, y, groups):
    b = MD.ols(X, y)
    res = y - X @ b
    XtXi = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    G = np.unique(groups)
    for g in G:
        s = X[groups == g].T @ res[groups == g]
        meat += np.outer(s, s)
    n, k = X.shape
    return XtXi @ meat @ XtXi * (len(G) / (len(G) - 1)) * ((n - 1) / (n - np.linalg.matrix_rank(X)))


def m5_package(S, cache_dir=None, draws: int | None = None) -> dict:
    """Refit M5 exactly as Chapter 4 (common sample, OLS on rates, year dummies), check it against
    the exported coefficients, and add what Chapter 5 needs: CR1 covariance, a positive-mean
    (quasi-Poisson) alternative, training support, and province-cluster bootstrap refits drawn
    jointly for the three outcomes (one draw = one simulation path)."""
    d = panel()
    Z = d[d.elig_m5_common].reset_index(drop=True)
    years = sorted(int(y) for y in Z.year.unique())
    exported = pd.read_csv(C4.ROOT / "outputs/chapter4_2/tables/T423_M5_COEFFICIENTS.csv", encoding="utf-8-sig")
    ref_exp = pd.read_csv(C4.ROOT / "outputs/chapter4_2/tables/T423_REFERENCE_PROFILE.csv", encoding="utf-8-sig")
    ref_year = int(S.cfg["m5"]["reference_year"])
    assert int(ref_exp.reference_year.iloc[0]) == ref_year, "Chapter 4 reference year differs from chapter5 config"
    ref_rows = d[d.year == ref_year]
    pkg = dict(years=years, n_rows=len(Z), n_prov=int(Z.prov_code.nunique()), beta={}, cov={}, beta_pos={},
               names=None, ref={}, reproduction={}, Z=Z)
    groups = Z.prov_code.to_numpy()
    for o in OUTCOMES:
        X, names = MD.design(Z, o, M5_BLOCKS, years=years)
        y = Z[MD.RATE_COL[o]].to_numpy(float)
        b = MD.ols(X, y)
        diff = float(np.abs(b - exported[o].to_numpy()).max())
        assert list(exported.term) == names, "exported M5 term order differs"
        assert diff < 1e-8, f"M5 {o} does not reproduce the exported coefficients (max diff {diff})"
        pkg["reproduction"][o] = diff
        pkg["beta"][o] = b
        pkg["cov"][o] = _cr1_cov(X, y, groups)
        bp, ok = MD.fit_positive(X, y)
        pkg["beta_pos"][o] = np.asarray(bp)
        pkg["names"] = names
        ref = MD.reference_profile(ref_rows, o, ref_rows)
        r_e = ref_exp[ref_exp.outcome == o].iloc[0]
        for kk in ["log_beds", "log_physicians", "log_nurses", "log_gpp_lag1"]:
            assert abs(ref[kk] - r_e[kk]) < 1e-9, f"reference profile {o}/{kk} differs from the export"
        pkg["ref"][o] = ref
    # training support of every covariate that moves in Chapter 5
    cols = ["s3_0-14", "s3_60+"] + P4.DISEASE + ["log_gpp_lag1", "log_beds_moph_per1000", "log_beds_cmx_per1000",
                                                 MD.PHYS, MD.NURS]
    pkg["support"] = pd.DataFrame({"variable": cols, "min": [Z[c].min() for c in cols],
                                   "max": [Z[c].max() for c in cols], "mean": [Z[c].mean() for c in cols]})
    hcols = ["s3_0-14", "s3_60+"] + P4.DISEASE
    Xh = Z[hcols].to_numpy(float)
    pkg["health_mu"], pkg["health_cov_inv"] = Xh.mean(0), np.linalg.inv(np.cov(Xh.T))
    dh = np.sqrt(np.einsum("ij,jk,ik->i", Xh - pkg["health_mu"], pkg["health_cov_inv"], Xh - pkg["health_mu"]))
    pkg["health_maha_max"] = float(dh.max())
    pkg["health_cols"] = hcols
    # bootstrap refits (cached by inputs fingerprint and seed)
    B = int(draws if draws is not None else S.cfg["m5"]["coefficient_draws"])
    key = f"m5_boot_{inputs_fingerprint()}_{S.seed}_{B}.npz"
    path = (cache_dir / key) if cache_dir is not None else None
    if path is not None and path.exists():
        z = np.load(path)
        pkg["boot"] = {o: z[o] for o in OUTCOMES}
    else:
        rng = np.random.default_rng(S.seed + 55)
        provs = np.array(sorted(Z.prov_code.unique()))
        pidx = {p: np.flatnonzero(groups == p) for p in provs}
        boot = {o: np.empty((B, len(pkg["names"]))) for o in OUTCOMES}
        Xs = {o: MD.design(Z, o, M5_BLOCKS, years=years)[0] for o in OUTCOMES}
        ys = {o: Z[MD.RATE_COL[o]].to_numpy(float) for o in OUTCOMES}
        for bi in range(B):
            ids = np.concatenate([pidx[p] for p in rng.choice(provs, len(provs), replace=True)])
            for o in OUTCOMES:
                boot[o][bi] = MD.ols(Xs[o][ids], ys[o][ids])
        pkg["boot"] = boot
        if path is not None:
            np.savez_compressed(path, **boot)
    return pkg


def m5_coefficient_table(pkg) -> pd.DataFrame:
    rows = []
    for o in OUTCOMES:
        se = np.sqrt(np.diag(pkg["cov"][o]))
        bs = pkg["boot"][o]
        for j, t in enumerate(pkg["names"]):
            rows.append(dict(outcome=o, term=t, coef=pkg["beta"][o][j], se_cr1=se[j],
                             boot_lo95=np.percentile(bs[:, j], 2.5), boot_hi95=np.percentile(bs[:, j], 97.5),
                             coef_positive_mean_model=pkg["beta_pos"][o][j],
                             reproduction_max_abs_diff=pkg["reproduction"][o]))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- readiness inventory

def readiness_inventory(S, flows: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """Section 3.1 inventory: what exists, what is used, and the fallback for what does not."""
    R = []

    def add(inp, content, status, used, fallback, affects):
        R.append(dict(input=inp, minimum_content=content, status=status, used_in_chapter5=used,
                      fallback_if_absent=fallback, affected_claims=affects))
    add("Baseline physician stock", "province, employer scope, reference date, count",
        "partial: MOPH-wide headcount (HRR report year 2025); no OPS-only stock; no FTE",
        f"MOPH physicians, 76 provinces, 2025 = {base.H0.sum():,.0f} (provisional managed stock)",
        "broader-scope stock used as an explicitly labelled provisional mapping",
        "every plan is exploratory_policy_scenario, not a calibrated OPS instruction")
    add("Historical workforce", "comparable annual provincial stocks and breaks", "available 2013-2025 (break 2016, 2020)",
        "stock-flow backtest FY2021-2025; not used to infer individual transitions", "-", "backtest only")
    add("Entries/exits", "category x province x year, boundary and duplication rules",
        "partial: HROPS events FY2017-2025 (OPS), not unique persons; transfers are cross-agency, no origin-destination",
        "hazards per opening-stock person-year FY2021-2025, EB-pooled; recruitment replaced by the allocator",
        "event-to-person assumption stated; internal transfers only as conditional proposals",
        "departure expectations; transfer routes are proposals, not approved moves")
    add("Population", "baseline age/sex counts and register definitions", "available: DOPA single-year age x sex 2013-2025",
        "civil_age register (Thai nationals, regular registration) as the M5 and allocation denominator", "-", "-")
    add("Demographic projection inputs", "official provincial projection or survival, fertility and migration",
        "absent: no official provincial projection, no vital statistics, no migration flows in the repository",
        "Hamilton-Perry cohort-change projection (deaths and net migration combined) with a national control",
        "request NESDC/IPSR provincial projection and DOPA births/deaths", "population and age paths")
    add("Entitlement register", "province, reference date, scheme/age/sex", "available: NHSO December snapshots 2010-2025",
        "province ratio NHSO/civil held at 2025 with 2019-2025 bounds", "-", "P entitlement variant")
    add("Service data", "OP visits, IP days, AdjRW, universe, breaks", "available: HRR RH+GH+CH 2013-2025; case-mix FY2018-2025",
        "constant-rate benchmark chosen by backtest; COVID years flagged", "-", "S family")
    add("M5 package", "coefficients, covariance, transforms, reference, training sample, checks",
        "available: refitted and matched to T423_M5_COEFFICIENTS (max diff < 1e-8)",
        "N-STD, resource-responsive services, N-FB", "-", "N family; feedback experiment")
    add("Future disease/economic paths", "defensible projections or explicit assumptions",
        "absent: 4 years of aggregate diagnosed prevalence; no age-specific prevalence",
        "fixed-2025 prevalence (central); bounded trend and age-held variants", "-", "N-STD growth")
    add("Modeled burden of disease", "provincial burden by cause, age and sex; several years",
        "partial: BOD Thailand 2022, 174 causes x 8 age groups (counts, rates, mid-year population), both sexes, one year; "
        "national totals only for other years",
        "B family: projected age groups x 2022 age-specific DALY rates (COVID-19 excluded); YLD and age-standardized variants",
        "further subnational BOD rounds would allow trends in age-specific rates", "B family (age-specific rates fixed at 2022)")
    add("Beds and nurses", "baseline and future paths matching M5", "baseline only (2025)",
        "common paths: fixed 2025 counts (central), recent-CAGR growth (sensitivity)", "-", "feedback experiment")
    add("Production and recruitment", "graduates, licensing, OPS share, acceptance, timing",
        "absent: no medical-school intake, graduate or placement data in the repository",
        "direct available-appointments scenario (2,000/year, illustrative); graduate and intake modes implemented with illustrative parameters",
        "request graduate and placement (ใช้ทุน) data", "supply totals")
    add("Operational limits", "funded posts, onboarding, eligibility, routes, service floors, budget",
        "absent", "configurable illustrative caps (10% gross arrivals, 2% transfers, 95% drawdown)",
        "policy inputs must be adopted by the decision-maker", "feasibility and binding constraints")
    add("Physician age / cohort", "age or year of first appointment", "absent",
        "retirement as a recorded-event rate (no age-specific retirement)", "request HROPS age distribution",
        "retirement wave timing")
    return pd.DataFrame(R)
