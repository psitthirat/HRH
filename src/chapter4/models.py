"""Model engines for 4.2.3 and 4.4.

The notebooks declare the specifications (which blocks enter M0-M5, which outcomes, which
samples); this module only implements estimation, validation and standardization so the
same code is used everywhere.

Conventions
-----------
* Outcomes are service rates per person (per fiscal year for AdjRW).
* Supply enters as logs of densities: beds per 1,000, staff per 100,000 population.
* Prevalence enters in percentage points (the HDC files' own unit, checked on ingest).
* Modeled burden (blocks "bod", "bod3") enters as log age-standardized DALYs per 100,000 of
  BOD 2022, a province attribute held fixed across years.
* Age enters as shares (proportions) with 15-59 omitted; shares sum to one.
* Predictive R^2 uses the TRAINING-fold mean as the baseline:
      R2_pred = 1 - sum (y - yhat)^2 / sum (y - ybar_train)^2
  pooled over every repeat and fold.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import least_squares
from scipy.stats import t as student_t
from sklearn.model_selection import KFold

from .panels import AGE_BANDS, BURDEN, BURDEN_GROUPS, DISEASE

from .model_design import design, BED_COL, RATE_COL, TOTAL_COL, PHYS, NURS


def ols(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def fit_positive(X, y, maxiter=200):
    """Positive-mean alternative: Poisson quasi-likelihood (log link) on the rate, equal
    province-year weights.  Accepts non-integer non-negative outcomes."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = sm.GLM(y, X, family=sm.families.Poisson()).fit(maxiter=maxiter)
    return m.params, m.converged


# ----------------------------------------------------------------------------- grouped CV

def province_folds(provs: np.ndarray, n_folds: int, repeats: int, seed: int) -> pd.DataFrame:
    """Fold assignment per repeat: province -> fold, all years of a province together."""
    rows = []
    provs = np.array(sorted(provs))
    for r in range(repeats):
        for f, (_, te) in enumerate(KFold(n_folds, shuffle=True, random_state=seed + r).split(provs)):
            rows += [dict(repeat=r, prov_code=int(p), fold=f) for p in provs[te]]
    return pd.DataFrame(rows)


def cross_validate(d: pd.DataFrame, outcome: str, specs: dict[str, list[str]], folds: pd.DataFrame,
                   age_k: int = 3, positive: bool = False, repeats: int | None = None):
    """Out-of-fold predictions for every spec on identical rows and folds.

    Returns (predictions long table, baseline array [repeats x n])."""
    y = d[RATE_COL[outcome]].to_numpy(float)
    yrs = sorted(d.year.unique())
    Xs = {m: design(d, outcome, b, age_k, years=yrs)[0] for m, b in specs.items()}
    reps = sorted(folds.repeat.unique())[: repeats or None]
    pmap = d.prov_code.to_numpy()
    preds = {m: np.full((len(reps), len(d)), np.nan) for m in specs}
    base = np.full((len(reps), len(d)), np.nan)
    conv_fail = 0
    for ri, r in enumerate(reps):
        fr = folds[folds.repeat == r].set_index("prov_code").fold
        fold_of_row = fr.reindex(pmap).to_numpy()
        for f in sorted(fr.unique()):
            te = fold_of_row == f
            tr = ~te
            base[ri, te] = y[tr].mean()
            for m, X in Xs.items():
                if positive:
                    b, ok = fit_positive(X[tr], y[tr])
                    conv_fail += (not ok)
                    preds[m][ri, te] = np.exp(X[te] @ b)
                else:
                    preds[m][ri, te] = X[te] @ ols(X[tr], y[tr])
    rows = []
    for m, P in preds.items():
        for ri, r in enumerate(reps):
            rows.append(pd.DataFrame({"outcome": outcome, "model": m, "repeat": r,
                                      "prov_code": pmap, "year": d.year.to_numpy(), "observed": y,
                                      "predicted": P[ri], "train_mean": base[ri],
                                      "estimator": "positive_quasi_poisson" if positive else "ols",
                                      "age_groups": age_k}))
    out = pd.concat(rows, ignore_index=True)
    out.attrs["convergence_failures"] = conv_fail
    return out


