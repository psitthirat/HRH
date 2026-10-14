"""Uncertainty (paired paths) and the common comparison of plans.

stage_uncertainty
    500 paired paths (config evaluation.main_simulation_runs) share departure-parameter draws,
    population-error paths, one M5 coefficient draw per path and common random numbers for the
    event draws.  Three objects are kept apart:
      fixed      the announced central schedules evaluated with the common minimal recourse rule
      adaptive   annual replanning on the first `adaptive_simulation_runs` paths (information
                 up to the decision date only)
      foresight  a perfect-foresight optimisation on the same paths (optimistic bound only)

stage_compare
    cross-evaluation of every plan against every denominator, regret, destination switches,
    practical-difference verdicts, binding constraints, feedback diagnostics, and the tables of
    the Thai report.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from . import allocation as AL
from . import evaluation as EV
from . import pipeline as PL
from . import responsibilities as R
from . import simulation as SIM
from .reporting import Registry

PRINCIPAL = ["P-R", "P-RT", "S-R", "S-RT", "N-R", "N-RT"]
FAM_LABEL = {"P": "ประชากร", "S": "บริการที่เกิดขึ้น", "N": "บริการคาดหมายมาตรฐาน M5", "N-STD": "บริการคาดหมายมาตรฐาน M5",
             "P_ent": "ประชากรทะเบียนสิทธิ", "N-FB": "M5 ป้อนกลับ", "status_quo": "สัดส่วนรับเข้าในอดีต",
             "B": "DALY คาดหมาย", "B-yld": "YLD คาดหมาย"}
CRIT = ["P", "Pent", "S", "N", "B"]
CRIT_COL = {"P": "D_P", "Pent": "D_Pent", "S": "D_S", "N": "D_N", "B": "D_B"}


def _results(S):
    res = PL.load_plan_results(S)
    return {r["job_id"]: r for r in res}


# ----------------------------------------------------------------------------- uncertainty

from .uncertainty import path_targets, path_metrics


def stage_uncertainty(S, n=None, n_adapt=None, workers=None) -> dict:
    t0 = time.time()
    Rg = Registry(S, "5_3")
    ev = S.cfg["evaluation"]
    n = int(n or ev["main_simulation_runs"])
    n_adapt = int(n_adapt if n_adapt is not None else ev["adaptive_simulation_runs"])
    ctx = PL.context(json.dumps(S.overrides, sort_keys=True), "{}")
    res = _results(S)
    pbt = pd.read_csv(S.dirs()["validation"] / "T5_POP_BACKTEST.csv", encoding="utf-8-sig").set_index("method")
    mape6 = float(pbt.loc["hamilton_perry_national_control", "mape_total_pct"]) / 100
    nat6 = abs(float(pbt.loc["hamilton_perry_national_control", "national_76_error_pct"])) / 100
    sig_p = mape6 * np.sqrt(np.pi / 2) / np.sqrt(6)
    sig_n = nat6 / np.sqrt(6)
    draws = SIM.make_draws(ctx, n, S.seed + 101, sig_p, sig_n)
    targets = {c: path_targets(ctx, draws, c) for c in ["P", "S", "N", "B"]}
    own = {"P": "P", "S": "S", "N": "N", "SQ": "P", "NFB1": "N", "B": "B"}
    rows, prov_rows = [], []
    plans = [p for p in PRINCIPAL + ["SQ-C", "NFB1-R", "B-R", "B-RT"] if p in res and res[p].get("x") is not None]
    for pid in plans:
        r = res[pid]
        spec = SIM.PlanSpec(**r["spec"])
        pb = SIM.make_problem(ctx, spec, r["T"])
        routes = r["routes"] if r.get("routes") is not None else pd.DataFrame(columns=["year_ce"])
        sim = SIM.simulate_fixed(ctx, pb, r["x"], r["zin"], r["zout"], routes, draws)
        H = sim["H"].astype(float)
        for c in ["P", "S", "N", "B"]:
            T, invalid = targets[c]
            m = path_metrics(H, T, ctx.region)
            df = pd.DataFrame(m).assign(plan_id=pid, mode="fixed_schedule", criterion=c, path=np.arange(n),
                                        m5_draw_invalid=invalid if c == "N" else False)
            rows.append(df)
        extra = pd.DataFrame(dict(plan_id=pid, mode="fixed_schedule", path=np.arange(n),
                                  cancelled_transfers=sim["cancelled"].sum(1),
                                  cap_breach_province_years=sim["cap_breach"].sum((1, 2)),
                                  protection_breach_province_years=sim["protection_breach"].sum((1, 2)),
                                  any_cap_breach=sim["cap_breach"].any((1, 2))))
        prov_rows.append(extra)
        Rg.claim(f"c53_capbreach_share_{pid}", 100 * sim["cap_breach"].mean(), "{:.1f}", "% ของจังหวัด-ปี")
        Rg.claim(f"c53_cancelled_mean_{pid}", sim["cancelled"].sum(1).mean(), "{:.1f}", "ครั้งต่อเส้นทาง")
        np.save(S.dirs()["cache"] / f"sim_fixed_{pid}.npy", sim["H"][:, -1].astype(np.int32))
    # adaptive replanning and perfect-foresight bound on the first n_adapt paths
    ad_rows = []
    if n_adapt > 0:
        jobs = []
        a = S.cfg["allocation"]
        prob_kw = dict(floor=int(a["universal_new_appointment_floor"]), cap_mode=a["cap_mode"],
                       cap=float(a["cap_fraction_of_opening_stock"]), reentry_consumes=bool(a["reentry_consumes_onboarding"]),
                       tangent_step=float(a["tangent_step"]), mip_rel_gap=float(a["mip_rel_gap"]),
                       time_limit=float(a["time_limit_s"]))
        dep = ctx.departures
        post_b = dep.b["resignation"]
        post_a = sum(dep.h[c] for c in SU_EXIT) * post_b
        re_b = post_b
        re_a = sum(dep.h[c] for c in ["reinstatement", "transfer_in"]) * re_b
        for fam in ["P", "S", "N"]:
            Tc = res[f"{fam}-R"]["T"]
            for k in range(n_adapt):
                jobs.append((dict(fam=fam, k=k, kind="adaptive"),
                             (k, dict(H0=ctx.H0, provs=ctx.provs), Tc, "common_total", draws.d[k], draws.r[k],
                              draws.U_exit[k], draws.U_re[k], draws.pop_mult[k], post_a, post_b, re_a, re_b,
                              ctx.pool, prob_kw)))
        workers = workers or max(1, min(9, (os.cpu_count() or 2) - 1))
        with ProcessPoolExecutor(max_workers=workers) as ex:
            outs = list(ex.map(SIM.simulate_adaptive_path, [j[1] for j in jobs]))
            fore = list(ex.map(_foresight_path, [(j[0]["fam"], j[1]) for j in jobs]))
        for (meta, _), o, f in zip(jobs, outs, fore):
            fam, k = meta["fam"], meta["k"]
            T, invalid = targets[fam]
            for mode, out in [("adaptive_replanning", o), ("perfect_foresight_bound", f)]:
                if out["status"] != "solved":
                    ad_rows.append(dict(plan_id=f"{fam}-R", mode=mode, path=k, criterion=fam, status=out["status"]))
                    continue
                m = path_metrics(out["H"][None].astype(float), T[k:k + 1], ctx.region)
                ad_rows.append(dict(plan_id=f"{fam}-R", mode=mode, path=k, criterion=fam, status="solved",
                                    **{kk: float(v[0]) for kk, v in m.items()}))
    fixed = pd.concat(rows, ignore_index=True)
    adapt = pd.DataFrame(ad_rows)
    ops = pd.concat(prov_rows, ignore_index=True)
    fixed.to_parquet(S.dirs()["plans"] / "chapter5_simulation_paths_fixed.parquet", index=False)
    if len(adapt):
        adapt.to_parquet(S.dirs()["plans"] / "chapter5_simulation_paths_adaptive.parquet", index=False)
    ops.to_parquet(S.dirs()["plans"] / "chapter5_simulation_operations.parquet", index=False)
    # summaries
    q = lambda s: pd.Series({"mean": s.mean(), "p05": s.quantile(.05), "p50": s.median(), "p95": s.quantile(.95)})
    met = ["national_attainment_2040", "bottom_quartile_2040", "worst_attainment_2040", "gini_2040", "cumulative_j",
           "stock_2040"]
    summ = []
    for (pid, mode, c), g in fixed.groupby(["plan_id", "mode", "criterion"]):
        g = g[~g.m5_draw_invalid]
        for mm in met:
            summ.append(dict(plan_id=pid, mode=mode, criterion=c, metric=mm, **q(g[mm]).to_dict(), n_valid=len(g)))
    if len(adapt):
        ok = adapt[adapt.status == "solved"]
        for (pid, mode, c), g in ok.groupby(["plan_id", "mode", "criterion"]):
            for mm in met:
                summ.append(dict(plan_id=pid, mode=mode, criterion=c, metric=mm, **q(g[mm]).to_dict(), n_valid=len(g)))
        # paired fixed rows on the same paths
        for fam in ["P", "S", "N"]:
            g = fixed[(fixed.plan_id == f"{fam}-R") & (fixed.criterion == fam) & (fixed.path < n_adapt)]
            for mm in met:
                summ.append(dict(plan_id=f"{fam}-R", mode="fixed_schedule_same_paths", criterion=fam, metric=mm,
                                 **q(g[mm]).to_dict(), n_valid=len(g)))
    SU_ = pd.DataFrame(summ)
    Rg.table("T5_UNCERTAINTY_SUMMARY", SU_, "ผลภายใต้ความไม่แน่นอน (เส้นทางจับคู่): แผนตายตัว การปรับแผนรายปี และขอบเขตรู้อนาคต", main=True)
    opsum = ops.groupby("plan_id").agg(cancelled_mean=("cancelled_transfers", "mean"),
                                       cap_breach_province_years_mean=("cap_breach_province_years", "mean"),
                                       share_paths_any_cap_breach=("any_cap_breach", "mean"),
                                       protection_breach_mean=("protection_breach_province_years", "mean")).reset_index()
    Rg.table("T5_UNCERTAINTY_OPERATIONS", opsum, "การยกเลิกการโยกย้ายและการเกินเพดานที่เกิดขึ้นจริงในแผนตายตัว (ไม่มีการแก้ไขด้วยการสรรหาฉุกเฉิน)")
    # probability-type and paired-difference statements
    piv = fixed[fixed.criterion == "P"].pivot_table(index="path", columns="plan_id", values="bottom_quartile_2040")
    diffs = []
    for a_, b_ in [("N-R", "P-R"), ("S-R", "P-R"), ("P-RT", "P-R"), ("SQ-C", "P-R"), ("B-R", "P-R")]:
        if a_ in piv and b_ in piv:
            d = piv[a_] - piv[b_]
            half = d.iloc[: n // 2]
            batches = np.array_split(d.to_numpy(), 10)
            se = np.std([b.mean() for b in batches], ddof=1) / np.sqrt(10)
            diffs.append(dict(comparison=f"{a_} − {b_}", criterion="P (bottom-quartile attainment 2040)",
                              mean=d.mean(), mean_first_half=half.mean(), batch_se=se, p05=d.quantile(.05),
                              p95=d.quantile(.95), share_positive=(d > 0).mean(), n=len(d)))
    DF = pd.DataFrame(diffs)
    Rg.table("T5_PAIRED_DIFFERENCES", DF, "ความต่างแบบจับคู่ระหว่างแผน และเสถียรภาพของ Monte Carlo", folder="validation")
    Rg.claim("c53_n_paths", n, "int", "เส้นทาง")
    for c_ in sorted(SU_.criterion.unique()):          # valid paths of the fixed schedules (all paths)
        z_ = SU_[(SU_.criterion == c_) & (SU_["mode"] == "fixed_schedule")]
        Rg.claim(f"c53_n_valid_{c_}", int(z_.n_valid.min()) if len(z_) else np.nan, "int", "เส้นทาง")
    Rg.claim("c53_n_adapt", n_adapt, "int", "เส้นทาง")
    Rg.claim("c53_sigma_prov", 100 * sig_p, "{:.2f}", "% ต่อปี")
    Rg.claim("c53_m5_invalid_share", 100 * float(targets["N"][1].mean()), "{:.1f}", "%")
    f0 = SU_[(SU_["mode"] == "fixed_schedule")]
    for pid in plans:
        c = own.get(pid.split("-")[0], "P")
        z = f0[(f0.plan_id == pid) & (f0.criterion == c)].set_index("metric")
        for mm, lab in [("national_attainment_2040", "nat"), ("bottom_quartile_2040", "bq")]:
            for qq in ["p05", "p50", "p95"]:
                Rg.claim(f"c53_{lab}_{qq}_{pid}", z.loc[mm, qq], "{:.3f}", "")
    if len(adapt):
        for fam in ["P", "S", "N"]:
            for mode in ["adaptive_replanning", "perfect_foresight_bound", "fixed_schedule_same_paths"]:
                z = SU_[(SU_.plan_id == f"{fam}-R") & (SU_["mode"] == mode) & (SU_.criterion == fam)].set_index("metric")
                if len(z):
                    Rg.claim(f"c53_{mode}_j_{fam}", z.loc["cumulative_j", "mean"], "{:.3f}", "")
                    Rg.claim(f"c53_{mode}_bq_{fam}", z.loc["bottom_quartile_2040", "mean"], "{:.3f}", "")
        Rg.claim("c53_adapt_failed", float((adapt.status != "solved").sum()), "{:.0f}", "เส้นทาง")
    for rr in DF.itertuples():
        tag = rr.comparison.replace(" − ", "_minus_").replace("-", "")
        Rg.claim(f"c53_diff_{tag}_mean", rr.mean, "{:.4f}", "")
        Rg.claim(f"c53_diff_{tag}_se", rr.batch_se, "{:.4f}", "")
        Rg.claim(f"c53_diff_{tag}_pos", 100 * rr.share_positive, "{:.0f}", "%")
    man = Rg.finalize(dict(n_paths=n, n_adapt=n_adapt, seconds_total=time.time() - t0))
    return dict(fixed=fixed, adaptive=adapt, summary=SU_, manifest=man)


SU_EXIT = ["resignation", "retirement", "transfer_out", "death", "disciplinary"]


def _foresight_path(arg):
    """Perfect-foresight optimistic bound: the plan optimised knowing the path's true hazards and
    population, then realised with the same random numbers."""
    fam, a = arg
    (k, cs, Tc, experiment, d_true, r_true, U1, U2, pop_mult, post_a, post_b, re_a, re_b, pool, prob_kw) = a
    from scipy import stats
    Tp = Tc * pop_mult
    Tp = Tp / Tp.sum(1, keepdims=True) * Tp.sum(1, keepdims=True)
    pb = AL.Problem(provs=cs["provs"], years=list(range(Tc.shape[0])), H0=cs["H0"], T=Tp, d=d_true, r=r_true, A=pool,
                    stages=("shortfall",), **prob_kw)
    sol = AL.solve(pb)
    if sol.status != "solved":
        return dict(status=sol.status)
    Hp = cs["H0"].round().astype(np.int64)
    H = np.zeros_like(sol.x, dtype=np.int64)
    for t in range(Tc.shape[0]):
        L = stats.binom.ppf(U1[t], Hp, d_true).astype(np.int64)
        R_ = stats.poisson.ppf(U2[t], np.maximum(r_true * Hp, 1e-12)).astype(np.int64)
        H[t] = Hp - L + R_ + sol.x[t]
        Hp = H[t]
    return dict(status="solved", H=H)


# ----------------------------------------------------------------------------- comparison

def plan_index(res: dict) -> pd.DataFrame:
    rows = []
    for pid, r in res.items():
        sp = r["spec"]
        st = r.get("stages") or []
        rows.append(dict(plan_id=pid, kind=r["kind"], group=r["group"], family=sp["family"], denominator=sp["index_col"],
                         mobility=sp["mobility"], experiment=sp["experiment"], feedback=sp["feedback"],
                         variant=sp["variant"], status=r.get("status"), error=r.get("error", ""),
                         cap_mode=r.get("cap_mode", ""), all_constraints_ok=(r.get("check") or {}).get("all_ok"),
                         objective_exact=r.get("objective_exact"), imbalance=r.get("imbalance"),
                         transfer_events=int(r["zout"].sum()) if r.get("zout") is not None else np.nan,
                         max_mip_gap=max([s_.get("mip_gap", 0) or 0 for s_ in st if s_["stage"] == "shortfall"], default=np.nan),
                         secondary_stage_gap=max([s_.get("mip_gap", 0) or 0 for s_ in st if s_["stage"] != "shortfall"], default=np.nan),
                         incumbent_adopted=bool((r.get("diagnostics") or {}).get("incumbent_adopted", False)),
                         incumbent_adopted_distribution=bool((r.get("diagnostics") or {}).get("incumbent_adopted_distribution", False)),
                         stage_outcomes="; ".join(f"{s_['stage']}: {s_.get('outcome', s_.get('status'))}" for s_ in st),
                         seconds=r.get("seconds"), notes=sp["notes"],
                         cap_binding_share=(r.get("binding") or {}).get("cap"),
                         floor_binding_share=(r.get("binding") or {}).get("floor"),
                         churn_netted=(r.get("diagnostics") or {}).get("churn_netted_events"),
                         stock_2040=float(r["H"][-1].sum()) if r.get("H") is not None else np.nan))
    return pd.DataFrame(rows)


def response_eval(ctx, H, lam):
    """Composite resource-responsive minutes per province-year under the common response
    mechanism (annual-average exposure) and the implied physician workload."""
    S = ctx.S
    Hp = np.vstack([ctx.H0[None], H[:-1]])
    mins = np.zeros_like(H)
    for t, y in enumerate(S.years):
        mins[t], _ = ctx.fb.response_minutes(y, 0.5 * (Hp[t] + H[t]), lam)
    return mins


def stage_compare(S) -> dict:
    t0 = time.time()
    Rg = Registry(S, "5_4")
    ctx = PL.context(json.dumps(S.overrides, sort_keys=True), "{}")
    res = _results(S)
    years = S.years
    k = ctx.k
    PIDX = plan_index(res)
    Rg.table("T5_PLAN_INDEX", PIDX, "ทะเบียนแผนทั้งหมด สถานะ ตัวแก้ปัญหา และการตรวจข้อจำกัด", folder="validation")
    # ---------------- ledgers, national balance, routes
    led = [r["ledger"] for r in res.values() if r.get("ledger") is not None]
    LED = pd.concat(led, ignore_index=True)
    LED.to_parquet(S.dirs()["plans"] / "chapter5_provincial_annual_plans_all.parquet", index=False)
    poolrows = []
    for pid, r in res.items():
        if r.get("pool") is not None:
            poolrows += [dict(plan_id=pid, year_ce=y, available=float(a_)) for y, a_ in zip(years, r["pool"])]
    NB = SIM.national_balance(LED, pd.DataFrame(poolrows))
    assert NB.reconciliation_difference.abs().max() < 1e-6
    NB.to_csv(S.dirs()["plans"] / "chapter5_national_annual_balance_all.csv", index=False, encoding="utf-8-sig")
    routes = [r["routes"] for r in res.values() if r.get("routes") is not None]
    RT = pd.concat(routes, ignore_index=True) if routes else pd.DataFrame()
    # route reconciliation with the ledgers
    if len(RT):
        a_ = RT.groupby(["plan_id", "year_ce", "origin_code"]).transfer_events.sum()
        b_ = LED.set_index(["plan_id", "year_ce", "prov_code"]).transfers_out_planned
        b_ = b_[b_ > 0]
        a_.index.names = b_.index.names
        assert np.allclose(a_.sort_index().to_numpy(), b_.reindex(a_.index).to_numpy()), "routes do not reconcile with outflows"
        # reciprocal route check over the horizon
        pairs = set(zip(RT.plan_id, RT.origin_code, RT.destination_code))
        recip = sum((p, d, o) in pairs for p, o, d in pairs)
        Rg.claim("c54_reciprocal_route_pairs", recip / 2, "{:.0f}", "คู่")
    RT.to_csv(S.dirs()["plans"] / "chapter5_transfer_routes_all.csv", index=False, encoding="utf-8-sig")
    # ---------------- evaluation targets (central context)
    ET = {exp: PL.eval_targets(ctx, exp) for exp in ["common_total", "fixed_base_conversion"]}
    popm = ctx.idx[ctx.idx.year.isin(years)].sort_values(["year", "prov_code"]).population.to_numpy().reshape(len(years), -1)
    central_ctx_plans = [pid for pid, r in res.items() if r.get("H") is not None and
                         (r["group"] in ("principal", "variant") or pid.endswith(("|net", "|tau0.05", "|greedy")))
                         and not res[pid]["spec"]["variant"].startswith(("migration", "weights", "inpatient"))]
    traj = []
    for pid in central_ctx_plans:
        H = res[pid]["H"]
        for exp, et in ET.items():
            for c in CRIT:
                traj.append(EV.trajectory_metrics(pid, f"{c}|{exp}", H, et[c], years, ctx.region, popm))
        traj.append(EV.trajectory_metrics(pid, "own", H, res[pid]["T"], years, ctx.region, popm))
    TR = pd.concat(traj, ignore_index=True)
    Rg.table("T5_TRAJECTORY_METRICS", TR, "ความเพียงพอ ความขาดแคลน และความเหลื่อมล้ำรายปีของทุกแผน ภายใต้ทุกเกณฑ์การประเมิน", parquet=True)
    # response-based evaluation (lambda 0.5 and 1)
    resp_rows = []
    for pid in [p for p in central_ctx_plans if res[p]["group"] in ("principal", "variant")]:
        H = res[pid]["H"]
        for lam in [0.5, 1.0]:
            mins = response_eval(ctx, H, lam)
            Tresp = k * ctx.idx.scale_S.iloc[0] * mins
            TrA = Tresp / Tresp.sum(1, keepdims=True) * (k * popm.sum(1, keepdims=True))
            wl = mins / H
            for t, y in enumerate(years):
                resp_rows.append(dict(plan_id=pid, lam=lam, year_ce=y, responsive_minutes=mins[t].sum(),
                                      national_workload_min_per_physician=mins[t].sum() / H[t].sum(),
                                      workload_p90_p10=np.quantile(wl[t], .9) / np.quantile(wl[t], .1),
                                      attainment_resp_B=H[t].sum() / Tresp[t].sum(),
                                      gini_resp_A=EV.gini(H[t] / TrA[t], TrA[t]),
                                      bottom_quartile_resp_A=EV.year_metrics(H[t], TrA[t], ctx.region, popm[t])["bottom_quartile_attainment"]))
    RESP = pd.DataFrame(resp_rows)
    Rg.table("T5_RESPONSE_EVALUATION", RESP, "บริการที่ตอบสนองต่อทรัพยากร (กลไก M5 เดียวกันทุกแผน) และภาระงานต่อแพทย์")
    # ---------------- cross-evaluation matrix (Experiment A targets; 2040 and cumulative)
    main_plans = [p for p in PRINCIPAL + ["SQ-C", "SQ-HIST", "Pent-R", "Pent-RT", "NFB0-R", "NFB0.5-R", "NFB1-R",
                                         "S-R|B", "N-R|B", "NFB1-R|B", "P-R|net", "S-R|net", "N-R|net", "P-RT|net",
                                         "S-RT|net", "N-RT|net", "B-R", "B-RT", "B-R|net", "B-RT|net", "B-R|yld",
                                         "B-R|B", "B-R|asr"]
                  if p in central_ctx_plans]
    X = []
    for pid in main_plans:
        for c in CRIT:
            z = TR[(TR.plan_id == pid) & (TR.criterion == f"{c}|common_total")]
            l = z[z.year_ce == years[-1]].iloc[0]
            X.append(dict(plan_id=pid, criterion=c, cumulative_j=z.j_short.sum(), cumulative_shortfall=z.shortfall_sum.sum(),
                          national_attainment_2040=l.national_attainment, bottom_quartile_2040=l.bottom_quartile_attainment,
                          worst_attainment_2040=l.worst_attainment, gini_2040=l.gini, theil_2040=l.theil,
                          p90_p10_2040=l.p90_p10, theil_between_share_2040=l.theil_between_share,
                          gap_spatial_2040=l.gap_spatial, gap_national_2040=l.gap_national,
                          provinces_meeting_2040=l.provinces_meeting))
        for lam in [0.5, 1.0]:
            z = RESP[(RESP.plan_id == pid) & (RESP.lam == lam)]
            if len(z):
                l = z[z.year_ce == years[-1]].iloc[0]
                X.append(dict(plan_id=pid, criterion=f"resp{lam:g}", bottom_quartile_2040=l.bottom_quartile_resp_A,
                              gini_2040=l.gini_resp_A, workload_2040=l.national_workload_min_per_physician,
                              workload_p90_p10_2040=l.workload_p90_p10, national_attainment_2040=l.attainment_resp_B))
    XE = pd.DataFrame(X)
    # best plan per criterion: every comparable Experiment-A gross-arrival plan, including the B family
    base_set = XE[XE.plan_id.isin(PRINCIPAL + ["B-R", "B-RT"])]
    best = base_set.groupby("criterion").cumulative_j.min()
    XE["regret_j_pct"] = 100 * (XE.cumulative_j / XE.criterion.map(best) - 1)
    bestbq = base_set.groupby("criterion").bottom_quartile_2040.max()
    XE["regret_bottom_quartile_pp"] = 100 * (XE.criterion.map(bestbq) - XE.bottom_quartile_2040)
    Rg.table("T5_CROSS_EVALUATION_LONG", XE, "การประเมินไขว้: ทุกแผนภายใต้ทุกเกณฑ์ (เป้าหมายรวมร่วม, 2583 และสะสม 15 ปี)")
    view = XE[XE.plan_id.isin(PRINCIPAL + ["SQ-C", "NFB1-R", "B-R"]) & XE.criterion.isin(CRIT + ["resp1"])].copy()
    view["cell"] = np.where(view.criterion.str.startswith("resp"),
                            view.bottom_quartile_2040.map("{:.3f}".format) + " (Gini " + view.gini_2040.map("{:.3f}".format) + ")",
                            view.bottom_quartile_2040.map("{:.3f}".format) + " / " + view.regret_j_pct.map("{:+.1f}%".format))
    T56 = view.pivot(index="plan_id", columns="criterion", values="cell").reindex(
        [p for p in PRINCIPAL + ["SQ-C", "NFB1-R", "B-R"] if p in view.plan_id.values]).reset_index()
    # Pivot sorts criterion codes (N before P); label by code, never by column position.
    col_th = {"plan_id": "แผน", "P": "ประชากรทะเบียนราษฎร", "N": "บริการคาดหมายมาตรฐาน M5", "Pent": "ประชากรทะเบียนสิทธิ",
              "S": "บริการที่เกิดขึ้น", "B": "DALY คาดหมาย", "resp1": "บริการตอบสนองทรัพยากร λ=1"}
    order = [c for c in ["plan_id", "N", "P", "Pent", "S", "B", "resp1"] if c in T56.columns]
    T56 = T56[order].rename(columns=col_th)
    Rg.table("T56_CROSS_EVALUATION", T56, "การประเมินไขว้ของแผนหลัก: ความเพียงพอของจังหวัดกลุ่มล่างสุด 19 จังหวัด ปี 2583 / ส่วนเกินของ J สะสมเทียบแผนที่ดีที่สุดภายใต้เกณฑ์นั้น (เป้าหมายรวมร่วม 1:1,000)", main=True)
    # ---------------- switches between families
    SW, PD, PROVD = [], [], []
    thr = S.cfg["evaluation"]
    pairs = [("P-R", "S-R"), ("P-R", "N-R"), ("S-R", "N-R"), ("P-RT", "S-RT"), ("P-RT", "N-RT"), ("S-RT", "N-RT"),
             ("P-R", "P-RT"), ("S-R", "S-RT"), ("N-R", "N-RT"), ("P-R", "SQ-C"), ("P-R", "Pent-R"), ("N-R", "NFB1-R"),
             ("N-R", "NFB0.5-R"), ("N-R", "NFB0-R"), ("S-R|B", "S-R"), ("N-R|B", "N-R"), ("P-R", "P-R|greedy"),
             ("P-R", "P-R|rolling"), ("P-R", "P-R|tangent_fine"), ("P-R|net", "P-RT|net"), ("P-R", "P-R|nofloor"),
             ("S-R", "S-R|nofloor"), ("N-R", "N-R|nofloor"), ("N-R", "N-R|morb_trend"), ("N-R", "N-R|age_held"),
             ("N-R", "N-R|positive"), ("P-R", "P-R|maximin"), ("P-R", "P-R|depnat"), ("P-R", "B-R"), ("S-R", "B-R"),
             ("N-R", "B-R"), ("B-R", "B-RT"), ("B-R", "B-R|yld"), ("B-R", "B-R|asr"), ("B-R|net", "B-RT|net"), ("P-R|net", "B-R|net"),
             ("B-R|B", "B-R"), ("P-RT", "P-RT|tau0.05"), ("S-RT", "S-RT|tau0.05"), ("N-RT", "N-RT|tau0.05")]
    # near-optimal alternatives of the same problem: the solver-indeterminacy benchmark (plan M-6, final check)
    noise_candidates = [("P-R", "P-R|greedy"), ("P-R", "P-R|rolling"), ("P-R", "P-R|tangent_fine"), ("P-R", "P-RT"),
                        ("S-R", "S-RT"), ("N-R", "N-RT"), ("P-RT", "P-RT|tau0.05"), ("S-RT", "S-RT|tau0.05"),
                        ("N-RT", "N-RT|tau0.05")]
    for m_, n_ in pairs:
        if m_ not in res or n_ not in res or res[m_].get("x") is None or res[n_].get("x") is None:
            continue
        xm, xn = res[m_]["x"], res[n_]["x"]
        um, un = res[m_]["pool"] - xm.sum(1), res[n_]["pool"] - xn.sum(1)
        sw, pct = EV.switches(xm, xn, um, un, res[m_]["pool"])
        for t, y in enumerate(years):
            SW.append(dict(plan_a=m_, plan_b=n_, year_ce=y, year_be=y + 543, switched=sw[t], switched_pct=pct[t]))
        cm, cn = xm.sum(0), xn.sum(0)
        Hm, Hn = res[m_]["H"][-1], res[n_]["H"][-1]
        # common criterion for the comparison: P (population, Experiment A)
        Tc = ET["common_total"]["P"]
        am = res[m_]["H"] / Tc
        low = np.argsort(am[-1])[: int(thr["bottom_quartile"])]
        loss = 100 * ((Hn[low] - Hm[low]) / Hm[low]).min()
        verdict = {}
        for c in CRIT:
            zm = TR[(TR.plan_id == m_) & (TR.criterion == f"{c}|common_total")].shortfall_sum.sum() if m_ in central_ctx_plans else np.nan
            zn = TR[(TR.plan_id == n_) & (TR.criterion == f"{c}|common_total")].shortfall_sum.sum() if n_ in central_ctx_plans else np.nan
            verdict[c] = 100 * abs(zn / zm - 1) if zm == zm and zn == zn and zm > 0 else np.nan
        mx = np.nanmax(list(verdict.values())) if any(v == v for v in verdict.values()) else np.nan
        similar = (pct.mean() < thr["switch_threshold_pct"]) and (mx == mx and mx < thr["cumulative_shortfall_threshold_pct"]) \
            and (loss > -thr["worst_province_loss_threshold_pct"])
        PD.append(dict(plan_a=m_, plan_b=n_, mean_annual_switched=sw.mean(), mean_annual_switched_pct=pct.mean(),
                       max_annual_switched_pct=pct.max(), cumulative_switched=sw.sum(),
                       max_cum_receipts_diff=int(np.abs(cn - cm).max()),
                       province_max_cum_diff=ctx.names[ctx.provs[int(np.argmax(np.abs(cn - cm)))]],
                       max_abs_2040_stock_diff=float(np.abs(Hn - Hm).max()),
                       max_cumulative_shortfall_diff_pct=mx,
                       **{f"cum_shortfall_diff_pct_{c}": v for c, v in verdict.items()},
                       worst_bottom_quartile_loss_pct=loss,
                       practically_similar=bool(similar),
                       criteria=f"switch<{thr['switch_threshold_pct']}%/yr; cumulative shortfall diff<{thr['cumulative_shortfall_threshold_pct']}% "
                                f"under every denominator; no bottom-quartile province loses >{thr['worst_province_loss_threshold_pct']}% of its 2040 stock"))
        for i, p in enumerate(ctx.provs):
            PROVD.append(dict(plan_a=m_, plan_b=n_, prov_code=int(p), province=ctx.names[p], cum_receipts_a=int(cm[i]),
                              cum_receipts_b=int(cn[i]), diff=int(cn[i] - cm[i]),
                              first_year_diff=int(xn[0, i] - xm[0, i]),
                              max_annual_abs_diff=int(np.abs(xn[:, i] - xm[:, i]).max()),
                              stock2040_a=Hm[i], stock2040_b=Hn[i]))
    SWT = pd.DataFrame(SW); PDT = pd.DataFrame(PD); PRD = pd.DataFrame(PROVD)
    tol = 100 * float(S.cfg["allocation"]["lexicographic_rel_tol"])
    dJ = lambda a_, b_: 100 * abs(res[b_]["objective_exact"] / res[a_]["objective_exact"] - 1) \
        if res.get(a_, {}).get("objective_exact") and res.get(b_, {}).get("objective_exact") else np.nan
    PDT["objective_diff_pct"] = [dJ(a_, b_) for a_, b_ in zip(PDT.plan_a, PDT.plan_b)]
    PDT["near_optimal_alternative"] = [(a_, b_) in noise_candidates and d_ == d_ and d_ <= tol and sw_ > 0
                                       for a_, b_, d_, sw_ in zip(PDT.plan_a, PDT.plan_b, PDT.objective_diff_pct, PDT.mean_annual_switched)]
    noise = PDT[PDT.near_optimal_alternative]
    noise_pct = float(noise.mean_annual_switched_pct.max()) if len(noise) else np.nan
    noise_cum = float(noise.max_cum_receipts_diff.max()) if len(noise) else np.nan
    PDT["exceeds_indeterminacy_annual"] = PDT.mean_annual_switched_pct > noise_pct
    PDT["exceeds_indeterminacy_cumulative"] = PDT.max_cum_receipts_diff > noise_cum
    Rg.table("T5_SWITCHES", SWT, "จำนวนการรับใหม่ที่ต้องเปลี่ยนจังหวัดปลายทางเมื่อเปลี่ยนหลักคิด รายปี")
    Rg.table("T5_PRACTICAL_DIFFERENCES", PDT, "เกณฑ์ความต่างเชิงปฏิบัติ (กำหนดก่อนอ่านผล) และผลตัดสินรายคู่แผน", main=True)
    Rg.table("T5_PROVINCE_DIFFERENCES", PRD, "ความต่างรายจังหวัดของจำนวนรับใหม่สะสม ปีแรก และจำนวนคงอยู่ 2583 ระหว่างคู่แผน")
    # ---------------- priority overlap
    pr = []
    for c in ["P", "S", "N"]:
        a0 = ctx.H0 / ET["common_total"][c][0]
        pr.append(set(ctx.provs[np.argsort(a0)[:19]]))
    names = ["P", "S", "N"]
    ov = [dict(a=names[i], b=names[j], overlap=len(pr[i] & pr[j]), jaccard=len(pr[i] & pr[j]) / len(pr[i] | pr[j]))
          for i in range(3) for j in range(i + 1, 3)]
    Rg.table("T5_PRIORITY_OVERLAP", pd.DataFrame(ov), "การทับซ้อนของกลุ่ม 19 จังหวัดที่ความเพียงพอต่ำสุด (2569) ระหว่างเกณฑ์")
    allthree = pr[0] & pr[1] & pr[2]
    Rg.text("c54_priority_all3", ", ".join(ctx.names[p] for p in sorted(allthree, key=lambda p: ctx.names[p])))
    Rg.claim("c54_priority_all3_n", len(allthree), "{:.0f}", "จังหวัด")
    # ---------------- binding constraints & capacity
    bind = []
    for pid in [p for p in res if res[p].get("ledger") is not None]:
        L = res[pid]["ledger"]
        bind.append(dict(plan_id=pid, cap_mode=res[pid].get("cap_mode"), cap_binding_share=L.cap_binding.mean(),
                         floor_binding_share=L.floor_binding.mean(),
                         floor_only_appointments=int(L.loc[L.floor_binding & ~L.cap_binding.astype(bool), "new_appointments_accepted_starts"].sum()),
                         transfer_cap_binding_share=L.transfer_cap_binding.mean(),
                         protection_binding_share=L.protection_binding.mean(),
                         transfer_events=int(L.transfers_out_planned.sum()),
                         unplaced_total=float(L.groupby("year_ce").unplaced_national.first().sum()),
                         provinces_with_net_decline_2040=int(((L[L.year_ce == years[-1]].expected_closing_stock.to_numpy()
                                                               - ctx.H0) < 0).sum()),
                         appointments_to_above_target=int(L.loc[L.attainment_own >= 1, "new_appointments_accepted_starts"].sum())))
    BC = pd.DataFrame(bind)
    Rg.table("T5_BINDING_CONSTRAINTS", BC, "ข้อจำกัดที่ตึงตัว การจัดสรรตามขั้นต่ำ จำนวนที่จัดสรรไม่ได้ และการโยกย้ายของทุกแผน", main=False)
    inv = [r["inverse_summary"] for r in res.values() if r.get("inverse_summary") is not None]
    INV = pd.concat(inv, ignore_index=True) if inv else pd.DataFrame()
    Rg.table("T5_INVERSE_FEASIBILITY", INV, "ต้องมีแพทย์พร้อมจัดสรรเท่าใดจึงถึงเกณฑ์ภายใน 2583 (LP relaxation; มีเงื่อนไขตามเพดาน)", main=True)
    INVP = pd.concat([r["inverse_path"] for r in res.values() if r.get("inverse_path") is not None], ignore_index=True) if inv else pd.DataFrame()
    Rg.table("T5_INVERSE_PATHS", INVP, "เส้นทางจำนวนแพทย์พร้อมจัดสรรที่ต้องการรายปี (ถ้าถึงเกณฑ์ได้)")
    # ---------------- sensitivity summary vs base plans
    sens = []
    base_of = lambda pid: pid.split("|")[0]
    for pid, r in res.items():
        if r["group"] != "sensitivity" or r.get("H") is None:
            continue
        b = base_of(pid)
        if b not in res or res[b].get("x") is None:
            continue
        L = r["ledger"]
        own = L.groupby("year_ce").agg(H=("expected_closing_stock", "sum"), T=("target_own", "sum"))
        z = TR[(TR.plan_id == pid) & (TR.criterion == "own")] if pid in central_ctx_plans else None
        a40 = (L[L.year_ce == years[-1]].expected_closing_stock / L[L.year_ce == years[-1]].target_own).to_numpy()
        Tl = L[L.year_ce == years[-1]].target_own.to_numpy()
        Hl = L[L.year_ce == years[-1]].expected_closing_stock.to_numpy()
        order = np.argsort(a40)[:19]
        sw, pct = EV.switches(res[b]["x"], r["x"], res[b]["pool"] - res[b]["x"].sum(1), r["pool"] - r["x"].sum(1),
                              res[b]["pool"])
        sens.append(dict(plan_id=pid, base_plan=b, variant=r["spec"]["variant"], status=r["status"],
                         stock_2040=Hl.sum(), national_attainment_own_2040=Hl.sum() / Tl.sum(),
                         bottom_quartile_own_2040=Hl[order].sum() / Tl[order].sum(),
                         gini_own_2040=EV.gini(a40, Tl), transfer_events=int(r["zout"].sum()),
                         objective_exact=r.get("objective_exact"),
                         mean_annual_switch_pct_vs_base=float(pct.mean()) if res[b]["pool"][0] == r["pool"][0] else np.nan,
                         cum_receipts_max_abs_diff_vs_base=int(np.abs(r["x"].sum(0) - res[b]["x"].sum(0)).max())))
    for pid in [p for p in res if res[p].get("x") is None and res[p]["group"] == "sensitivity"]:
        sens.append(dict(plan_id=pid, base_plan=base_of(pid), variant=res[pid]["spec"]["variant"], status=res[pid]["status"]))
    SENS = pd.DataFrame(sens)
    Rg.table("T5_SENSITIVITY_SUMMARY", SENS, "สรุปการวิเคราะห์ความไว (เทียบแผนฐาน)", main=True)
    # ---------------- feedback diagnostics
    fbl = [r["feedback_log"] for r in res.values() if r.get("feedback_log") is not None]
    FBL = pd.concat(fbl, ignore_index=True) if fbl else pd.DataFrame()
    Rg.table("T5_FEEDBACK_LOG", FBL, "บันทึกการป้อนกลับรายปี: ความยืดหยุ่นเฉพาะที่ และกำไรป้อนกลับต่อเป้าหมาย")
    fbc = []
    for pid in ["N-R", "NFB0-R", "NFB0.5-R", "NFB1-R", "NFB1-R|B", "NFB1-R|grow"]:
        if pid not in res or res[pid].get("H") is None:
            continue
        H = res[pid]["H"]
        TN = ET["common_total"]["N"]
        a = H / TN
        top = np.argsort(ctx.H0 / TN[0])[-19:]
        for t, y in enumerate(years):
            fbc.append(dict(plan_id=pid, year_ce=y, gini_vs_nstd=EV.gini(a[t], TN[t]),
                            bottom_quartile_vs_nstd=EV.year_metrics(H[t], TN[t], ctx.region, popm[t])["bottom_quartile_attainment"],
                            share_receipts_top19_2025=float(res[pid]["x"][t, top].sum() / res[pid]["x"][t].sum()),
                            own_target_total=float(res[pid]["T"][t].sum()),
                            own_attainment=float(H[t].sum() / res[pid]["T"][t].sum()),
                            own_gini=EV.gini(H[t] / res[pid]["T"][t], res[pid]["T"][t])))
    FBC = pd.DataFrame(fbc)
    Rg.table("T5_FEEDBACK_CONVERGENCE", FBC, "N-FB เทียบ N-STD: ความเหลื่อมล้ำเทียบตัวหารอ้างอิงคงที่ ส่วนแบ่งการรับใหม่ของจังหวัดที่ได้เปรียบ และความเพียงพอตามเป้าของตนเอง")
    # zero-feedback verification: N-FB(lambda=0) targets equal N-STD targets exactly
    if "NFB0-R" in res and res["NFB0-R"].get("T") is not None:
        Rg.claim("c54_nfb0_target_maxdiff", float(np.abs(res["NFB0-R"]["T"] - res["N-R"]["T"]).max()), "{:.1e}", "คน")
    # ---------------- workload-dependent departures (sensitivity of fixed schedules)
    beta = float(S.cfg["departures"]["workload_departure_elasticity"])
    wrows = []
    svc = ctx.svc[ctx.svc.year.isin([S.base_year] + years)].sort_values(["year", "prov_code"])
    Vop = svc.V_op_moph.to_numpy().reshape(len(years) + 1, -1)
    L0 = Vop[0] / ctx.H0
    hres = ctx.departures.h["resignation"]
    hoth = sum(ctx.departures.h[c] for c in SU_EXIT[1:])
    for pid in [p for p in PRINCIPAL + ["SQ-C"] if p in res and res[p].get("x") is not None]:
        r = res[pid]
        Hp = ctx.H0.copy()
        for t in range(len(years)):
            Lw = Vop[t] / Hp if t > 0 else L0
            h = hres * (Lw / L0) ** beta + hoth
            d = 1 - np.exp(-h)
            Hp = (1 - d + ctx.dep["r"]) * Hp + r["x"][t] + r["zin"][t] - r["zout"][t]
        wrows.append(dict(plan_id=pid, stock_2040_base=float(r["H"][-1].sum()), stock_2040_workload=float(Hp.sum()),
                          diff=float(Hp.sum() - r["H"][-1].sum()),
                          bottom_quartile_P_base=EV.year_metrics(r["H"][-1], ET["common_total"]["P"][-1], ctx.region, popm[-1])["bottom_quartile_attainment"],
                          bottom_quartile_P_workload=EV.year_metrics(Hp, ET["common_total"]["P"][-1], ctx.region, popm[-1])["bottom_quartile_attainment"],
                          elasticity=beta))
    WD = pd.DataFrame(wrows)
    Rg.table("T5_WORKLOAD_DEPARTURES", WD, "ความไวต่อการลาออกที่ขึ้นกับภาระงาน (สัมประสิทธิ์ความสัมพันธ์จากบทที่ 4; ไม่ใช่ผลเชิงเหตุผล)")
    # ---------------- report tables
    rows = []
    for pid in PRINCIPAL:
        r = res[pid]
        L = r["ledger"]
        own = TR[(TR.plan_id == pid) & (TR.criterion == "own")]
        l = own[own.year_ce == years[-1]].iloc[0]
        rows.append({"แผน": pid, "ตัวหาร": FAM_LABEL[r["spec"]["family"]],
                     "การโยกย้าย": "ไม่มี" if r["spec"]["mobility"] == "recruitment_only" else "มี (≤2%/ปี, งบประเทศ 1%)",
                     "เป้าหมาย": "รวมร่วม 1:1,000 (Experiment A)", "สถานะ": r["status"],
                     "แพทย์ 2583": round(float(r["H"][-1].sum())), "ความเพียงพอรวม 2583": round(l.national_attainment, 3),
                     "กลุ่มล่าง 19 จังหวัด 2583": round(l.bottom_quartile_attainment, 3),
                     "ต่ำสุด 2583": round(l.worst_attainment, 3), "Gini 2583": round(l.gini, 3),
                     "การโยกย้ายสะสม (ครั้ง)": int(r["zout"].sum()),
                     "สัดส่วนจังหวัด-ปีที่เพดานตึง": round(float(L.cap_binding.mean()), 2)})
    T53 = pd.DataFrame(rows)
    Rg.table("T53_MAIN_PLANS", T53, "แผนหลักหกแบบ: ตัวหาร การโยกย้าย เป้าหมาย ข้อจำกัดร่วม และผลปี 2583 ตามเกณฑ์ของตนเอง", main=True)
    cap_rows = []
    for pid in ["P-R", "P-RT", "S-RT", "N-RT", "P-R|net", "P-RT|net", "S-RT|net", "N-RT|net", "P-RT|tau0.05",
                "P-RT|net|tau0.05", "P-RT|net|surplus", "P-RT|net|region", "P-R|pool2500", "P-R|pool1500"]:
        if pid not in res:
            continue
        r = res[pid]
        if r.get("ledger") is None:
            cap_rows.append({"แผน": pid, "สถานะ": r["status"],
                             "จำนวนที่จัดสรรไม่ได้ (ขั้นต่ำ)": sum((r.get("diagnostics") or {}).get("min_unplaced_by_year", []) or [0])})
            continue
        L = r["ledger"]
        base = res.get(pid.replace("RT", "R").replace("|tau0.05", "").replace("|surplus", "").replace("|region", ""))
        dJ = 100 * (r["objective_exact"] / base["objective_exact"] - 1) if base and base.get("objective_exact") else np.nan
        cap_rows.append({"แผน": pid, "เพดาน": "รับเข้ารวม 10%" if r["cap_mode"] == "gross_arrivals" else "เติบโตสุทธิ 10%",
                         "สถานะ": r["status"], "การโยกย้ายสะสม (ครั้ง)": int(r["zout"].sum()),
                         "จังหวัด-ปีที่เพดานตึง (%)": round(100 * float(L.cap_binding.mean()), 1),
                         "จังหวัด-ปีที่ได้เพียงขั้นต่ำ (%)": round(100 * float(L.floor_binding.mean()), 1),
                         "จำนวนที่จัดสรรไม่ได้": float(L.groupby("year_ce").unplaced_national.first().sum()),
                         "J เทียบแผนไม่มีโยกย้าย (%)": round(dJ, 2) if "RT" in pid else np.nan,
                         "แพทย์ 2583": round(float(r["H"][-1].sum()))})
    T54 = pd.DataFrame(cap_rows)
    Rg.table("T54_TRANSFER_AND_CAPACITY", T54, "การโยกย้าย ข้อจำกัดที่ตึงตัว และจำนวนที่จัดสรรไม่ได้ ภายใต้เพดานสองแบบ", main=True)
    # first-year plan
    fy = []
    for pid in ["P-R", "S-R", "N-R"]:
        L = res[pid]["ledger"]
        fy.append(L[L.year_ce == years[0]].set_index("prov_code")[["new_appointments_accepted_starts", "expected_closing_stock",
                                                                    "attainment_own"]].add_suffix(f"_{pid}"))
    L0_ = res["P-R"]["ledger"]
    L0_ = L0_[L0_.year_ce == years[0]].set_index("prov_code")
    T57 = pd.concat([L0_[["province", "health_region", "opening_headcount", "expected_departures_total", "expected_reentries"]]] + fy, axis=1).reset_index()
    T57 = T57.rename(columns={"province": "จังหวัด", "health_region": "เขต", "opening_headcount": "ตั้งต้น 2568",
                              "expected_departures_total": "ออกที่คาด", "expected_reentries": "กลับเข้าที่คาด",
                              "new_appointments_accepted_starts_P-R": "รับใหม่ P-R", "new_appointments_accepted_starts_S-R": "รับใหม่ S-R",
                              "new_appointments_accepted_starts_N-R": "รับใหม่ N-R",
                              "expected_closing_stock_P-R": "ปลายปี P-R", "expected_closing_stock_S-R": "ปลายปี S-R",
                              "expected_closing_stock_N-R": "ปลายปี N-R", "attainment_own_P-R": "ความเพียงพอ P-R",
                              "attainment_own_S-R": "ความเพียงพอ S-R", "attainment_own_N-R": "ความเพียงพอ N-R"})
    for c in T57.columns:
        if T57[c].dtype.kind == "f":
            T57[c] = T57[c].round(3 if "ความเพียงพอ" in c else 1)
    T57 = T57.drop(columns=["prov_code"]).sort_values(["เขต", "จังหวัด"])
    Rg.table("T57_FIRST_YEAR_PLAN", T57, "แผนปี พ.ศ. 2569 รายจังหวัด: จำนวนตั้งต้น ออกและกลับเข้าที่คาด รับใหม่ จำนวนปลายปี และความเพียงพอ (แผน R ของสามหลักคิด; ไม่มีการโยกย้ายในแผน R)", main=True)
    # baseline and assumptions (report table 5.2)
    a = S.cfg["allocation"]
    by = S.base_year
    pop = ctx.pop
    p25 = pop[pop.year == by].population.sum(); p40 = pop[pop.year == years[-1]].population.sum()
    s60 = lambda y: 100 * pop[pop.year == y]["n3_60+"].sum() / pop[pop.year == y].population.sum()
    T52 = pd.DataFrame([
        ("ปีฐาน / ปีจัดสรร", f"พ.ศ. {by + 543} / {years[0] + 543}–{years[-1] + 543} (15 การตัดสินใจ)", "การออกแบบ", "ข้อตกลง"),
        ("แพทย์ตั้งต้น 76 จังหวัด", f"{ctx.H0.sum():,.0f} คน", "รายงานทรัพยากรสาธารณสุข 2568 สังกัด สธ.", "สังเกต (ขอบเขตกว้างกว่า สป.สธ.)"),
        ("ประชากรทะเบียนราษฎร 76 จังหวัด", f"{p25:,.0f} → {p40:,.0f} คน (2568→2583)", "DOPA; Hamilton–Perry", "สังเกต → ฉาย"),
        ("สัดส่วนอายุ 60+", f"ร้อยละ {s60(by):.1f} → {s60(years[-1]):.1f}", "DOPA; Hamilton–Perry", "สังเกต → ฉาย"),
        ("ความน่าจะเป็นที่แพทย์ออกต่อปี", f"ร้อยละ {100 * (ctx.dep['d'] * ctx.H0).sum() / ctx.H0.sum():.2f} (รายจังหวัดรวมกำลังแบบ EB)", "HROPS ปีงบ 2564–2568", "ประมาณ"),
        ("อัตรากลับเข้าต่อปี", f"ร้อยละ {100 * (ctx.dep['r'] * ctx.H0).sum() / ctx.H0.sum():.2f}", "HROPS ปีงบ 2564–2568", "ประมาณ"),
        ("แพทย์พร้อมจัดสรร", f"{ctx.pool[0]:,.0f} คนต่อปี (ผู้เริ่มงานที่ตอบรับแล้ว)", "ตัวอย่างของผู้เขียน", "ตัวอย่าง"),
        ("ค่าอ้างอิงความเพียงพอ", f"{S.cfg['targets']['reference_per_1000']:g} แพทย์ต่อประชากร 1,000", "ตัวอย่างของผู้เขียน (ไม่ใช่ WHO 4.45)", "ตัวอย่าง"),
        ("ขั้นต่ำรายจังหวัด", f"{a['universal_new_appointment_floor']} คนต่อปีทุกจังหวัด", "ผู้เขียน", "ทางเลือกนโยบาย"),
        ("เพดาน", f"ผู้มาใหม่รวม ≤ ร้อยละ {100 * a['cap_fraction_of_opening_stock']:.0f} ของจำนวนตั้งต้น (ทางเลือก: เติบโตสุทธิ)", "ตัวอย่างของผู้เขียน; การตีความเป็นทางเลือก", "ตัวอย่าง"),
        ("การโยกย้าย (แผน RT)", f"≤ ร้อยละ {100 * a['main_transfer_fraction']:.0f} ต่อจังหวัด; งบประเทศร้อยละ {100 * a['national_transfer_budget_fraction']:.0f}; ต้นทางเหลือ ≥ ร้อยละ {100 * a['protected_survivor_fraction']:.0f}", "ตัวอย่าง", "ตัวอย่าง"),
        ("น้ำหนักบริการ", f"{S.cfg['services']['op_minutes']:g} นาที/ครั้ง OP, {S.cfg['services']['adjrw_minutes']:g} นาที/AdjRW", "ค่าหลักของบทที่ 4 (4.2.2)", "ตัวอย่าง (ไม่ใช่ WISN)"),
        ("M5", "สัมประสิทธิ์บทที่ 4; อ้างอิงปี 2566; ความชุกคงที่ปี 2568", "บทที่ 4 (T423)", "ประมาณ + ข้อตกลง"),
    ], columns=["รายการ", "ค่า", "แหล่ง", "สถานะ"])
    Rg.table("T52_BASELINE_AND_ASSUMPTIONS", T52, "ค่าเริ่มต้น พ.ศ. 2568 แหล่งข้อมูล ขอบเขต และข้อสมมติที่ผู้กำหนดนโยบายปรับได้", main=True)
    # ---------------- illustrative health gain (evaluation only; config/chapter5_health_gain.toml)
    _health_gain(Rg, ctx, res)
    # ---------------- integrated cutoff-safe hindcast (criteria declared in config/validation.toml)
    from . import hindcast as HC
    HCR = HC.run()
    Rg.table("T5_HINDCAST_PREDICTIONS", HCR["predictions"], "การทดสอบย้อนหลังทั้งระบบ: ค่าทำนายรายจังหวัดจากจุดตั้งต้น 2563–2566 เทียบค่าจริง", folder="validation", parquet=True)
    Rg.table("T5_HINDCAST_METRICS", HCR["metrics"], "ตัวชี้วัดการทดสอบย้อนหลัง: MAE, bias, การจัดอันดับ, กลุ่ม 19 จังหวัดต่ำสุด, ความครอบคลุมของช่วงคาดการณ์ แยกระยะและกลุ่มย่อย", folder="validation")
    acc = HCR["acceptance"].assign(criteria_file_sha256=HCR["config_sha256"])
    Rg.table("T5A_HINDCAST_ACCEPTANCE", acc, "ผลตามเกณฑ์ที่ประกาศก่อนการทดสอบย้อนหลัง (config/validation.toml)")
    pm = HCR["metrics"][(HCR["metrics"].origin == "pooled") & (HCR["metrics"].stratum == "all")].set_index(["model", "horizon"])
    for m_ in ["persistence", "population_only", "trend", "stock_flow_unconditional", "stock_flow_conditional"]:
        tag = m_.replace("stock_flow_", "sf_").replace("population_only", "poponly")
        for hh in [1, 3, 5]:
            if (m_, hh) in pm.index:
                Rg.claim(f"c5a_hc_mae_{tag}_h{hh}", pm.loc[(m_, hh), "mae"], "{:.1f}", "คน")
                Rg.claim(f"c5a_hc_mape_{tag}_h{hh}", pm.loc[(m_, hh), "mape_pct"], "{:.1f}", "%")
                Rg.claim(f"c5a_hc_nat_{tag}_h{hh}", pm.loc[(m_, hh), "national_error_pct"], "{:+.1f}", "%")
                Rg.claim(f"c5a_hc_jac_{tag}_h{hh}", pm.loc[(m_, hh), "jaccard_lowest19"], "{:.2f}", "")
        if m_.startswith("stock_flow"):
            Rg.claim(f"c5a_hc_cov_{tag}_h3", pm.loc[(m_, 3), "interval_coverage"], "{:.0%}", "")
    # horizon-3 MAE by origin: shows where the pooled verdict comes from (final check M-7)
    po = HCR["metrics"][(HCR["metrics"].origin != "pooled") & (HCR["metrics"].stratum == "all") & (HCR["metrics"].horizon == 3)]
    wins = 0
    for o_ in sorted(po.origin.unique()):
        z = po[po.origin == o_].set_index("model").mae
        Rg.claim(f"c5a_hc_mae_sfu_o{o_}_h3", z["stock_flow_unconditional"], "{:.1f}", "คน")
        Rg.claim(f"c5a_hc_mae_pers_o{o_}_h3", z["persistence"], "{:.1f}", "คน")
        wins += int(z["stock_flow_unconditional"] < min(z["persistence"], z["population_only"]))
    Rg.claim("c5a_hc_n_origins_h3", po.origin.nunique(), "{:.0f}", "จุดตั้งต้น")
    Rg.claim("c5a_hc_n_wins_h3", wins, "{:.0f}", "จุดตั้งต้น")
    lost = [o_ for o_ in sorted(po.origin.unique()) if po[(po.origin == o_) & (po.model == "stock_flow_unconditional")].mae.iloc[0]
            >= po[(po.origin == o_) & (po.model == "persistence")].mae.iloc[0]]
    Rg.text("c5a_hc_lost_origins_be", ", ".join(str(int(o_) + 543) for o_ in lost) or "ไม่มี")
    for r_ in acc.itertuples():
        key = r_.criterion.split()[0].lower()
        Rg.text(f"c5a_hc_{key}_verdict", "ผ่าน" if r_.passed else "ไม่ผ่าน")
        Rg.claim(f"c5a_hc_{key}_value", r_.value, "{:.2f}", "")
    Rg.text("c5a_hc_criteria_sha", HCR["config_sha256"][:12])
    # ---------------- one validation inventory over the Chapter 4/5 artifacts
    from . import validation as VAL
    INVV = VAL.inventory(S, hindcast=HCR)
    Rg.table("T5_VALIDATION_INVENTORY", INVV, "บัญชีผลการตรวจสอบทั้งหมดของบทที่ 4–5: ชนิดหลักฐาน ข้อมูลที่ใช้ ตัวเทียบ ระยะ ตัวชี้วัด และข้อจำกัด", folder="validation")
    Rg.table("T5A_VALIDATION_SUMMARY", VAL.summary_th(INVV), "สรุปผลการตรวจสอบ: แบบจำลองเทียบตัวเทียบอย่างง่าย และสิ่งที่การตรวจแต่ละแบบยืนยันไม่ได้")
    for v, n_ in INVV.verdict.value_counts().items():
        Rg.claim(f"c5a_val_{v}", n_, "{:.0f}", "รายการ")
    Rg.claim("c5a_val_total", len(INVV), "{:.0f}", "รายการ")
    tz = INVV[INVV.check_id.str.startswith("C4-TEMP")]
    Rg.claim("c5a_val_temporal_beaten", int((tz.verdict == "does_not_beat_comparator").sum()), "{:.0f}", "รายการ")
    Rg.claim("c5a_val_temporal_total", len(tz), "{:.0f}", "รายการ")
    if S.name == "canonical":                                  # compact validation view for the Lab release
        from .config import OUT_CANONICAL
        lab_val = OUT_CANONICAL / "validation" / "lab_validation.json"
        lab_val.parent.mkdir(parents=True, exist_ok=True)
        lab_val.write_text(json.dumps(VAL.lab_summary(INVV, HCR), ensure_ascii=False, indent=1))
    # ---------------- claims used by the report
    _claims_compare(Rg, S, ctx, res, TR, XE, PDT, PRD, BC, INV, SENS, FBL, FBC, RESP, WD, ET, popm)
    man = Rg.finalize(dict(seconds_total=time.time() - t0))
    return dict(TR=TR, XE=XE, PDT=PDT, LED=LED, NB=NB, RT=RT, PIDX=PIDX, SENS=SENS, INV=INV, manifest=man)


HG_PLANS = PRINCIPAL + ["SQ-C", "SQ-HIST", "Pent-R", "NFB1-R", "B-R", "B-RT", "B-R|B", "B-R|asr", "P-R|net", "S-R|net",
                        "N-R|net", "B-R|net"]


def _health_gain(Rg, ctx, res):
    """Amenable burden averted by each plan under assumed elasticities (scenario arithmetic)."""
    from . import health_gain as HG
    cfg = HG.load_cfg()
    plans = [p for p in HG_PLANS if p in res and res[p].get("H") is not None]
    HGS, HGP, HGA = HG.evaluate(ctx, res, plans, cfg)
    Rg.table("T5_HEALTH_GAIN_ASSUMPTIONS", HGA, "ข้อสมมติของการประเมินภาระที่ระบบบริการช่วยได้ซึ่งป้องกันได้ (ฉากทัศน์สมมติ ไม่ใช่ผลที่ประมาณ)")
    Rg.table("T5_HEALTH_GAIN_SUMMARY", HGS, "ภาระที่ระบบบริการช่วยได้ซึ่งป้องกันได้ พ.ศ. 2569–2583 ของแต่ละแผน ภายใต้ความยืดหยุ่นที่สมมติ (YLL หลัก, DALY ความไว)")
    Rg.table("T5_HEALTH_GAIN_PROVINCES", HGP, "ภาระที่ป้องกันได้รายจังหวัด (YLL, ความยืดหยุ่นกลาง)")
    prim, cen = cfg["amenable"]["primary_measure"], cfg["elasticity"]["central"]
    z = HGS[HGS.measure == prim]
    view = z.assign(cell=z.averted_total.map("{:,.0f}".format) + " (" + z.averted_vs_PR_pct.map("{:+.1f}%".format) + ")")
    T = view.pivot(index="plan_id", columns="elasticity_label", values="cell").reindex([p for p in plans if p in set(z.plan_id)])
    T = T[[k for k in cfg["elasticity"]["values"]]].reset_index()
    T.columns = ["แผน"] + [f"ความยืดหยุ่น {cfg['elasticity']['values'][k]:+.2f}" for k in cfg["elasticity"]["values"]]
    Rg.table("T56_HEALTH_GAIN", T, "ฉากทัศน์สมมติ: YLL ที่ระบบบริการช่วยได้ซึ่งป้องกันได้สะสม พ.ศ. 2569–2583 เทียบการคงความหนาแน่นแพทย์ปี 2568 (ในวงเล็บ = ต่างจาก P-R)", main=True)
    A = HG.counterfactual_burden(ctx, prim, cfg)
    Rg.claim("c56_hg_amenable_2026", A[0].sum(), "int", "YLL")
    Rg.claim("c56_hg_amenable_share", 100 * A[0].sum() / ctx.idx[ctx.idx.year == ctx.S.years[0]].B_B.sum(), "{:.1f}", "%")
    Rg.claim("c56_hg_n_causes", len(cfg["amenable"]["max_age"]), "{:.0f}", "รหัส")
    for lab, e in cfg["elasticity"]["values"].items():
        Rg.claim(f"c56_hg_e_{lab}", e, "{:+.2f}", "")
    for r in z.itertuples():
        tag = r.plan_id.replace("|", "_").replace("-", "").replace(".", "")
        Rg.claim(f"c56_hg_{tag}_{r.elasticity_label}", r.averted_total, "int", "YLL")
        Rg.claim(f"c56_hgpct_{tag}_{r.elasticity_label}", r.averted_vs_PR_pct, "{:+.1f}", "%")
        if r.elasticity_label == cen:
            Rg.claim(f"c56_hgper1000_{tag}", r.averted_per_1000_physician_years, "int", "YLL")
            Rg.claim(f"c56_hglow19_{tag}", 100 * r.averted_low19_share, "{:.0f}", "%")
            Rg.claim(f"c56_hgloss_{tag}", r.provinces_with_loss, "{:.0f}", "จังหวัด")
    zd = HGS[(HGS.measure != prim) & (HGS.elasticity_label == cen)].set_index("plan_id")
    for pid in ["S-R", "SQ-C", "B-R", "P-R|net"]:
        if pid in zd.index:
            Rg.claim(f"c56_hgpct_daly_{pid.replace('|', '_').replace('-', '')}", zd.loc[pid, "averted_vs_PR_pct"], "{:+.1f}", "%")


def _claims_compare(Rg, S, ctx, res, TR, XE, PDT, PRD, BC, INV, SENS, FBL, FBC, RESP, WD, ET, popm):
    years = S.years
    y1 = years[-1]
    for pid in PRINCIPAL + ["SQ-C", "SQ-HIST", "Pent-R", "NFB1-R", "NFB0.5-R", "P-R|net", "P-RT|net", "S-RT|net", "N-RT|net",
                            "S-R|B", "N-R|B", "NFB1-R|B", "B-R", "B-RT", "B-R|net", "B-RT|net", "B-R|yld", "B-R|B",
                            "B-R|asr"]:
        if pid not in res or res[pid].get("H") is None:
            continue
        tag = pid.replace("|", "_").replace("-", "").replace(".", "")
        H = res[pid]["H"]
        Rg.claim(f"c54_stock2040_{tag}", H[-1].sum(), "int", "คน")
        Rg.claim(f"c54_stock2030_{tag}", H[4].sum(), "int", "คน")
        Rg.claim(f"c54_transfers_{tag}", res[pid]["zout"].sum(), "int", "ครั้ง")
        for crit in ["own"] + [f"{c}|common_total" for c in CRIT]:
            z = TR[(TR.plan_id == pid) & (TR.criterion == crit)]
            if not len(z):
                continue
            l = z[z.year_ce == y1].iloc[0]
            ct = crit.split("|")[0]
            Rg.claim(f"c54_nat_{tag}_{ct}", l.national_attainment, "{:.3f}", "")
            Rg.claim(f"c54_bq_{tag}_{ct}", l.bottom_quartile_attainment, "{:.3f}", "")
            Rg.claim(f"c54_worst_{tag}_{ct}", l.worst_attainment, "{:.3f}", "")
            Rg.claim(f"c54_gini_{tag}_{ct}", l.gini, "{:.3f}", "")
            Rg.claim(f"c54_p90p10_{tag}_{ct}", l.p90_p10, "{:.2f}", "")
            Rg.claim(f"c54_theilb_{tag}_{ct}", 100 * l.theil_between_share, "{:.0f}", "%")
            Rg.claim(f"c54_gapnat_{tag}_{ct}", l.gap_national, "int", "คน")
            Rg.claim(f"c54_gapsp_{tag}_{ct}", l.gap_spatial, "int", "คน")
            Rg.claim(f"c54_meet_{tag}_{ct}", l.provinces_meeting, "{:.0f}", "จังหวัด")
            Rg.claim(f"c54_cumshort_{tag}_{ct}", z.shortfall_sum.sum(), "int", "คน-ปี")
            f = z[z.year_ce == years[0]].iloc[0]
            Rg.claim(f"c54_gini2026_{tag}_{ct}", f.gini, "{:.3f}", "")
            Rg.claim(f"c54_bq2026_{tag}_{ct}", f.bottom_quartile_attainment, "{:.3f}", "")
    # baseline (2025) inequality under the population criterion
    from chapter4 import metrics as M4
    for c in CRIT:
        D0 = ctx.idx[ctx.idx.year == S.base_year].sort_values("prov_code")[CRIT_COL[c]].to_numpy()
        Rg.claim(f"c54_gini2025_{c}", M4.weighted_gini(ctx.H0 / D0, D0), "{:.3f}", "")
    for r in XE.itertuples():
        if r.plan_id in PRINCIPAL + ["SQ-C", "NFB1-R", "B-R"] and r.criterion in CRIT:
            tag = r.plan_id.replace("-", "").replace(".", "")
            Rg.claim(f"c54_regret_{tag}_{r.criterion}", r.regret_j_pct, "{:.1f}", "%")
    for r in XE[XE.criterion == "resp1"].itertuples():
        tag = r.plan_id.replace("-", "").replace(".", "").replace("|", "_")
        Rg.claim(f"c54_workload_{tag}", r.workload_2040, "int", "นาทีต่อแพทย์ต่อปี")
        Rg.claim(f"c54_wlp9010_{tag}", r.workload_p90_p10_2040, "{:.2f}", "")
    z = RESP[(RESP.plan_id == "P-R") & (RESP.lam == 1.0)]
    if len(z):
        Rg.claim("c54_workload_2026_PR", z.iloc[0].national_workload_min_per_physician, "int", "นาที")
    for r in PDT.itertuples():
        tag = f"{r.plan_a}_vs_{r.plan_b}".replace("-", "").replace("|", "_").replace(".", "")
        Rg.claim(f"c54_sw_{tag}", r.mean_annual_switched, "{:.0f}", "คนต่อปี")
        Rg.claim(f"c54_swpct_{tag}", r.mean_annual_switched_pct, "{:.1f}", "%")
        Rg.claim(f"c54_swmax_{tag}", r.max_annual_switched_pct, "{:.1f}", "%")
        Rg.claim(f"c54_swcum_{tag}", r.cumulative_switched, "int", "คน")
        Rg.claim(f"c54_maxcum_{tag}", r.max_cum_receipts_diff, "int", "คน")
        Rg.text(f"c54_maxcumprov_{tag}", r.province_max_cum_diff)
        Rg.claim(f"c54_bqloss_{tag}", r.worst_bottom_quartile_loss_pct, "{:.1f}", "%")
        Rg.text(f"c54_similar_{tag}", "ใกล้เคียงกันเชิงปฏิบัติ" if r.practically_similar else "ต่างกันเชิงปฏิบัติ")
        Rg.text(f"c54_beyond_noise_{tag}", "เกินระดับความไม่เป็นเอกลักษณ์ของคำตอบ" if r.exceeds_indeterminacy_cumulative
                else "ไม่เกินระดับความไม่เป็นเอกลักษณ์ของคำตอบ")
        if r.max_cumulative_shortfall_diff_pct == r.max_cumulative_shortfall_diff_pct:
            Rg.claim(f"c54_shortdiff_{tag}", r.max_cumulative_shortfall_diff_pct, "{:.1f}", "%")
    nz = PDT[PDT.near_optimal_alternative]
    Rg.claim("c54_noise_n_pairs", len(nz), "{:.0f}", "คู่")
    if len(nz):
        Rg.claim("c54_noise_pct_min", nz.mean_annual_switched_pct.min(), "{:.1f}", "%")
        Rg.claim("c54_noise_pct_max", nz.mean_annual_switched_pct.max(), "{:.1f}", "%")
        Rg.claim("c54_noise_cum_max", nz.max_cum_receipts_diff.max(), "int", "คน")
        Rg.claim("c54_noise_dj_max", nz.objective_diff_pct.max(), "{:.3f}", "%")
    # the provinces with the largest cumulative differences between families
    for a_, b_ in [("P-R", "S-R"), ("P-R", "N-R"), ("S-R", "N-R"), ("P-R", "B-R"), ("N-R", "B-R"), ("S-R", "B-R")]:
        z = PRD[(PRD.plan_a == a_) & (PRD.plan_b == b_)].sort_values("diff")
        tag = f"{a_}_vs_{b_}".replace("-", "")
        lo = z.head(3); hi = z.tail(3).iloc[::-1]
        Rg.text(f"c54_gain_{tag}", ", ".join(f"{r.province} (+{r.diff:,})" for r in hi.itertuples()))
        Rg.text(f"c54_lose_{tag}", ", ".join(f"{r.province} ({r.diff:,})" for r in lo.itertuples()))
    for r in BC.itertuples():
        if r.plan_id in PRINCIPAL + ["P-R|net", "P-RT|net", "P-R|ref0.5", "P-R|nofloor", "P-R|ref0.5|nofloor", "SQ-C", "B-R",
                         "B-R|net"]:
            tag = r.plan_id.replace("-", "").replace("|", "_").replace(".", "")
            Rg.claim(f"c54_capbind_{tag}", 100 * r.cap_binding_share, "{:.0f}", "%")
            Rg.claim(f"c54_floorbind_{tag}", 100 * r.floor_binding_share, "{:.0f}", "%")
            Rg.claim(f"c54_decline_{tag}", r.provinces_with_net_decline_2040, "{:.0f}", "จังหวัด")
            Rg.claim(f"c54_abovetarget_{tag}", r.appointments_to_above_target, "int", "คน")
    for r in INV.itertuples() if len(INV) else []:
        tag = f"{r.cap_mode}_{r.criterion}_{'ramp' if r.ramp_limited else 'noramp'}"
        Rg.claim(f"c54_inv_maxatt_{tag}", r.max_attainment_2040, "{:.2f}", "")
        Rg.text(f"c54_inv_reach_{tag}", "ถึงได้" if r.reference_reachable_by_2040 else "ถึงไม่ได้")
        if r.reference_reachable_by_2040:
            Rg.claim(f"c54_inv_total_{tag}", r.total_appointments_required, "int", "คน")
            Rg.claim(f"c54_inv_2040_{tag}", r.pool_2040_required, "int", "คนต่อปี")
        if r.binding_province:
            Rg.text(f"c54_inv_bind_{tag}", r.binding_province)
    for r in SENS.itertuples():
        tag = r.plan_id.replace("-", "").replace("|", "_").replace(".", "")
        if r.stock_2040 == r.stock_2040:
            Rg.claim(f"c55_sens_bq_{tag}", r.bottom_quartile_own_2040, "{:.3f}", "")
            Rg.claim(f"c55_sens_nat_{tag}", r.national_attainment_own_2040, "{:.3f}", "")
            Rg.claim(f"c55_sens_stock_{tag}", r.stock_2040, "int", "คน")
            Rg.claim(f"c55_sens_tr_{tag}", r.transfer_events, "int", "ครั้ง")
            if r.mean_annual_switch_pct_vs_base == r.mean_annual_switch_pct_vs_base:
                Rg.claim(f"c55_sens_sw_{tag}", r.mean_annual_switch_pct_vs_base, "{:.1f}", "%")
        Rg.text(f"c55_sens_status_{tag}", str(r.status))
    if len(FBL):
        for lam in sorted(FBL.lam.unique()):
            z = FBL[(FBL.lam == lam) & (FBL.plan_id == f"NFB{lam:g}-R")]
            if len(z):
                t = f"{lam:g}".replace(".", "")
                Rg.claim(f"c55_eta_first_{t}", z.eta_mean.iloc[0], "{:.2f}", "")
                Rg.claim(f"c55_eta_last_{t}", z.eta_mean.iloc[-1], "{:.2f}", "")
                Rg.claim(f"c55_gainB_first_{t}", z.gain_B_mean.iloc[0], "{:.2f}", "")
                Rg.claim(f"c55_gainB_last_{t}", z.gain_B_mean.iloc[-1], "{:.2f}", "")
                Rg.claim(f"c55_gainBmax_{t}", z.gain_B_max.max(), "{:.2f}", "")              # over all 15 years
                Rg.claim(f"c55_gainBmax_first_{t}", z.gain_B_max.iloc[0], "{:.2f}", "")       # first decision year
                Rg.claim(f"c55_ngain1_first_{t}", z.provinces_gain_B_ge_1.iloc[0], "{:.0f}", "จังหวัด")
                Rg.claim(f"c55_ngain1_last_{t}", z.provinces_gain_B_ge_1.iloc[-1], "{:.0f}", "จังหวัด")
    for pid in FBC.plan_id.unique():
        z = FBC[FBC.plan_id == pid]
        tag = pid.replace("-", "").replace("|", "_").replace(".", "")
        Rg.claim(f"c55_fb_gini_{tag}", z.gini_vs_nstd.iloc[-1], "{:.3f}", "")
        Rg.claim(f"c55_fb_bq_{tag}", z.bottom_quartile_vs_nstd.iloc[-1], "{:.3f}", "")
        Rg.claim(f"c55_fb_top19_{tag}", 100 * z.share_receipts_top19_2025.mean(), "{:.1f}", "%")
        Rg.claim(f"c55_fb_ownatt_{tag}", z.own_attainment.iloc[-1], "{:.3f}", "")
        Rg.claim(f"c55_fb_owntotal_{tag}", z.own_target_total.iloc[-1], "int", "คน")
        Rg.claim(f"c55_fb_owngini_{tag}", z.own_gini.iloc[-1], "{:.3f}", "")
    for r in WD.itertuples():
        tag = r.plan_id.replace("-", "")
        Rg.claim(f"c55_wd_diff_{tag}", r.diff, "int", "คน")
    Rg.claim("c55_wd_beta", float(S.cfg["departures"]["workload_departure_elasticity"]), "{:.3f}", "")
    # solver quality
    PI = plan_index(res)
    ok = PI[PI.status.astype(str).str.startswith("exploratory")]
    Rg.claim("c54_n_plans", len(PI), "{:.0f}", "แผน")
    Rg.claim("c54_n_blocked", int((PI.status == "blocked_for_specific_reason").sum()), "{:.0f}", "แผน")
    Rg.claim("c54_n_infeasible", int((PI.status == "infeasible_under_selected_constraints").sum()), "{:.0f}", "แผน")
    Rg.claim("c54_max_gap", 100 * ok.max_mip_gap.max(), "{:.3f}", "%")
    opt = ok[ok.plan_id != "SQ-HIST"]
    Rg.claim("c54_n_checked", float(opt.all_constraints_ok.notna().sum()), "{:.0f}", "แผน")
    Rg.claim("c54_n_checks_failed", float((opt.all_constraints_ok == False).sum()), "{:.0f}", "แผน")  # noqa: E712
    Rg.claim("c54_n_incumbent_adopted", float(PI.incumbent_adopted.sum()), "{:.0f}", "แผน")
    adopted = PI[PI.incumbent_adopted.astype(bool)]
    Rg.claim("c54_n_incumbent_zero_transfers", float((adopted.transfer_events == 0).sum()), "{:.0f}", "แผน")
    Rg.claim("c54_n_incumbent_with_transfers", float((adopted.transfer_events > 0).sum()), "{:.0f}", "แผน")
    Rg.claim("c54_max_gap_non_incumbent", 100 * PI[~PI.incumbent_adopted.astype(bool)].max_mip_gap.max(), "{:.3f}", "%")
    for g in ["P-R|greedy", "S-R|greedy", "N-R|greedy"]:
        if g in res and res[g].get("objective_exact"):
            b = g.split("|")[0]
            tag = b.replace("-", "")
            Rg.claim(f"c54_greedy_gap_{tag}", 100 * (res[g]["objective_exact"] / res[b]["objective_exact"] - 1), "{:.3f}", "%")
            Rg.claim(f"c54_greedy_sec_{tag}", res[g]["diagnostics"]["seconds"], "{:.2f}", "วินาที")
            Rg.claim(f"c54_milp_sec_{tag}", res[b]["seconds"], "{:.0f}", "วินาที")
    if "P-R|tangent_fine" in res and res["P-R|tangent_fine"].get("objective_exact"):
        Rg.claim("c54_tangent_diff", 100 * (res["P-R|tangent_fine"]["objective_exact"] / res["P-R"]["objective_exact"] - 1), "{:.3f}", "%")
    Rg.claim("c54_tangent_err_bound", float(S.cfg["allocation"]["tangent_step"]) ** 2 / 4, "{:.5f}", "")
    if "P-R|rolling" in res and res["P-R|rolling"].get("objective_exact"):
        Rg.claim("c54_rolling_diff", 100 * (res["P-R|rolling"]["objective_exact"] / res["P-R"]["objective_exact"] - 1), "{:.3f}", "%")
    # J change from allowing transfers, against the recruitment-only counterpart
    for pid in [p for p in res if "RT" in p.split("|")[0] and res[p].get("objective_exact")]:
        b = PL.r_counterpart(pid)
        if b in res and res[b].get("objective_exact"):
            tag = pid.replace("-", "").replace("|", "_").replace(".", "")
            Rg.claim(f"c54_dJ_{tag}", 100 * (res[pid]["objective_exact"] / res[b]["objective_exact"] - 1), "{:.3f}", "%")
    # pool 2,500: unplaced physicians under compulsory full placement
    for pid in ["P-R|pool2500", "S-R|pool2500", "N-R|pool2500"]:
        u = (res.get(pid, {}).get("diagnostics") or {}).get("min_unplaced_by_year")
        if u:
            tag = pid.replace("-", "").replace("|", "_")
            Rg.claim(f"c54_unplaced2026_{tag}", u[0], "int", "คน")
            Rg.claim(f"c54_unplacedtotal_{tag}", sum(u), "int", "คน")
            last = max([i for i, v in enumerate(u) if v > 0], default=-1)
            Rg.claim(f"c54_unplacedlast_{tag}", years[last] + 543 if last >= 0 else np.nan, "{:.0f}", "พ.ศ.")
    # the province bound by the gross cap (lowest 2040 attainment under P-R)
    TP = ET["common_total"]["P"]
    aPR = res["P-R"]["H"][-1] / TP[-1]
    iw = int(np.argmin(aPR))
    Rg.text("c54_worst_province", ctx.names[ctx.provs[iw]])
    Rg.claim("c54_worst_province_H0", ctx.H0[iw], "int", "คน")
    Rg.claim("c54_worst_province_H2040", res["P-R"]["H"][-1][iw], "int", "คน")
    Rg.claim("c54_worst_province_exit", 100 * ctx.dep["d"][iw], "{:.1f}", "% ต่อปี")
    Rg.claim("c54_worst_province_cap", 100 * S.cfg["allocation"]["cap_fraction_of_opening_stock"], "{:.0f}", "%")
    Rg.claim("c54_worst_province_attain_net", res["P-R|net"]["H"][-1][iw] / TP[-1][iw] if "P-R|net" in res else np.nan, "{:.3f}", "")
    Rg.claim("c54_worst_province_attain_2025", ctx.H0[iw] / TP[0][iw], "{:.3f}", "")
    Rg.claim("c54_worst_province_cap_n", S.cfg["allocation"]["cap_fraction_of_opening_stock"] * ctx.H0[iw], "{:.0f}", "คนต่อปี")
    from . import inputs as I_
    ev = I_.flow_events_province()
    rec = ev[(ev.direction == "entry") & (ev.category == "recruitment_hiring") & (ev.prov_code == int(ctx.provs[iw]))
             & ev.fiscal_year.between(2021, 2025)].groupby("fiscal_year").events.sum()
    Rg.claim("c54_worst_province_rec_hist", rec.mean() if len(rec) else np.nan, "{:.0f}", "คนต่อปี")
    Rg.claim("c54_worst_province_rec_hist_pct", 100 * rec.mean() / ctx.H0[iw] if len(rec) else np.nan, "{:.0f}", "%")
    for pid in ["P-R", "S-R", "N-R", "B-R"]:
        x0 = res[pid]["x"][0]
        tag = pid.replace("-", "")
        Rg.claim(f"c54_floorprov2026_{tag}", float((x0 == 1).sum()), "{:.0f}", "จังหวัด")
        Rg.claim(f"c54_xmax2026_{tag}", float(x0.max()), "int", "คน")
        Rg.text(f"c54_xmaxprov2026_{tag}", ctx.names[ctx.provs[int(np.argmax(x0))]])
        top = np.argsort(-x0, kind="stable")[:3]
        Rg.text(f"c54_top3_2026_{tag}", ", ".join(f"{ctx.names[ctx.provs[i]]} {int(x0[i])} คน" for i in top))
        cum = res[pid]["x"].sum(0)
        top = np.argsort(-cum, kind="stable")[:3]
        Rg.text(f"c54_top3_cum_{tag}", ", ".join(f"{ctx.names[ctx.provs[i]]} {int(cum[i]):,} คน" for i in top))
    sq = res.get("SQ-C", {})
    if sq.get("diagnostics"):
        Rg.claim("c54_sq_l1", sq["diagnostics"].get("l1_distance_to_historical_rule", np.nan), "int", "คน")
        Rg.claim("c54_sq_moved", sq["diagnostics"].get("l1_distance_to_historical_rule", np.nan) / 2, "int", "ตำแหน่ง")
    h = res.get("SQ-HIST", {}).get("check") or {}
    Rg.text("c54_sqhist_violations", ", ".join(k_ for k_, v in h.items() if v is False and k_ != "all_ok") or "ไม่มี")
