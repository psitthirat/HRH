"""Integrated, cutoff-safe hindcast of the provincial physician stock (next-phase plan §5.2 B–C).

Design and acceptance criteria are declared in config/validation.toml before any run; the run
records that file's SHA-256.  For every origin y only information available at y is used:
HRR stock up to y, HROPS events of fiscal years <= y (hazards re-estimated on that window with the
canonical empirical-Bayes pooling), and civil registers up to y (Hamilton–Perry projected from y).

Models scored on the same province-years:
    persistence, trend (post-2020 points), population_only, stock_flow_unconditional (canonical
    mechanics with recruitment persistence) and stock_flow_conditional (actual recruitment;
    labelled conditional, never presented as a forecast).
Metrics: MAE, RMSE, MAPE, bias (mean signed error) and national error, population-weighted MAPE,
Spearman rank correlation of densities, Jaccard overlap of the lowest-19 density group (convention:
predicted and observed densities both use the OBSERVED target-year population, so the rank metrics
score the stock forecast alone; every model, including persistence, is scored the same way), and 90%
predictive-interval coverage for the stock-flow models; stratified by province size and by
whether the target year is COVID-affected.
"""
from __future__ import annotations

import hashlib
import tomllib

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from chapter4 import config as C4

from . import config as C
from . import demography as D
from . import inputs as I
from . import supply as SU

CFG_PATH = C4.ROOT / "config" / "validation.toml"
COVID_TARGETS = {2020, 2021, 2022}


def load_cfg() -> tuple[dict, str]:
    raw = CFG_PATH.read_bytes()
    return tomllib.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def _population_from(y: int, provs: np.ndarray, last: int) -> pd.DataFrame:
    arr, pv, years = D.register_array()
    proj, _, _ = D.project(arr, pv, years, y, last, (2013, y - 1), (y - 3, y), m=1.0, national_control=True)
    rows = [dict(year=t, prov_code=int(p), population=float(P[i].sum())) for t, P in proj.items() for i, p in enumerate(pv)]
    z = pd.DataFrame(rows)
    return z[z.prov_code.isin(provs)].pivot_table(index="prov_code", columns="year", values="population").reindex(provs)


def run() -> dict:
    cfg, cfg_sha = load_cfg()
    dz = cfg["design"]
    rng = np.random.default_rng(int(dz["seed"]))
    provs = I.provinces().prov_code.to_numpy()
    k = I.provinces().set_index("prov_code")
    stock = I.stock_series().pivot_table(index="prov_code", columns="year", values="headcount").reindex(provs)
    ev = I.flow_events_province()
    rec_all = (ev[(ev.direction == "entry") & (ev.category == "recruitment_hiring")]
               .pivot_table(index="prov_code", columns="fiscal_year", values="events", aggfunc="sum").reindex(provs).fillna(0))
    last = int(dz["last_target_year"])
    obs_pop = I.panel().pivot_table(index="prov_code", columns="year", values="population").reindex(provs)
    preds = []
    for y in dz["origins"]:
        S_y = C.load({"departures.estimation_fy": [max(2017, y - int(dz["hazard_window_years"]) + 1), y]})
        rates = I.flow_rates(S_y)
        deps = SU.Departures(rates, provs)
        dep = deps.central()
        H0 = stock[y].to_numpy(float)
        rw = [f for f in range(y - int(dz["recruitment_window_years"]) + 1, y + 1) if f in rec_all.columns]
        R_hat = rec_all[rw].mean(axis=1).to_numpy(float)
        pop = _population_from(y, provs, last)
        post = [t for t in stock.columns if 2020 <= t <= y]
        slope = np.zeros(len(provs))
        if len(post) >= int(dz["trend_min_points"]):
            X = np.array(post, float)
            slope = np.polyfit(X, stock[post].to_numpy(float).T, 1)[0]
        n = int(dz["simulation_draws"])
        dd = deps.draw(rng, n)
        H_unc, H_con = H0.copy(), H0.copy()
        Hs_unc = np.tile(H0.round(), (n, 1)).astype(np.int64)
        Hs_con = Hs_unc.copy()
        for t in range(y + 1, last + 1):
            h = t - y
            R_con = rec_all[t].to_numpy(float) if t in rec_all.columns else np.full(len(provs), np.nan)
            H_unc = H_unc * (1 - dep["d"] + dep["r"]) + R_hat
            H_con = H_con * (1 - dep["d"] + dep["r"]) + R_con
            L, Rr = SU.draw_events(rng, Hs_unc, dd["d"], dd["r"], dd["shares"])
            Hs_unc = Hs_unc - L + Rr + rng.poisson(np.tile(R_hat, (n, 1)))
            L2, R2 = SU.draw_events(rng, Hs_con, dd["d"], dd["r"], dd["shares"])
            Hs_con = Hs_con - L2 + R2 + np.tile(np.nan_to_num(R_con).round().astype(np.int64), (n, 1))
            lo, hi = dz["interval"]
            models = {
                "persistence": (H0, None, None),
                "trend": (H0 + slope * h, None, None),
                "population_only": (H0 * pop[t].to_numpy(float) / pop[y].to_numpy(float), None, None),
                "stock_flow_unconditional": (H_unc.copy(), np.quantile(Hs_unc, lo, axis=0), np.quantile(Hs_unc, hi, axis=0)),
                "stock_flow_conditional": (H_con.copy(), np.quantile(Hs_con, lo, axis=0), np.quantile(Hs_con, hi, axis=0)),
            }
            for m, (pred, plo, phi) in models.items():
                preds.append(pd.DataFrame(dict(origin=y, target_year=t, horizon=h, model=m, prov_code=provs,
                                               predicted=pred, lower=plo if plo is not None else np.nan,
                                               upper=phi if phi is not None else np.nan,
                                               observed=stock[t].to_numpy(float),
                                               population_observed=obs_pop[t].to_numpy(float),
                                               health_region=k.health_region.reindex(provs).to_numpy())))
    P = pd.concat(preds, ignore_index=True)
    size = pd.qcut(obs_pop[2020], 3, labels=["small", "medium", "large"])
    P["size_tercile"] = P.prov_code.map(size).astype(str)
    P["covid_target"] = P.target_year.isin(COVID_TARGETS)
    P["error"] = P.predicted - P.observed
    P["inside_interval"] = np.where(P.lower.notna(), (P.observed >= P.lower) & (P.observed <= P.upper), np.nan)
    M = metrics(P)
    ACC = acceptance(M, cfg)
    return dict(predictions=P, metrics=M, acceptance=ACC, config=cfg, config_sha256=cfg_sha)