def score(pred: pd.DataFrame) -> pd.DataFrame:
    """MAE, RMSE, R2_pred (training-mean baseline) and, separately labelled, R2 with the
    test-set mean.  MAPE only because no outcome is zero (checked)."""
    rows = []
    for (o, m, e, k), g in pred.groupby(["outcome", "model", "estimator", "age_groups"]):
        err = g.predicted - g.observed
        assert (g.observed > 0).all(), "MAPE undefined with zero outcomes"
        sse = (err ** 2).sum()
        rows.append(dict(outcome=o, model=m, estimator=e, age_groups=k,
                         n_rows=g[["prov_code", "year"]].drop_duplicates().shape[0],
                         provinces=g.prov_code.nunique(), repeats=g.repeat.nunique(),
                         mae=err.abs().mean(), rmse=np.sqrt((err ** 2).mean()),
                         r2_pred_train_mean=1 - sse / ((g.observed - g.train_mean) ** 2).sum(),
                         r2_testset_mean_reference_only=1 - sse / sum(
                             ((gg.observed - gg.observed.mean()) ** 2).sum()
                             for _, gg in g.groupby("repeat")),
                         mape_pct=100 * (err.abs() / g.observed).mean(),
                         negative_predictions=int((g.predicted <= 0).sum())))
    return pd.DataFrame(rows)


def paired_gains(pred: pd.DataFrame, pairs: list[tuple[str, str]], draws: int, seed: int) -> pd.DataFrame:
    """SSE reduction 100*(SSE_a - SSE_b)/SSE_a with a province-cluster bootstrap interval.

    Each province's squared errors are summed over years and repeats first, so the ten
    repeats of one province are never treated as independent.  The interval is CONDITIONAL
    on the fitted cross-validation predictions (no refitting)."""
    rows = []
    rng = np.random.default_rng(seed)
    for (o, e, k), g in pred.groupby(["outcome", "estimator", "age_groups"]):
        g = g.assign(se=(g.predicted - g.observed) ** 2)
        sse = g.pivot_table(index="prov_code", columns="model", values="se", aggfunc="sum")
        provs = sse.index.to_numpy()
        idx = rng.integers(0, len(provs), (draws, len(provs)))
        for a, b in pairs:
            if a not in sse or b not in sse:
                continue
            ea, eb = sse[a].to_numpy(), sse[b].to_numpy()
            gain = 100 * (ea.sum() - eb.sum()) / ea.sum()
            bs = 100 * (ea[idx].sum(1) - eb[idx].sum(1)) / ea[idx].sum(1)
            rows.append(dict(outcome=o, estimator=e, age_groups=k, baseline=a, model=b,
                             sse_reduction_pct=gain, lo95=np.percentile(bs, 2.5),
                             hi95=np.percentile(bs, 97.5), share_draws_positive=(bs > 0).mean(),
                             interval="province-cluster bootstrap, conditional on CV fits",
                             draws=draws))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- temporal

def temporal_validation(d: pd.DataFrame, outcome: str, specs: dict[str, list[str]], test_year: int,
                        prior_years: list[int]) -> pd.DataFrame:
    """Hold out one year.  Two information sets, labelled:
      conditional_retrospective: the held-out year's own covariates are used;
      forward: covariates carried forward from the last training year (information
               available before the test year).
    Two year-effect rules, applied identically to every model:
      trend: linear time trend fitted on training years, extrapolated;
      last_year_effect: year dummies fitted, the last training year's effect reused.
    A persistence baseline (last observed province rate) is included."""
    y_col = RATE_COL[outcome]
    tr = d[d.year.isin(prior_years)].copy()
    te = d[d.year == test_year].copy()
    last = max(prior_years)
    carry = tr[tr.year == last].set_index("prov_code")
    te_fwd = te.copy()
    fixed = [c for c in te.columns if c.startswith(("s3_", "s6_", "prev_", "log_"))]
    for c in fixed:
        te_fwd[c] = te_fwd.prov_code.map(carry[c])
    rows = []
    ytr = tr[y_col].to_numpy(float)
    for info, T in [("conditional_retrospective", te), ("forward", te_fwd)]:
        T = T[T.prov_code.isin(carry.index)]
        for rule in ["trend", "last_year_effect"]:
            for m, blocks in specs.items():
                if rule == "trend":
                    Xtr, _ = design(tr, outcome, blocks, year_mode="trend", ref_year=last)
                    Xte, _ = design(T, outcome, blocks, year_mode="trend", ref_year=last)
                else:
                    Xtr, names = design(tr, outcome, blocks, years=prior_years)
                    Tl = T.assign(year=last)
                    Xte, _ = design(Tl, outcome, blocks, years=prior_years)
                b = ols(Xtr, ytr)
                yh = Xte @ b
                rows.append(pd.DataFrame({"outcome": outcome, "information": info, "year_rule": rule,
                                          "model": m, "prov_code": T.prov_code.to_numpy(),
                                          "test_year": test_year, "observed": T[y_col].to_numpy(float),
                                          "predicted": yh, "train_mean": ytr.mean()}))
        rows.append(pd.DataFrame({"outcome": outcome, "information": info, "year_rule": "none",
                                  "model": "persistence", "prov_code": T.prov_code.to_numpy(),
                                  "test_year": test_year, "observed": T[y_col].to_numpy(float),
                                  "predicted": T.prov_code.map(carry[y_col]).to_numpy(float),
                                  "train_mean": ytr.mean()}))
    return pd.concat(rows, ignore_index=True)


