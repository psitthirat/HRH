"""Population and entitlement projections for 2026-2040.

Method (documented in docs/methods_and_limitations.md).  The repository has no official provincial
projection and no provincial births, deaths or migration flows, so the projection is a
Hamilton-Perry cohort-change-ratio model on the DOPA civil register (single year of age x sex):

    P[p, a+1, s, t+1] = CCR[p, a, s] * P[p, a, s, t]                   a = 0..99
    P[p, 101+, s, t+1] = CCR_open[p, s] * (P[p, 100, s, t] + P[p, 101+, s, t])
    P[p, 0, s, t+1]    = CWR[p, s] * W[p, 15-49, t+1]                  (child-woman ratio)

A cohort-change ratio combines survival and net migration; the two are not separable with
these data.  Internal migration is represented as the provincial deviation from the national
ratio, CCR_p = CCR_nat * (CCR_p / CCR_nat)^m, and the migration scenarios scale that deviation
(m = 0.5, 1, 1.5).  With national control the 77 provincial projections (Bangkok included, as
the external demographic boundary of the 76-province allocation) are raked each year to the
national cohort projection by age and sex, so internal net migration sums to zero across the
full geographic system while the 76 provinces alone need not balance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from chapter4 import config as C4
from chapter4.ingest import load as load4
from chapter4 import panels as P4

AGES = np.arange(0, 102)          # 101 = open-ended ">100"
SEXES = ["M", "F"]
MIN_DEN = 50.0                    # a province-age cohort smaller than this borrows the national ratio


BOD_AGE_GROUPS = [tuple(b) for b in C4.CFG["burden"]["age_groups"]]

def register_array():
    p = load4("population_single_age")
    provs = sorted(p.prov_code.unique())
    years = sorted(p.year.unique())
    arr = np.zeros((len(provs), 2, len(AGES), len(years)))
    pi = {c: i for i, c in enumerate(provs)}
    yi = {y: i for i, y in enumerate(years)}
    si = {"M": 0, "F": 1}
    arr[p.prov_code.map(pi).to_numpy(), p.sex.map(si).to_numpy(), p.age.to_numpy(), p.year.map(yi).to_numpy()] = p.n.to_numpy()
    return arr, np.array(provs), np.array(years)


def ccr(arr, years, window):
    """Cohort-change ratios pooled over pairs t -> t+1 for t in [window0, window1]."""
    t0, t1 = window
    ts = [i for i, y in enumerate(years) if t0 <= y <= t1 and y + 1 in years]
    num = np.zeros(arr.shape[:3])
    den = np.zeros(arr.shape[:3])
    for i in ts:
        num[..., 1:101] += arr[..., 1:101, i + 1]
        den[..., 0:100] += arr[..., 0:100, i]
        num[..., 101] += arr[..., 101, i + 1]
        den[..., 101] += arr[..., 100, i] + arr[..., 101, i]
    # ratio for age a -> a+1 stored at index a (0..99); open group at 101
    r = np.full(arr.shape[:3], np.nan)
    r[..., 0:100] = num[..., 1:101] / np.where(den[..., 0:100] > 0, den[..., 0:100], np.nan)
    r[..., 101] = num[..., 101] / np.where(den[..., 101] > 0, den[..., 101], np.nan)
    nat_num, nat_den = num.sum(0), den.sum(0)
    nat = np.full(arr.shape[1:3], np.nan)
    nat[:, 0:100] = nat_num[:, 1:101] / nat_den[:, 0:100]
    nat[:, 101] = nat_num[:, 101] / nat_den[:, 101]
    small = (den < MIN_DEN) | ~np.isfinite(r)
    small[..., 100] = True                     # index 100 unused (100 -> open group)
    r = np.where(small, nat[None], r)
    return r, nat, float(small[..., :100].mean())


def cwr(arr, years, window):
    t0, t1 = window
    ts = [i for i, y in enumerate(years) if t0 <= y <= t1]
    sub = arr[..., ts]                                 # prov x sex x age x years
    b = sub[:, :, 0, :].sum(-1)                        # prov x sex
    w = sub[:, 1, 15:50, :].sum(axis=(1, 2))           # women 15-49
    r = b / w[:, None]
    nat = sub[:, :, 0, :].sum(axis=(0, 2)) / sub[:, 1, 15:50, :].sum()
    return r, nat


def _step(P, r, c):
    """One-year projection of P[prov, sex, age]."""
    Q = np.zeros_like(P)
    Q[..., 1:101] = P[..., 0:100] * r[..., 0:100]
    Q[..., 101] = (P[..., 100] + P[..., 101]) * r[..., 101]
    W = Q[:, 1, 15:50].sum(-1) if Q.ndim == 3 else Q[1, 15:50].sum()
    if Q.ndim == 3:
        Q[:, :, 0] = c * W[:, None]
    else:
        Q[:, 0] = c * W
    return Q


def project(arr, provs, years, base_year, horizon_last, ccr_window, cwr_window, m=1.0,
            national_control=True):
    """Returns {year: P[prov, sex, age]} for base_year..horizon_last and a component table."""
    r, r_nat, share_borrowed = ccr(arr[..., : list(years).index(base_year) + 1],
                                   years[: list(years).index(base_year) + 1], ccr_window)
    c, c_nat = cwr(arr[..., : list(years).index(base_year) + 1], years[: list(years).index(base_year) + 1],
                   cwr_window)
    r_m = r_nat[None] * np.power(r / r_nat[None], m)
    P = arr[..., list(years).index(base_year)].copy()
    N = P.sum(0)
    out = {base_year: P.copy()}
    comp = []
    raked_abs = 0.0
    for y in range(base_year + 1, horizon_last + 1):
        Q = _step(P, r_m, c)
        Nq = _step(N, r_nat, c_nat)
        if national_control:
            s = Q.sum(0)
            f = np.where(s > 0, Nq / np.where(s > 0, s, 1), 1.0)
            raked_abs += float(np.abs(Q * (f[None] - 1)).sum())
            Q = Q * f[None]
        births = Q[..., 0].sum(-1)
        existing = Q[..., 1:].sum((-1, -2)) - P.sum((-1, -2))
        for i, pc in enumerate(provs):
            comp.append(dict(year=y, prov_code=int(pc), births=float(births[i].sum()),
                             existing_cohort_change=float(existing[i]),
                             population=float(Q[i].sum())))
        P, N = Q, Nq
        out[y] = P.copy()
    meta = dict(share_ccr_borrowed_from_national=share_borrowed, raking_abs_persons=raked_abs,
                cwr_national_M=float(c_nat[0]), cwr_national_F=float(c_nat[1]))
    return out, pd.DataFrame(comp), meta


def aggregate(proj: dict, provs) -> pd.DataFrame:
    rows = []
    for y, P in proj.items():
        tot = P.sum((1, 2))
        a014 = P[:, :, 0:15].sum((1, 2))
        a60 = P[:, :, 60:].sum((1, 2))
        w1549 = P[:, 1, 15:50].sum(-1)
        # the 8 BOD age groups (chapter 4 burden.age_groups), for burden projected at fixed age-specific rates
        g8 = np.stack([P[:, :, lo:min(hi, P.shape[2] - 1) + 1].sum((1, 2)) for lo, hi in BOD_AGE_GROUPS], 1)
        assert np.allclose(g8.sum(1), tot)
        for i, pc in enumerate(provs):
            rows.append({"year": y, "prov_code": int(pc), "population": tot[i], "n3_0-14": a014[i],
                         "n3_15-59": tot[i] - a014[i] - a60[i], "n3_60+": a60[i], "women_15_49": w1549[i],
                         **{f"g{j + 1}": g8[i, j] for j in range(g8.shape[1])}})
    d = pd.DataFrame(rows)
    for g in ["0-14", "15-59", "60+"]:
        d[f"s3_{g}"] = d[f"n3_{g}"] / d.population
    return d


def projections(S) -> dict:
    """Central and migration scenarios 2025-2040 for 77 provinces (Bangkok kept as boundary)."""
    D = S.cfg["demography"]
    arr, provs, years = register_array()
    out, comps, metas = {}, [], {}
    for name, m in D["migration_scenarios"].items():
        proj, comp, meta = project(arr, provs, years, S.base_year, S.years[-1], D["ccr_window_central"],
                                   D["cwr_window"], m=float(m), national_control=bool(D["national_control"]))
        agg = aggregate(proj, provs).assign(scenario=name)
        out[name] = agg
        comps.append(comp.assign(scenario=name))
        metas[name] = meta
        if name == "central":
            out["_central_array"] = proj
    tab = pd.concat([v for k, v in out.items() if not k.startswith("_")], ignore_index=True)
    # the base year must reproduce the observed register exactly
    obs = arr[..., list(years).index(S.base_year)].sum((1, 2))
    b = tab[(tab.year == S.base_year) & (tab.scenario == "central")].set_index("prov_code").population
    assert np.allclose(b.reindex(provs).to_numpy(), obs), "baseline age/sex sums do not reproduce the 2025 register"
    return dict(table=tab, components=pd.concat(comps, ignore_index=True), meta=metas,
                central_array=out["_central_array"], provs=provs)


def backtest(S) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Project 2019 -> 2025 with information up to 2019 only and compare with the observed 2025 register."""
    D = S.cfg["demography"]
    arr, provs, years = register_array()
    b0 = int(D["backtest_base"])
    yi = list(years)
    obs25 = arr[..., yi.index(2025)]
    obs_tot = obs25.sum((1, 2))
    obs60 = obs25[:, :, 60:].sum((1, 2)) / obs_tot
    rows = []
    variants = {"hamilton_perry_national_control": dict(national_control=True),
                "hamilton_perry_unconstrained": dict(national_control=False)}
    preds = {}
    for name, kw in variants.items():
        proj, _, _ = project(arr, provs, years, b0, 2025, (2013, b0 - 1), (b0 - 3, b0), m=1.0, **kw)
        P = proj[2025]
        preds[name] = (P.sum((1, 2)), P[:, :, 60:].sum((1, 2)) / P.sum((1, 2)),
                       0.5 * np.abs(P / P.sum((1, 2), keepdims=True) - obs25 / obs_tot[:, None, None]).sum((1, 2)))
    base = arr[..., yi.index(b0)]
    preds["no_change_2019"] = (base.sum((1, 2)), base[:, :, 60:].sum((1, 2)) / base.sum((1, 2)),
                               0.5 * np.abs(base / base.sum((1, 2), keepdims=True) - obs25 / obs_tot[:, None, None]).sum((1, 2)))
    tot_hist = arr[..., : yi.index(b0) + 1].sum((1, 2))
    tt = np.array(years[: yi.index(b0) + 1], float)
    slope = np.polyfit(tt, tot_hist.T, 1)
    lin = slope[0] * 2025 + slope[1]
    preds["linear_trend_totals_2013_2019"] = (lin, np.full(len(provs), np.nan), np.full(len(provs), np.nan))
    k = P4.key().set_index("prov_code")
    bk = int(k[k.is_bangkok].index[0])
    det = []
    for name, (tot, s60, dis) in preds.items():
        ape = 100 * np.abs(tot - obs_tot) / obs_tot
        m76 = provs != bk
        rows.append(dict(method=name, base_year=b0, target_year=2025, provinces=int(m76.sum()),
                         mape_total_pct=float(ape[m76].mean()), medape_total_pct=float(np.median(ape[m76])),
                         max_ape_total_pct=float(ape[m76].max()),
                         national_76_error_pct=float(100 * (tot[m76].sum() / obs_tot[m76].sum() - 1)),
                         mae_share60_pp=float(np.nanmean(100 * np.abs(s60 - obs60)[m76])) if np.isfinite(s60).any() else np.nan,
                         median_dissimilarity_index=float(np.nanmedian(dis[m76])) if np.isfinite(dis).any() else np.nan))
        for i, pc in enumerate(provs):
            if pc == bk:
                continue
            det.append(dict(method=name, prov_code=int(pc), province=k.loc[pc, "province"], observed_2025=obs_tot[i],
                            predicted_2025=tot[i], ape_pct=ape[i], share60_observed=obs60[i], share60_predicted=s60[i]))
    return pd.DataFrame(rows), pd.DataFrame(det)


def entitlement(S, civil: pd.DataFrame) -> pd.DataFrame:
    """Entitlement population = province ratio (NHSO / civil_age) x projected civil population.

    The ratio is an administrative relationship, not extra residents; central holds the 2025
    ratio, low/high use the 2019-2025 minimum/maximum of the province's own ratio."""
    r = P4.registers()
    w = r.pivot_table(index=["year", "prov_code"], columns="register", values="population").reset_index()
    w["ratio"] = w.nhso_rights / w.civil_age
    w = w[w.year.between(2019, S.base_year)]
    g = w.groupby("prov_code").ratio
    rat = pd.DataFrame({"central": w[w.year == S.base_year].set_index("prov_code").ratio,
                        "low": g.min(), "high": g.max(), "mean_2021_2025": w[w.year >= 2021].groupby("prov_code").ratio.mean()})
    out = civil.merge(rat, left_on="prov_code", right_index=True, how="left")
    for v in ["central", "low", "high", "mean_2021_2025"]:
        out[f"pop_entitlement_{v}"] = out.population * out[v]
    return out.drop(columns=["central", "low", "high", "mean_2021_2025"]), rat.reset_index()