def _scores(g: pd.DataFrame, q: int = 19) -> dict:
    e = g.error.to_numpy(float)
    obs, pred, pop = g.observed.to_numpy(float), g.predicted.to_numpy(float), g.population_observed.to_numpy(float)
    out = dict(n=len(g), mae=float(np.mean(np.abs(e))), rmse=float(np.sqrt(np.mean(e ** 2))),
               mape_pct=float(np.mean(100 * np.abs(e) / obs)), bias_mean=float(np.mean(e)),
               national_error_pct=float(100 * (pred.sum() / obs.sum() - 1)),
               mape_pop_weighted_pct=float(np.average(100 * np.abs(e) / obs, weights=pop)))
    if len(g) >= 2 * q:
        dp, do = pred / pop, obs / pop
        out["spearman_density"] = float(spearmanr(dp, do).statistic)
        lp, lo_ = set(np.argsort(dp, kind="stable")[:q]), set(np.argsort(do, kind="stable")[:q])
        out["jaccard_lowest19"] = len(lp & lo_) / len(lp | lo_)
    cov = g.inside_interval.dropna()
    out["interval_coverage"] = float(cov.mean()) if len(cov) else np.nan
    return out


def metrics(P: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (m, o, h), g in P.groupby(["model", "origin", "horizon"]):
        rows.append(dict(model=m, origin=o, horizon=h, stratum="all", **_scores(g)))
    for (m, h), g in P.groupby(["model", "horizon"]):
        # pooled over origins: per-origin rank statistics averaged, errors pooled
        per = [_scores(z) for _, z in g.groupby("origin")]
        s = _scores(g)
        s["spearman_density"] = float(np.nanmean([x.get("spearman_density", np.nan) for x in per]))
        s["jaccard_lowest19"] = float(np.nanmean([x.get("jaccard_lowest19", np.nan) for x in per]))
        rows.append(dict(model=m, origin="pooled", horizon=h, stratum="all", **s))
        for col in ["size_tercile", "covid_target"]:
            for val, z in g.groupby(col):
                rows.append(dict(model=m, origin="pooled", horizon=h, stratum=f"{col}={val}", **_scores(z)))
    return pd.DataFrame(rows)


def acceptance(M: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    a = cfg["acceptance"]
    pooled = M[(M.origin == "pooled") & (M.stratum == "all")].set_index(["model", "horizon"])
    rows = []
    h = int(a["c1_horizon"])
    mae = {m: pooled.loc[(m, h), "mae"] for m in ["stock_flow_unconditional"] + list(a["c1_must_beat"])}
    ok1 = all(mae["stock_flow_unconditional"] < mae[b] for b in a["c1_must_beat"])
    rows.append(dict(criterion="C1 forecaster status", horizon=h, value=mae["stock_flow_unconditional"],
                     benchmark="; ".join(f"{b} {mae[b]:.2f}" for b in a["c1_must_beat"]), passed=ok1,
                     consequence="describe the engine as a forecaster" if ok1 else
                     "describe the engine as a scenario engine; forecast with the better baseline"))
    cov = M[(M.origin == "pooled") & (M.stratum == "all") & M.model.isin(["stock_flow_unconditional"])].interval_coverage
    c = float(np.average(cov, weights=M[(M.origin == "pooled") & (M.stratum == "all") & M.model.isin(["stock_flow_unconditional"])].n))
    lo, hi = a["c2_coverage_range"]
    rows.append(dict(criterion="C2 interval calibration (unconditional)", horizon="all", value=c, benchmark=f"[{lo}, {hi}]",
                     passed=lo <= c <= hi, consequence="intervals usable as predictive" if lo <= c <= hi else
                     "intervals mis-calibrated; present as scenario ranges only"))
    j = pooled.loc[("stock_flow_unconditional", int(a["c3_horizon"])), "jaccard_lowest19"]
    rows.append(dict(criterion="C3 lowest-19 group stability", horizon=int(a["c3_horizon"]), value=j,
                     benchmark=f">= {a['c3_min_jaccard']}", passed=j >= a["c3_min_jaccard"],
                     consequence="priority group predictable at this horizon" if j >= a["c3_min_jaccard"] else
                     "priority group not stable; re-identify it every year"))
    return pd.DataFrame(rows)