def score_temporal(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, g in t.groupby(["outcome", "test_year", "information", "year_rule", "model"]):
        e = g.predicted - g.observed
        rows.append(dict(zip(["outcome", "test_year", "information", "year_rule", "model"], keys),
                         n=len(g), mae=e.abs().mean(), rmse=np.sqrt((e ** 2).mean()),
                         r2_pred_train_mean=1 - (e ** 2).sum() / ((g.observed - g.train_mean) ** 2).sum()))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- associations

def cluster_ols(X, y, groups, names):
    """OLS with province-clustered (CR1) standard errors and t(G-1) intervals."""
    b = ols(X, y)
    res = y - X @ b
    XtXi = np.linalg.pinv(X.T @ X)
    G = np.unique(groups)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in G:
        s = X[groups == g].T @ res[groups == g]
        meat += np.outer(s, s)
    n, k = X.shape
    cov = XtXi @ meat @ XtXi * (len(G) / (len(G) - 1)) * ((n - 1) / (n - np.linalg.matrix_rank(X)))
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    crit = student_t.ppf(.975, len(G) - 1)
    return pd.DataFrame({"term": names, "coef": b, "se": se, "lo95": b - crit * se, "hi95": b + crit * se})


def ppml(df: pd.DataFrame, y: str, X_cols: list[str], offset: str | None, fe: list[str],
         cluster: str) -> dict:
    """Poisson pseudo-maximum likelihood (log link) with an optional log offset, dummy fixed
    effects and cluster-robust (province) inference.  Returns coefficients and diagnostics."""
    z = df.dropna(subset=[y] + X_cols + ([offset] if offset else [])).copy()
    parts = [z[X_cols].astype(float)]
    for f in fe:
        parts.append(pd.get_dummies(z[f], prefix=f, drop_first=True, dtype=float))
    X = sm.add_constant(pd.concat(parts, axis=1), has_constant="add")
    off = np.log(z[offset].astype(float)) if offset else None
    # separation check: FE groups whose outcome is all zero cannot be estimated
    sep = [f"{f}={v}" for f in fe for v, g in z.groupby(f) if (g[y] == 0).all()]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod = sm.GLM(z[y].astype(float), X, family=sm.families.Poisson(), offset=off)
        res = mod.fit(cov_type="cluster", cov_kwds={"groups": z[cluster].to_numpy()}, maxiter=300)
    G = z[cluster].nunique()
    crit = student_t.ppf(.975, G - 1)
    tab = pd.DataFrame({"term": X_cols, "coef": res.params[X_cols].to_numpy(),
                        "se": res.bse[X_cols].to_numpy()})
    tab["lo95"] = tab.coef - crit * tab.se
    tab["hi95"] = tab.coef + crit * tab.se
    mu = res.fittedvalues
    pearson = ((z[y] - mu) ** 2 / mu).sum() / (len(z) - X.shape[1])
    return dict(table=tab, n=len(z), clusters=G, converged=bool(res.converged),
                separated_groups=sep, pearson_dispersion=float(pearson), result=res, X=X, data=z)


def within_variation(d: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Share of each variable's variance left after residualizing on province and year
    fixed effects (the actual unbalanced two-way design, not a balanced shortcut)."""
    rows = []
    D = pd.concat([pd.get_dummies(d.prov_code, prefix="p", dtype=float),
                   pd.get_dummies(d.year, prefix="y", drop_first=True, dtype=float)], axis=1).to_numpy()
    for c in cols:
        x = d[c].to_numpy(float)
        r = x - D @ ols(D, x)
        rows.append(dict(variable=c, total_var=np.var(x), within_residual_var=np.var(r),
                         share_remaining_pct=100 * np.var(r) / np.var(x)))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- standardization

def reference_profile(d_ref: pd.DataFrame, outcome: str, gpp_year_rows: pd.DataFrame) -> dict:
    """Pooled 76-province reference in the declared year: log of pooled density (beds per
    1,000; physicians and nurses per 100,000), and log of the population-weighted mean GPP
    level of the lag year implied by the model (GPP of t-1)."""
    pop = d_ref.population.sum()
    bed_total = {"op_moph": "moph_beds", "ip_moph": "moph_beds", "adjrw": "cmx_beds"}[outcome]
    gp = (gpp_year_rows.gpp_lag1 * gpp_year_rows.population).sum() / gpp_year_rows.population.sum()
    return {"log_beds": np.log(1000 * d_ref[bed_total].sum() / pop),
            "log_physicians": np.log(100_000 * d_ref.moph_physicians.sum() / pop),
            "log_nurses": np.log(100_000 * d_ref.moph_professional_nurses.sum() / pop),
            "log_gpp_lag1": np.log(gp)}


def standardized_prediction(d: pd.DataFrame, outcome: str, beta: np.ndarray, names: list[str],
                            ref: dict, ref_year: int, years: list[int]) -> np.ndarray:
    """Full M5 prediction with economic context, supply and year held at the reference,
    and each province-year's own age shares and recorded prevalence."""
    z = d.copy()
    z["year"] = ref_year
    z[BED_COL[outcome]] = ref["log_beds"]
    z[PHYS] = ref["log_physicians"]
    z[NURS] = ref["log_nurses"]
    z["log_gpp_lag1"] = ref["log_gpp_lag1"]
    X, nm = design(z, outcome, ["age", "disease", "gpp", "beds", "physicians", "nurses"], years=years)
    assert nm == names
    return X @ beta


# ----------------------------------------------------------------------------- age weights

def age_mixture(z: pd.DataFrame, outcome: str, k: int, controls: list[str] | None = None, start=None):
    """Age-specific relative rates from province aggregates:

        rate_pt = q_t * sum_a s_pta * r_a * exp(gamma' c_pt),   r_a >= 0, q_first = 1

    q_t are year scale factors profiled out in closed form.  Returns rates, convergence,
    and the share of rates at the zero bound."""
    controls = controls or []
    S = z[[f"s{k}_{g}" for _, _, g in AGE_BANDS[k]]].to_numpy(float)
    yy = z[RATE_COL[outcome]].to_numpy(float)
    scale = yy.mean()
    y = yy / scale
    Z = z[controls].to_numpy(float) if controls else np.zeros((len(z), 0))
    mu, sd = (Z.mean(0), Z.std(0)) if controls else (np.zeros(0), np.ones(0))
    sd = np.where(sd < 1e-10, 1, sd)
    Z = (Z - mu) / sd
    years = sorted(z.year.unique())
    ix = [np.flatnonzero(z.year.to_numpy() == t) for t in years]
    q_n = k + Z.shape[1]

    def resid(par):
        v = (S @ par[:k]) * np.exp(np.clip(Z @ par[k:], -30, 30))
        out = np.empty(len(y))
        for t, j in enumerate(ix):
            vt = v[j]
            q = 1.0 if t == 0 else (vt @ y[j]) / max(vt @ vt, 1e-24)
            out[j] = q * vt - y[j]
        return out

    x0 = np.r_[np.ones(k), np.zeros(Z.shape[1])] if start is None else np.r_[np.maximum(start / scale, 1e-6), np.zeros(Z.shape[1])]
    opt = least_squares(resid, x0, bounds=(np.r_[np.zeros(k), np.full(Z.shape[1], -np.inf)], np.full(q_n, np.inf)),
                        ftol=1e-10, xtol=1e-10, gtol=1e-10, max_nfev=2000)
    r = opt.x[:k] * scale
    return dict(rates=r, success=bool(opt.success), cost=float(2 * opt.cost),
                at_bound=float(np.mean(opt.x[:k] < 1e-8)))


def age_weights(rates: np.ndarray, base_counts: np.ndarray) -> np.ndarray:
    """Weights relative to the base-year population mean rate: w_a = r_a / (sum_a N_a r_a / N)."""
    mean = (base_counts / base_counts.sum()) @ rates
    return rates / mean if mean > 0 else np.full_like(rates, np.nan)
