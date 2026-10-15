"""Chapter 5 pipeline: context, the plan catalogue and the deterministic plan runs.

Stages (each writes to outputs/chapter5/ or to a scenario folder):
    inputs   input contract, projections, supply, indices, M5 checks          (pipeline.stage_inputs)
    plans    principal plans, variants, sensitivities, inverse feasibility     (pipeline.stage_plans)
    uncert   paired stochastic evaluation, adaptive replanning                 (analysis.stage_uncertainty)
    compare  cross-evaluation, switches, practical differences, figures, workbook (analysis.stage_compare)
    report   Thai chapter from the template and the claim registry            (report.render)
"""
from __future__ import annotations

from chapter4 import config as C4

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from . import allocation as AL
from . import config as C
from . import demography as D
from . import inputs as I
from . import responsibilities as R
from . import simulation as SIM
from . import supply as SU
from .reporting import Registry

CTX_DEFAULT = dict(demog="central", departures="pooled", weights=None, inpatient=None, morb=None, age="projected",
                   estimator="ols", resources="fixed", ent="central")


@dataclass
class Ctx:
    S: object
    opts: dict
    base: pd.DataFrame
    key: pd.DataFrame
    provs: np.ndarray
    names: dict
    region: np.ndarray
    H0: np.ndarray
    rates: pd.DataFrame
    departures: object
    dep: dict
    pop: pd.DataFrame
    ent: pd.DataFrame
    svc: pd.DataFrame
    svc_method: dict
    pkg: dict
    w: dict
    idx: pd.DataFrame
    registry: pd.DataFrame
    support: pd.DataFrame
    res: pd.DataFrame
    cov: pd.DataFrame
    fb: object
    pool: np.ndarray
    pool_table: pd.DataFrame
    dist: np.ndarray
    k: float


@lru_cache(maxsize=2)
def _projections(overrides_json):
    S = C.load(json.loads(overrides_json))
    return D.projections(S)


@lru_cache(maxsize=2)
def _m5(overrides_json):
    S = C.load(json.loads(overrides_json))
    return I.m5_package(S, cache_dir=S.dirs()["cache"] if S.name == "canonical" else C.load().dirs()["cache"])


def centroids(provs):
    import geopandas as gpd
    g = gpd.read_file(C4.geo_path())
    pts = g.to_crs(32647).representative_point().to_crs(4326)
    g = g.assign(lat=pts.y, lon=pts.x).set_index("prov_id")
    g = g.loc[provs]
    return g.lat.to_numpy(), g.lon.to_numpy()


@lru_cache(maxsize=16)
def context(overrides_json: str = "{}", opts_json: str = "{}") -> Ctx:
    S = C.load(json.loads(overrides_json))
    opts = CTX_DEFAULT | json.loads(opts_json)
    base = I.baseline(S)
    key = I.provinces()
    provs = base.prov_code.to_numpy()
    rates = I.flow_rates(S)
    deps = SU.Departures(rates, provs, national=opts["departures"] == "national")
    dep = deps.central()
    pr = _projections(overrides_json)
    tab = pr["table"]
    pop = tab[(tab.scenario == opts["demog"]) & tab.prov_code.isin(provs) & (tab.year >= S.base_year)].copy()
    ent, _ = D.entitlement(S, pop)
    if opts["ent"] != "central":
        ent["pop_entitlement_central"] = ent[f"pop_entitlement_{opts['ent']}"]
    panel = I.panel()
    bs = R.backtest_summary(R.service_backtest(S, panel), int(S.cfg["services"]["min_cutoffs_for_trend"]))
    method = {o: bs[(bs.outcome == o) & bs.chosen].method.iloc[0] for o in ["op_moph", "ip_moph", "adjrw"]}
    svc = R.service_projection(S, panel, pop, method)
    pkg = dict(_m5(overrides_json))
    if opts["estimator"] == "positive":
        pkg = pkg | {"beta": pkg["beta_pos"], "link": "log"}
    w = R.weights(S, tuple(opts["weights"]) if opts["weights"] else None, opts["inpatient"])
    idx, reg, sup = R.build_indices(S, base, pop, ent, svc, pkg, morb_mode=opts["morb"], age_mode=opts["age"], w=w,
                                    scenario_label=json.dumps(opts, ensure_ascii=False))
    cov = idx.attrs["cov"]
    mode = "grow_recent_cagr" if opts["resources"] == "grow" else "fixed_2025_count"
    res = R.resource_paths(S, base, pop, mode, mode)
    fb = R.Feedback(S, pkg, idx, res, cov, w)
    pool_table = SU.pool_path(S)
    lat, lon = centroids(provs)
    return Ctx(S=S, opts=opts, base=base, key=key, provs=provs, names=dict(zip(key.prov_code, key.province)),
               region=base.health_region.to_numpy(), H0=base.H0.to_numpy(float), rates=rates, departures=deps,
               dep=dep, pop=pop, ent=ent, svc=svc, svc_method=method, pkg=pkg, w=w, idx=idx, registry=reg,
               support=sup, res=res, cov=cov, fb=fb, pool=pool_table.available.to_numpy(float),
               pool_table=pool_table, dist=AL.great_circle(lat, lon),
               k=float(S.cfg["targets"]["reference_per_1000"]) / 1000.0)


def T_of(ctx, col, experiment, k=None):
    return SIM.targets_matrix(ctx.idx, col, experiment, ctx.k if k is None else k, ctx.S.base_year, ctx.S.years)


def eval_targets(ctx, experiment):
    return {n: T_of(ctx, c, experiment) for n, c in [("P", "D_P"), ("Pent", "D_Pent"), ("S", "D_S"), ("N", "D_N"),
                                                       ("B", "D_B")] if c in ctx.idx}


# ----------------------------------------------------------------------------- plan catalogue

def J(plan_id, family, col, mobility, experiment, group, cfg=None, ctx_opts=None, overrides=None, kind="milp",
      lam=0.0, variant="principal", notes="", k=None, stages=None):
    spec = SIM.PlanSpec(plan_id=plan_id, family=family, index_col=col, mobility=mobility, experiment=experiment,
                        feedback=f"lagged_lambda_{lam:g}" if kind == "sequential_nfb" else "none", lam=lam,
                        variant=variant, overrides=overrides or {}, notes=notes)
    return dict(job_id=plan_id, kind=kind, spec=spec, group=group, cfg=cfg or {}, ctx_opts=ctx_opts or {}, k=k,
                stages=stages)


FAM = [("P", "D_P"), ("S", "D_S"), ("N", "D_N")]
MOB = [("R", "recruitment_only"), ("RT", "recruitment_and_transfers")]


def catalogue(S, which=("principal", "variant", "sensitivity", "benchmark")) -> list[dict]:
    jobs = []
    a = S.cfg["allocation"]
    if "principal" in which:
        for f, col in FAM:
            for m, mob in MOB:
                jobs.append(J(f"{f}-{m}", f if f != "N" else "N-STD", col, mob, "common_total", "principal"))
        for f, col in FAM[1:]:
            for m, mob in MOB:
                jobs.append(J(f"{f}-{m}|B", f if f != "N" else "N-STD", col, mob, "fixed_base_conversion", "principal",
                              variant="experiment_B"))
    if "variant" in which:
        jobs.append(J("SQ-HIST", "status_quo", "D_P", "recruitment_only", "common_total", "variant", kind="status_quo_hist",
                      variant="historical_rule_unconstrained", notes="FY2021-2025 recruitment shares, largest remainder"))
        jobs.append(J("SQ-C", "status_quo", "D_P", "recruitment_only", "common_total", "variant", kind="status_quo_closest",
                      variant="historical_rule_constrained", notes="closest feasible (L1) to the historical rule"))
        for m, mob in MOB:
            jobs.append(J(f"Pent-{m}", "P_ent", "D_Pent", mob, "common_total", "variant", variant="entitlement"))
        for lam in S.cfg["feedback"]["response_strengths"]:
            jobs.append(J(f"NFB{lam:g}-R", "N-FB", "D_N", "recruitment_only", "common_total", "variant",
                          kind="sequential_nfb", lam=float(lam), variant="feedback"))
        jobs.append(J("NFB1-R|ols", "N-FB", "D_N", "recruitment_only", "common_total", "variant", kind="sequential_nfb",
                      lam=1.0, variant="feedback_ols_levels_attempt", cfg={"m5.response_model": "ols"}))
        jobs.append(J("NFB1-R|B", "N-FB", "D_N", "recruitment_only", "fixed_base_conversion", "variant",
                      kind="sequential_nfb", lam=1.0, variant="feedback_experiment_B"))
        jobs.append(J("NFB1-R|grow", "N-FB", "D_N", "recruitment_only", "common_total", "variant", kind="sequential_nfb",
                      lam=1.0, variant="feedback_beds_nurses_grow", ctx_opts={"resources": "grow"}))
        for m, mob in MOB:
            jobs.append(J(f"B-{m}", "B", "D_B", mob, "common_total", "variant", variant="expected_burden",
                          notes="projected age groups x BOD 2022 age-specific DALY rates (COVID-19 excluded)"))
        jobs.append(J("B-R|B", "B", "D_B", "recruitment_only", "fixed_base_conversion", "variant",
                      variant="expected_burden_experiment_B",
                      notes="target grows with expected DALYs (ageing) instead of the common population total"))
    if "sensitivity" in which:
        for pool in S.cfg["supply"]["annual_path_sensitivity"]:
            if int(pool) == int(S.cfg["supply"]["annual_path"]):
                continue
            for f, col in FAM:
                jobs.append(J(f"{f}-R|pool{pool}", f, col, "recruitment_only", "common_total", "sensitivity",
                              cfg={"supply.annual_path": pool}, variant=f"pool_{pool}"))
        for f, col in FAM:
            for m, mob in MOB:
                jobs.append(J(f"{f}-{m}|net", f, col, mob, "common_total", "sensitivity",
                              overrides={"cap_mode": "net_growth"}, variant="net_growth_cap"))
        for tau in [t for t in S.cfg["allocation"]["transfer_sensitivity"] if t not in (0.0, a["main_transfer_fraction"])]:
            for f, col in FAM:
                jobs.append(J(f"{f}-RT|tau{tau:g}", f, col, "recruitment_and_transfers", "common_total", "sensitivity",
                              overrides={"tau": tau, "nat_budget": tau / 2}, variant=f"transfer_{tau:g}"))
                jobs.append(J(f"{f}-RT|net|tau{tau:g}", f, col, "recruitment_and_transfers", "common_total", "sensitivity",
                              overrides={"tau": tau, "nat_budget": tau / 2, "cap_mode": "net_growth"},
                              variant=f"net_growth_cap_transfer_{tau:g}"))
        jobs.append(J("P-RT|net|surplus", "P", "D_P", "recruitment_and_transfers", "common_total", "sensitivity",
                      overrides={"cap_mode": "net_growth", "protect_mode": "surplus_only"}, variant="surplus_only"))
        jobs.append(J("P-RT|net|region", "P", "D_P", "recruitment_and_transfers", "common_total", "sensitivity",
                      overrides={"cap_mode": "net_growth", "network": "within_health_region"}, variant="regional_network"))
        for f, col in FAM:
            jobs.append(J(f"{f}-R|depnat", f, col, "recruitment_only", "common_total", "sensitivity",
                          ctx_opts={"departures": "national"}, variant="national_departure_rates"))
            jobs.append(J(f"{f}-R|ref0.5", f, col, "recruitment_only", "common_total", "sensitivity", k=0.5 / 1000,
                          variant="reference_0.5_per_1000"))
        for sc in ["low", "high"]:
            for f, col in FAM:
                jobs.append(J(f"{f}-R|mig_{sc}", f, col, "recruitment_only", "common_total", "sensitivity",
                              ctx_opts={"demog": sc}, variant=f"migration_{sc}"))
        for alt in S.cfg["services"]["weight_sensitivity"]:
            for f, col in FAM[1:]:
                jobs.append(J(f"{f}-R|w{alt[0]:g}_{alt[1]:g}", f, col, "recruitment_only", "common_total", "sensitivity",
                              ctx_opts={"weights": list(alt)}, variant=f"weights_{alt[0]:g}_{alt[1]:g}"))
        for f, col in FAM[1:]:
            jobs.append(J(f"{f}-R|ipdays", f, col, "recruitment_only", "common_total", "sensitivity",
                          ctx_opts={"inpatient": "ip_days"}, variant="inpatient_ip_days"))
        jobs.append(J("N-R|morb_trend", "N-STD", "D_N", "recruitment_only", "common_total", "sensitivity",
                      ctx_opts={"morb": "trend_bounded"}, variant="morbidity_trend_bounded"))
        jobs.append(J("N-R|age_held", "N-STD", "D_N", "recruitment_only", "common_total", "sensitivity",
                      ctx_opts={"morb": "age_held_2025", "age": "held_2025"}, variant="age_and_morbidity_held_2025"))
        jobs.append(J("N-R|positive", "N-STD", "D_N", "recruitment_only", "common_total", "sensitivity",
                      ctx_opts={"estimator": "positive"}, variant="m5_positive_mean_model"))
        jobs.append(J("B-R|yld", "B-yld", "D_Byld", "recruitment_only", "common_total", "sensitivity",
                      variant="burden_yld_only"))
        jobs.append(J("B-R|asr", "B-asr", "D_Basr", "recruitment_only", "common_total", "sensitivity",
                      variant="burden_age_standardized_no_ageing"))
        for m, mob in MOB:
            jobs.append(J(f"B-{m}|net", "B", "D_B", mob, "common_total", "sensitivity",
                          overrides={"cap_mode": "net_growth"}, variant="net_growth_cap"))
        jobs.append(J("P-R|maximin", "P", "D_P", "recruitment_only", "common_total", "sensitivity",
                      stages=("maximin", "shortfall", "distribution"), variant="fairness_maximin_then_shortfall"))
        jobs.append(J("Pent-R|ent_high", "P_ent", "D_Pent", "recruitment_only", "common_total", "sensitivity",
                      ctx_opts={"ent": "high"}, variant="entitlement_ratio_high"))
        repl = int(round(float(((SU.Departures(I.flow_rates(S), I.baseline(S).prov_code.to_numpy()).central()["d"]
                                 - SU.Departures(I.flow_rates(S), I.baseline(S).prov_code.to_numpy()).central()["r"])
                                * I.baseline(S).H0.to_numpy()).sum())))
        for m, mob in MOB:
            jobs.append(J(f"P-{m}|replacement", "P", "D_P", mob, "common_total", "sensitivity",
                          cfg={"supply.annual_path": repl}, overrides={"cap_mode": "net_growth"},
                          variant="replacement_only_decomposition",
                          notes=f"pool = expected net departures of the 2025 stock ({repl}); net-growth cap"))
    if "benchmark" in which:
        for f, col in FAM:
            jobs.append(J(f"{f}-R|nofloor", f, col, "recruitment_only", "common_total", "benchmark",
                          overrides={"floor": 0}, variant="no_universal_floor"))
        jobs.append(J("P-R|ref0.5|nofloor", "P", "D_P", "recruitment_only", "common_total", "benchmark", k=0.5 / 1000,
                      overrides={"floor": 0}, variant="reference_0.5_no_floor"))
        for f, col in FAM:
            jobs.append(J(f"{f}-R|greedy", f, col, "recruitment_only", "common_total", "benchmark", kind="greedy",
                          variant="heuristic_benchmark"))
        jobs.append(J("P-R|rolling", "P", "D_P", "recruitment_only", "common_total", "benchmark", kind="rolling",
                      variant="deterministic_annual_replanning"))
        jobs.append(J("P-R|tangent_fine", "P", "D_P", "recruitment_only", "common_total", "benchmark",
                      overrides={"tangent_step": float(S.cfg["allocation"]["tangent_step_check"])},
                      variant="finer_tangent_grid"))
        for cm in ["gross_arrivals", "net_growth"]:
            jobs.append(J(f"INV|{cm}", "P", "D_P", "recruitment_only", "common_total", "benchmark", kind="inverse",
                          overrides={"cap_mode": cm}, variant=f"inverse_{cm}"))
    return jobs


# ----------------------------------------------------------------------------- job execution

def _status(sol_status):
    return "exploratory_policy_scenario" if sol_status == "solved" else sol_status


def run_job(job) -> dict:
    """Executed in a worker process.  Returns plain data (no context objects)."""
    t0 = time.time()
    base_over = job.get("base_cfg", {})
    ov = json.dumps(base_over | job["cfg"], sort_keys=True)
    ctx = context(ov, json.dumps(job["ctx_opts"], sort_keys=True))
    S = ctx.S
    spec = job["spec"]
    kind = job["kind"]
    k = job["k"] if job["k"] is not None else ctx.k
    out = dict(job_id=job["job_id"], kind=kind, group=job["group"], spec=asdict(spec),
               incumbent_from=job.get("incumbent_from", ""))
    try:
        if kind in ("milp", "status_quo_closest", "status_quo_hist", "greedy", "rolling"):
            T = T_of(ctx, spec.index_col, spec.experiment, k)
            kw = {"stages": job["stages"]} if job["stages"] else {}
            pb = SIM.make_problem(ctx, spec, T, **kw)
            if kind == "milp":
                inc = job.get("incumbent")
                if pb.transfers and inc is None:
                    # the recruitment-only optimum is feasible for the transfer problem: pass it as an incumbent
                    pbR = SIM.make_problem(ctx, spec, T, transfers=False, stages=("shortfall",))
                    sR = AL.solve(pbR)
                    if sR.status == "solved":
                        z0 = np.zeros_like(sR.x)
                        inc = (sR.x, z0, z0.copy())
                sol = AL.solve(pb, incumbent=inc)
            elif kind == "status_quo_hist":
                sh = I.recruitment_shares(S).set_index("prov_code").reindex(ctx.provs).share.to_numpy()
                x = np.array([AL.apportion(int(a_), sh) for a_ in pb.A])
                z = np.zeros_like(x)
                sol = AL.Solution(status="solved", x=x, zin=z, zout=z, H=AL.trajectory(pb, x, z, z), u=pb.A - x.sum(1),
                                  diagnostics=dict(rule="historical shares, unconstrained"))
            elif kind == "status_quo_closest":
                sh = I.recruitment_shares(S).set_index("prov_code").reindex(ctx.provs).share.to_numpy()
                pb.reference_x = np.array([AL.apportion(int(a_), sh) for a_ in pb.A])
                sol = AL.solve(pb, objective="closest_to_reference")
                if sol.status == "solved":
                    sol.diagnostics["l1_distance_to_historical_rule"] = float(np.abs(sol.x - pb.reference_x).sum())
            elif kind == "greedy":
                g = AL.greedy(pb)
                z = np.zeros_like(g["x"])
                sol = AL.Solution(status="solved", x=g["x"], zin=z, zout=z, H=g["H"], u=g["unplaced"],
                                  diagnostics=dict(objective_exact=g["objective_exact"], seconds=g["seconds"],
                                                   heuristic="myopic greedy, exact per year"))
            else:  # rolling: deterministic annual replanning with the same central information
                r = SIM.sequential(ctx, spec, lambda t, Hp: (T[t:], {}))
                sol = AL.Solution(status=r["status"], x=r.get("x"), zin=r.get("zin"), zout=r.get("zout"), H=r.get("H"),
                                  u=None, diagnostics=dict(seconds=r.get("seconds")))
                sol.u = pb.A - sol.x.sum(1) if sol.x is not None else None
            out.update(_package(ctx, spec, pb, sol, kind))
        elif kind == "sequential_nfb":
            lam = spec.lam
            fb = ctx.fb
            exp_ = spec.experiment
            common = ctx.idx.groupby("year").population.sum().reindex(S.years).to_numpy() * k
            logrows = []

            def tf(t, Hp):
                Ds, etas = [], []
                for y in S.years[t:]:
                    Dfb, eta = fb.nfb_D(y, Hp, lam)
                    Ds.append(Dfb); etas.append(eta)
                Ds = np.array(Ds)
                if exp_ == "common_total":
                    Trem = common[t:, None] * Ds / Ds.sum(1, keepdims=True)
                else:
                    Trem = k * Ds
                share = Trem[0] / Trem[0].sum()
                gainB = etas[0] * Trem[0] / Hp
                gainA = gainB * (1 - share)
                logrows.append(dict(year=S.years[t], eta_mean=float(np.average(etas[0], weights=Trem[0])),
                                    eta_min=float(etas[0].min()), eta_max=float(etas[0].max()),
                                    gain_B_mean=float(np.average(gainB, weights=Hp)), gain_B_max=float(gainB.max()),
                                    gain_A_mean=float(np.average(gainA, weights=Hp)),
                                    provinces_gain_B_ge_1=int((gainB >= 1).sum())))
                return Trem, {"eta_mean": float(np.average(etas[0], weights=Trem[0]))}
            r = SIM.sequential(ctx, spec, tf)
            if r["status"] != "solved":
                out.update(status=r["status"], diagnostics=r.get("diagnostics", {}))
            else:
                pb = SIM.make_problem(ctx, spec, r["T"])
                sol = AL.Solution(status="solved", x=r["x"], zin=r["zin"], zout=r["zout"], H=r["H"],
                                  u=pb.A - r["x"].sum(1), diagnostics=dict(seconds=r["seconds"]))
                out.update(_package(ctx, spec, pb, sol, kind))
                out["feedback_log"] = pd.DataFrame(logrows).assign(plan_id=spec.plan_id, lam=lam)
        elif kind == "inverse":
            out.update(inverse(ctx, spec, k))
    except Exception as e:  # a failed job must be visible, never silently dropped
        import traceback
        out.update(status="blocked_for_specific_reason", error=f"{type(e).__name__}: {e}",
                   traceback=traceback.format_exc())
    out["seconds"] = time.time() - t0
    return out


def _package(ctx, spec, pb, sol, kind) -> dict:
    out = dict(status=_status(sol.status), solver_status=sol.status, stages=sol.stages, diagnostics=sol.diagnostics)
    if sol.status != "solved":
        out["ledger"] = None
        return out
    if kind != "status_quo_hist":
        chk = AL.check(pb, sol)
    else:
        chk = AL.check(pb, sol)
        chk["note"] = "historical rule evaluated without enforcing the current constraints"
    out["check"] = chk
    fl = AL.binding_flags(pb, sol)
    reasons = AL.explanation(pb, sol, fl)
    if kind == "status_quo_hist":
        reasons = np.full(sol.x.shape, "historical recruitment share (FY2021-2025), not optimised", dtype=object)
    elif kind == "greedy":
        reasons = np.full(sol.x.shape, "greedy benchmark (myopic one-year shortfall reduction)", dtype=object)
    status = out["status"]
    if kind == "status_quo_hist" and not chk["all_ok"]:
        status = "exploratory_policy_scenario (violates current constraints: " + \
                 ", ".join(k_ for k_, v in chk.items() if v is False) + ")"
    led = SIM.ledger(ctx, spec, pb, sol.x, sol.zin, sol.zout, status, eval_targets(ctx, spec.experiment), fl, reasons)
    out["ledger"] = led
    out["routes"] = SIM.routes_table(ctx, spec, pb, sol.zin, sol.zout) if pb.transfers and sol.zout.sum() > 0 else None
    out.update(x=sol.x, zin=sol.zin, zout=sol.zout, H=sol.H, T=pb.T, u=np.asarray(sol.u, float), pool=pb.A.copy(),
               cap_mode=pb.cap_mode, transfers=pb.transfers,
               objective_exact=AL.objective_exact(pb, sol.H), imbalance=AL.imbalance(pb, sol.H),
               binding=dict(cap=float(fl["cap_binding"].mean()), floor=float(fl["floor_binding"].mean()),
                            transfer_cap=float(np.mean(fl["transfer_cap_binding"])),
                            protection=float(np.mean(fl["protection_binding"]))))
    return out


def inverse(ctx, spec, k):
    """Minimum ramp-limited appointment path so that every province reaches the reference by 2040
    (LP relaxation of the recruitment-only problem; integers rounded up).  If infeasible, the
    maximum common attainment level reachable by 2040 under the caps with the ramp-limited pool."""
    import scipy.sparse as sp
    from scipy.optimize import Bounds, LinearConstraint, milp
    S = ctx.S
    T = T_of(ctx, spec.index_col, spec.experiment, k)
    pb = SIM.make_problem(ctx, spec, T)
    ramp = float(S.cfg["inverse"]["ramp_fraction"])
    base_pool = float(ctx.pool[0])
    P, nT = pb.P, pb.nT
    nx = nT * P
    iX = lambda t: t * P + np.arange(P)
    iH = lambda t: nx + t * P + np.arange(P)
    iA = 2 * nx + np.arange(nT)
    ith = 2 * nx + nT
    nvar = ith + 1
    B = AL._Builder()
    ones = np.ones(P)
    for t in range(nT):
        a = 1 - pb.d[t] + pb.r[t]
        if t == 0:
            B.add(np.c_[iH(t), iX(t)], np.c_[ones, -ones], a * pb.H0, a * pb.H0)
        else:
            B.add(np.c_[iH(t), iH(t - 1), iX(t)], np.c_[ones, -a, -ones], 0, 0)
        B.add(np.r_[iX(t), iA[t]][None], np.r_[ones, -1.0][None], 0, 0)
        if pb.cap_mode == "gross_arrivals":
            coef = pb.cap - pb.r[t]
            if t == 0:
                B.add(iX(t)[:, None], ones[:, None], -np.inf, coef * pb.H0)
            else:
                B.add(np.c_[iX(t), iH(t - 1)], np.c_[ones, -coef], -np.inf, 0)
        else:
            if t == 0:
                B.add(iH(t)[:, None], ones[:, None], -np.inf, (1 + pb.cap) * pb.H0)
            else:
                B.add(np.c_[iH(t), iH(t - 1)], np.c_[ones, -(1 + pb.cap) * ones], -np.inf, 0)
        # ramp
        if t == 0:
            B.add(np.array([[iA[0]]]), np.array([[1.0]]), -np.inf, base_pool * (1 + ramp))
        else:
            B.add(np.array([[iA[t], iA[t - 1]]]), np.array([[1.0, -(1 + ramp)]]), -np.inf, 0)
    A_, lo, hi = B.matrix(nvar)
    Acsr = A_.tocsr()
    ramp_rows = np.zeros(A_.shape[0], bool)
    for i in range(A_.shape[0]):
        cols = Acsr.indices[Acsr.indptr[i]:Acsr.indptr[i + 1]]
        ramp_rows[i] = bool(len(cols)) and np.all(cols >= 2 * nx) and np.all(cols < ith)
    last = iH(nT - 1)
    prov_rows = sp.csr_matrix((np.r_[np.ones(P), -T[-1]], (np.r_[np.arange(P), np.arange(P)], np.r_[last, np.full(P, ith)])),
                              shape=(P, nvar))
    nat_row = sp.csr_matrix((np.r_[np.ones(P), -T[-1].sum()], (np.zeros(P + 1, int), np.r_[last, ith])), shape=(1, nvar))
    lb = np.zeros(nvar); ub = np.full(nvar, np.inf)
    lb[: nx] = pb.floor
    ub[ith] = 10.0

    def run(crit, ramp_on, mode):
        keep = np.ones(A_.shape[0], bool) if ramp_on else ~ramp_rows
        extra = prov_rows if crit == "province" else nat_row
        Am = sp.vstack([Acsr[keep], extra]).tocsr()
        l_ = np.r_[lo[keep], np.zeros(extra.shape[0])]
        h_ = np.r_[hi[keep], np.full(extra.shape[0], np.inf)]
        lb_ = lb.copy(); c = np.zeros(nvar)
        if mode == "min_pool":
            lb_[ith] = 1.0
            c[iA] = 1.0
        else:
            c[ith] = -1.0
        r = milp(c, constraints=LinearConstraint(Am, l_, h_), bounds=Bounds(lb_, ub))
        return r

    rows, summ_rows = [], []
    for crit in ["province", "national"]:
        for ramp_on in [True, False]:
            r1 = run(crit, ramp_on, "min_pool")
            r2 = run(crit, ramp_on, "max_theta")
            tag = f"{crit}|{'ramp' if ramp_on else 'no_ramp'}"
            summ_rows.append(dict(plan_id=spec.plan_id, cap_mode=pb.cap_mode, criterion=crit, ramp_limited=ramp_on,
                                  ramp_fraction=ramp if ramp_on else np.nan, base_pool=base_pool,
                                  reference_reachable_by_2040=r1.x is not None,
                                  total_appointments_required=float(np.ceil(r1.x[iA] - 1e-6).sum()) if r1.x is not None else np.nan,
                                  pool_2040_required=float(np.ceil(r1.x[iA[-1]] - 1e-6)) if r1.x is not None else np.nan,
                                  max_attainment_2040=float(r2.x[ith]) if r2.x is not None else np.nan,
                                  binding_province=(ctx.names[ctx.provs[int(np.argmin(r2.x[last] / T[-1]))]]
                                                    if (r2.x is not None and crit == "province") else ""),
                                  note="LP relaxation of the recruitment-only problem; conditional on the caps and the ramp; "
                                       "educational and funded-post capacity unknown"))
            for t in range(nT):
                rows.append(dict(plan_id=spec.plan_id, cap_mode=pb.cap_mode, run=tag, year_ce=S.years[t],
                                 year_be=S.years[t] + 543,
                                 required_pool=float(np.ceil(r1.x[iA[t]] - 1e-6)) if r1.x is not None else np.nan,
                                 pool_at_max_attainment=float(r2.x[iA[t]]) if r2.x is not None else np.nan))
    summ = pd.DataFrame(summ_rows)
    return dict(status="solved", inverse_path=pd.DataFrame(rows), inverse_summary=summ)


def r_counterpart(job_id: str) -> str:
    """The recruitment-only plan with the same targets and constraints as a transfer plan."""
    head, *tail = job_id.split("|")
    tail = [t for t in tail if not t.startswith("tau") and t not in ("surplus", "region")]
    return "|".join([head.replace("-RT", "-R")] + tail)


def attach_incumbents(jobs, results: dict):
    """Give every transfer plan the finished recruitment-only plan as a feasible incumbent."""
    for j in jobs:
        if j["kind"] == "milp" and j["spec"].mobility == "recruitment_and_transfers":
            r = results.get(r_counterpart(j["job_id"]))
            if r is not None and r.get("x") is not None:
                z = np.zeros_like(r["x"])
                j["incumbent"] = (r["x"], z, z.copy())
                j["incumbent_from"] = r["job_id"]


def run_jobs(jobs, workers=None, base_cfg=None):
    workers = workers or max(1, min(9, (os.cpu_count() or 2) - 1))
    for j in jobs:
        j["base_cfg"] = base_cfg or {}
    # slow jobs first so the pool stays busy
    order = sorted(range(len(jobs)), key=lambda i: 0 if ("RT" in jobs[i]["job_id"] or jobs[i]["kind"] in
                                                         ("sequential_nfb", "rolling")) else 1)
    if workers == 1:
        return [run_job(jobs[i]) for i in order]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(run_job, [jobs[i] for i in order]))
    return res


# ----------------------------------------------------------------------------- stage: inputs

def stage_inputs(S) -> dict:
    """Input contract, readiness, projections, supply, indices, M5 checks; tables and claims."""
    Rg = Registry(S, "5_1")
    ov = json.dumps(S.overrides, sort_keys=True)
    ctx = context(ov, "{}")
    by = S.base_year
    art = I.artifact_register()
    Rg.table("T5_INPUT_CONTRACT", art, "สัญญาข้อมูลนำเข้า: ไฟล์จากบทที่ 4 และ SHA-256 ที่ใช้", folder="validation")
    Rg.table("T5_EFFECTIVE_CONFIG", S.effective_table(), "ค่าตั้งที่ใช้จริง พร้อมสถานะที่มา (สังเกต/ประมาณ/ตัวอย่าง/ทางเลือกนโยบาย)")
    inv = I.readiness_inventory(S, ctx.rates, ctx.base)
    Rg.table("T5_DATA_READINESS", inv, "ความพร้อมของข้อมูลนำเข้า และทางเลือกเมื่อขาดข้อมูล", main=True)
    b = ctx.base.copy()
    Rg.table("T5_BASELINE_PROVINCES", b, f"ค่าเริ่มต้นรายจังหวัด พ.ศ. {by + 543}")
    Rg.table("T5_FLOW_RATES", ctx.rates, "อัตราเหตุการณ์ต่อบุคลากรตั้งต้น (ปีงบ 2564–2568) ก่อนและหลังการรวมกำลังแบบ empirical Bayes")
    nsf = I.national_stock_flow(S)
    Rg.table("T5_NATIONAL_STOCK_FLOW", nsf, "การกระทบยอดจำนวนคงอยู่กับเหตุการณ์ที่บันทึก ระดับประเทศ (76 จังหวัด)", folder="validation")
    sfb = SU.stock_flow_backtest(S, ctx.rates, ctx.provs, I.stock_series(), I.flow_events_province())
    Rg.table("T5_STOCK_FLOW_BACKTEST", sfb, "ตรวจย้อนหลังแบบมีเงื่อนไข: จำนวนคงอยู่จำลองเทียบจริง 2564–2568 (ใช้การรับเข้าจริง)", folder="validation")
    pbt, pdet = D.backtest(S)
    Rg.table("T5_POP_BACKTEST", pbt, "ตรวจย้อนหลังการฉายประชากร 2562→2568", folder="validation", main=True)
    Rg.table("T5_POP_BACKTEST_PROVINCES", pdet, "ผลตรวจย้อนหลังการฉายประชากรรายจังหวัด", folder="validation")
    pr = _projections(ov)
    Rg.table("T5_POP_PROJECTION", pr["table"], "ประชากรฉายรายจังหวัด-ปี ตามฉากทัศน์การย้ายถิ่น (รวมกรุงเทพฯ เป็นขอบเขตภายนอก)", parquet=True)
    Rg.table("T5_POP_COMPONENTS", pr["components"], "องค์ประกอบการเปลี่ยนแปลงประชากร: การเกิด และการเปลี่ยนแปลงของรุ่นที่มีอยู่ (ตาย+ย้ายถิ่นสุทธิรวมกัน)")
    _, rat = D.entitlement(S, ctx.pop)
    Rg.table("T5_ENTITLEMENT_RATIOS", rat, "อัตราส่วนทะเบียนสิทธิ/ทะเบียนราษฎร รายจังหวัด และขอบเขตที่ใช้")
    bt = R.service_backtest(S, I.panel())
    bs = R.backtest_summary(bt, int(S.cfg["services"]["min_cutoffs_for_trend"]))
    Rg.table("T5_SERVICE_BACKTEST", bs, "ตรวจย้อนหลังวิธีฉายอัตราบริการ (MAPE รายจังหวัด)", folder="validation", main=True)
    Rg.table("T5_SERVICE_PROJECTION", ctx.svc, "บริการฉายรายจังหวัด-ปี (อัตราตามวิธีที่เลือก × ประชากรฉาย)")
    Rg.table("T5_M5_COEFFICIENTS", I.m5_coefficient_table(ctx.pkg), "สัมประสิทธิ์ M5 ที่ประมาณซ้ำ ตรงกับบทที่ 4 พร้อม CR1 SE และช่วง bootstrap", folder="validation")
    sup = ctx.support.copy()
    supy = sup.groupby("year").agg(share_extrapolation=("extrapolation", "mean"),
                                   share_age60_out=("out_s3_60+", "mean"),
                                   share_joint_out=("joint_outside", "mean")).reset_index()
    Rg.table("T5_M5_SUPPORT_BY_YEAR", supy, "สัดส่วนจังหวัดที่ตัวแปรสุขภาพอยู่นอกช่วงข้อมูลที่ใช้ประมาณ M5", folder="validation", main=True)
    Rg.table("T5_INDICES", ctx.idx.drop(columns=[c for c in ctx.idx.columns if c.startswith("conv")]),
             "ดัชนีความรับผิดชอบรายจังหวัด-ปีของทุกตระกูล (หน่วยเทียบเท่าประชากร ด้วยสเกลคงที่ปี 2568)", parquet=True)
    Rg.table("T5_DENOMINATOR_REGISTRY", ctx.registry, "ทะเบียนตัวหาร: ที่มา หน่วย การปรับสเกล และการตีความ", main=True)
    if "D_B" in ctx.idx:
        # Aggregate family B inputs, also read by the Workforce Lab package (no personal data).
        bi = R.burden_inputs()
        bod = pd.concat([bi["rate_daly"].stack().rename("rate_daly"), bi["rate_yld"].stack().rename("rate_yld")],
                        axis=1).reset_index()
        bod["asr_daly_per100k"] = bod.prov_code.map(bi["asr_daly"])
        Rg.table("T5_BOD_RATES", bod, "อัตรา DALY และ YLD ต่อคน-ปี รายจังหวัด × 8 กลุ่มอายุ (BOD 2565 ไม่รวม COVID-19) "
                 "และอัตรา DALY ปรับมาตรฐานอายุต่อแสนคน ที่ใช้สร้าง family B")
    # supply modes (the direct mode is used; the other two are shown with their illustrative parameters)
    pools = []
    for mode in ["available_appointments", "national_graduates", "student_intake"]:
        pools.append(SU.pool_path(C.load(S.overrides | {"supply.input_mode": mode})))
    Rg.table("T5_POOL_PATHS", pd.concat(pools, ignore_index=True), "เส้นทางแพทย์ที่พร้อมจัดสรร ตามสามรูปแบบการป้อนข้อมูล (ค่าพารามิเตอร์เป็นตัวอย่าง)")
    # feedback diagnostics at the baseline
    fb = ctx.fb
    rows = []
    for lam in S.cfg["feedback"]["response_strengths"]:
        Dfb, eta = fb.nfb_D(S.years[0], ctx.H0, float(lam))
        Tb = ctx.k * Dfb
        rows.append(pd.DataFrame(dict(lam=float(lam), prov_code=ctx.provs, eta=eta, target_B=Tb, H0=ctx.H0,
                                      gain_B=eta * Tb / ctx.H0,
                                      gain_A=eta * Tb / ctx.H0 * (1 - Tb / Tb.sum()))))
    fbd = pd.concat(rows, ignore_index=True)
    Rg.table("T5_FEEDBACK_ELASTICITY_2026", fbd, "ความยืดหยุ่นเฉพาะที่ของตัวหาร N-FB ต่อจำนวนแพทย์ และกำไรป้อนกลับต่อเป้าหมาย (การตัดสินใจปี 2569; การทดลอง B ค่าเฉลี่ยไม่ถ่วงน้ำหนัก จึงต่างจากตัวเลขในรายงานที่ใช้การทดลอง A ถ่วงด้วยจำนวนแพทย์ตาม T5_FEEDBACK_LOG)")
    # claims
    k = ctx.key
    Rg.claim("c51_H0_total", ctx.H0.sum(), "int", "คน", "T5_BASELINE_PROVINCES")
    Rg.claim("c51_pop_2025", ctx.pop[ctx.pop.year == by].population.sum(), "int", "คน")
    for sc in ["central", "low", "high"]:
        z = pr["table"][(pr["table"].scenario == sc) & pr["table"].prov_code.isin(ctx.provs)]
        p40 = z[z.year == S.years[-1]].population.sum()
        Rg.claim(f"c51_pop_2040_{sc}", p40, "int", "คน")
        Rg.claim(f"c51_pop_change_pct_{sc}", 100 * (p40 / z[z.year == by].population.sum() - 1), "{:.1f}", "%")
    zc = pr["table"][(pr["table"].scenario == "central") & pr["table"].prov_code.isin(ctx.provs)]
    for y in [by, S.years[-1]]:
        zz = zc[zc.year == y]
        Rg.claim(f"c51_share60_{y}", 100 * zz["n3_60+"].sum() / zz.population.sum(), "{:.1f}", "%")
    Rg.claim("c51_share60_train_max", 100 * ctx.pkg["support"].set_index("variable").loc["s3_60+", "max"], "{:.1f}", "%")
    for y in [2030, 2035, S.years[-1]]:
        Rg.claim(f"c51_extrap_share_{y}", 100 * supy.set_index("year").loc[y, "share_extrapolation"], "{:.0f}", "%")
    hp = pbt.set_index("method")
    Rg.claim("c51_popbt_hp_mape", hp.loc["hamilton_perry_national_control", "mape_total_pct"], "{:.2f}", "%")
    Rg.claim("c51_popbt_nochange_mape", hp.loc["no_change_2019", "mape_total_pct"], "{:.2f}", "%")
    Rg.claim("c51_popbt_linear_mape", hp.loc["linear_trend_totals_2013_2019", "mape_total_pct"], "{:.2f}", "%")
    Rg.claim("c51_popbt_hp_nat", hp.loc["hamilton_perry_national_control", "national_76_error_pct"], "{:.2f}", "%")
    Rg.claim("c51_popbt_hp_s60", hp.loc["hamilton_perry_national_control", "mae_share60_pp"], "{:.2f}", "จุดร้อยละ")
    Rg.claim("c51_popbt_nochange_s60", hp.loc["no_change_2019", "mae_share60_pp"], "{:.2f}", "จุดร้อยละ")
    comp = pr["components"][(pr["components"].scenario == "central") & pr["components"].prov_code.isin(ctx.provs)]
    Rg.claim("c51_births_2026", comp[comp.year == S.years[0]].births.sum(), "int", "คน")
    Rg.claim("c51_births_2040", comp[comp.year == S.years[-1]].births.sum(), "int", "คน")
    agg = ctx.rates.groupby("cause")[["events", "exposure"]].sum()
    for c in ["resignation", "retirement", "transfer_out", "death", "disciplinary", "reinstatement", "transfer_in",
              "recruitment_hiring"]:
        Rg.claim(f"c51_rate_{c}", 100 * agg.loc[c, "events"] / agg.loc[c, "exposure"], "{:.2f}", "ต่อ 100 คน-ปี")
    Rg.claim("c51_exit_prob_nat", 100 * float((ctx.dep["d"] * ctx.H0).sum() / ctx.H0.sum()), "{:.2f}", "%")
    Rg.claim("c51_reentry_nat", 100 * float((ctx.dep["r"] * ctx.H0).sum() / ctx.H0.sum()), "{:.2f}", "%")
    Rg.claim("c51_exp_departures_2026", float((ctx.dep["d"] * ctx.H0).sum()), "int", "คน")
    Rg.claim("c51_exp_reentries_2026", float((ctx.dep["r"] * ctx.H0).sum()), "int", "คน")
    rs = ctx.rates[ctx.rates.cause == "resignation"]
    Rg.claim("c51_resig_raw_p10", 100 * rs.rate_raw.quantile(.1), "{:.1f}", "ต่อ 100")
    Rg.claim("c51_resig_raw_p90", 100 * rs.rate_raw.quantile(.9), "{:.1f}", "ต่อ 100")
    Rg.claim("c51_resig_pooled_p10", 100 * rs.rate_pooled.quantile(.1), "{:.1f}", "ต่อ 100")
    Rg.claim("c51_resig_pooled_p90", 100 * rs.rate_pooled.quantile(.9), "{:.1f}", "ต่อ 100")
    Rg.claim("c51_resig_shrink_median", 100 * rs.shrinkage.median(), "{:.0f}", "%")
    z = nsf[nsf.fiscal_year.between(2021, 2025)]
    Rg.claim("c51_sf_dstock_2125", z.d_stock.sum(), "int", "คน")
    Rg.claim("c51_sf_net_2125", z.net_recorded.sum(), "int", "ครั้ง")
    Rg.claim("c51_sf_resid_2125", z.residual.sum(), "int", "คน")
    Rg.claim("c51_sf_resid_2020", nsf.set_index("fiscal_year").loc[2020, "residual"], "int", "คน")
    Rg.claim("c51_recruit_mean_2125", z.recruitment.mean(), "int", "ครั้งต่อปี")
    Rg.claim("c51_exits_mean_2125", z.exits.mean(), "int", "ครั้งต่อปี")
    Rg.claim("c51_sfb_2025_resid", sfb.set_index("year").loc[2025, "residual"], "int", "คน")
    Rg.claim("c51_sfb_2025_mape", sfb.set_index("year").loc[2025, "mape_province_pct"], "{:.1f}", "%")
    for o in ["op_moph", "ip_moph", "adjrw"]:
        q = bs[bs.outcome == o]
        ch = q[q.chosen].iloc[0]
        Rg.text(f"c51_svc_method_{o}", {"constant_last": "อัตราปีล่าสุดคงที่", "mean_last3": "ค่าเฉลี่ยสามปีล่าสุด",
                                         "trend_last5_damped": "แนวโน้มห้าปีแบบหน่วง"}[ch.method])
        Rg.claim(f"c51_svc_mape_{o}", ch.mape_pct, "{:.1f}", "%")
        Rg.claim(f"c51_svc_best_mape_{o}", q.mape_pct.min(), "{:.1f}", "%")
        Rg.claim(f"c51_svc_cutoffs_{o}", q.cutoffs.max(), "{:.0f}", "จุดตัด")
    ix = ctx.idx
    g = ix.groupby("year")[["D_P", "D_Pent", "D_S", "D_N", "D_B", "D_Basr", "B_S", "B_N"]].sum()
    for c in ["D_P", "D_Pent", "D_S", "D_N", "D_B", "D_Basr"]:
        Rg.claim(f"c51_{c}_growth_pct", 100 * (g.loc[S.years[-1], c] / g.loc[by, c] - 1), "{:.1f}", "%")
    for o in ["op_moph", "ip_moph", "adjrw"]:
        Rg.claim(f"c51_minrate_std_{o}", ix[f"rate_std_{o}"].min(), "{:.3f}", "ต่อคน")
    Rg.claim("c51_nstd_positive", float(ix.positive_N.all()), "{:.0f}", "")
    # B: expected burden relative to P in the base year; growth of raw expected DALYs (ageing at fixed rates)
    gb = ix.groupby("year")[["B_B", "population"]].sum()
    Rg.claim("c51_B_dalys_2025", gb.loc[by, "B_B"], "int", "DALY")
    Rg.claim("c51_B_dalys_2040", gb.loc[S.years[-1], "B_B"], "int", "DALY")
    Rg.claim("c51_B_dalys_growth_pct", 100 * (gb.loc[S.years[-1], "B_B"] / gb.loc[by, "B_B"] - 1), "{:.1f}", "%")
    Rg.claim("c51_B_dalys_per_person_2025", gb.loc[by, "B_B"] / gb.loc[by, "population"], "{:.3f}", "DALY ต่อคน")
    Rg.claim("c51_B_dalys_per_person_2040", gb.loc[S.years[-1], "B_B"] / gb.loc[S.years[-1], "population"], "{:.3f}", "DALY ต่อคน")
    zb = ix[ix.year == by].set_index("prov_code")
    rb = (zb.D_B / zb.D_P).sort_values()
    Rg.claim("c51_B_ratio_min", rb.iloc[0], "{:.2f}", "")
    Rg.claim("c51_B_ratio_max", rb.iloc[-1], "{:.2f}", "")
    Rg.text("c51_B_ratio_min_prov", ctx.names[rb.index[0]])
    Rg.text("c51_B_ratio_max_prov", ctx.names[rb.index[-1]])
    Rg.text("c51_B_top_gain", ", ".join(f"{ctx.names[p]} (+{zb.D_B[p] - zb.D_P[p]:,.0f})"
                                        for p in (zb.D_B - zb.D_P).sort_values(ascending=False).index[:3]))
    Rg.text("c51_B_top_loss", ", ".join(f"{ctx.names[p]} ({zb.D_B[p] - zb.D_P[p]:,.0f})"
                                        for p in (zb.D_B - zb.D_P).sort_values().index[:3]))
    fb1 = fbd[fbd.lam == 1.0]
    Rg.claim("c51_eta_lam1_mean", float(np.average(fb1.eta, weights=fb1.target_B)), "{:.2f}", "")
    Rg.claim("c51_eta_lam1_min", fb1.eta.min(), "{:.2f}", "")
    Rg.claim("c51_eta_lam1_max", fb1.eta.max(), "{:.2f}", "")
    Rg.claim("c51_gainB_lam1_mean", float(np.average(fb1.gain_B, weights=fb1.H0)), "{:.2f}", "")
    Rg.claim("c51_gainB_lam1_n_ge1", float((fb1.gain_B >= 1).sum()), "{:.0f}", "จังหวัด")
    jp = ctx.pkg["names"].index("log_physicians")
    for o in ["op_moph", "ip_moph", "adjrw"]:
        Rg.claim(f"c51_beta_phys_{o}", ctx.pkg["beta"][o][jp], "{:.3f}", "")
        Rg.claim(f"c51_beta_nurse_{o}", ctx.pkg["beta"][o][ctx.pkg["names"].index("log_nurses")], "{:.3f}", "")
        Rg.claim(f"c51_beta_s60_{o}", ctx.pkg["beta"][o][ctx.pkg["names"].index("s3_60+")], "{:.3f}", "")
    for o in ["op_moph", "ip_moph", "adjrw"]:
        Rg.claim(f"c51_bpos_phys_{o}", ctx.pkg["beta_pos"][o][jp], "{:.2f}", "")
    Rg.claim("c51_m5_repro_max", max(ctx.pkg["reproduction"].values()), "{:.1e}", "")
    Rg.claim("c51_pool", ctx.pool[0], "int", "คนต่อปี")
    Rg.claim("c51_base_be", by + 543, "{:.0f}", "พ.ศ.")
    Rg.claim("c51_first_be", S.years[0] + 543, "{:.0f}", "พ.ศ.")
    Rg.claim("c51_last_be", S.years[-1] + 543, "{:.0f}", "พ.ศ.")
    Rg.claim("c51_n_years", len(S.years), "{:.0f}", "ปี")
    Rg.claim("c51_ref_per1000", float(S.cfg["targets"]["reference_per_1000"]), "{:g}", "คนต่อประชากร 1,000")
    Rg.claim("c51_cap_pct", 100 * float(S.cfg["allocation"]["cap_fraction_of_opening_stock"]), "{:.0f}", "%")
    Rg.claim("c51_transfer_pct", 100 * float(S.cfg["allocation"]["main_transfer_fraction"]), "{:.0f}", "%")
    Rg.claim("c51_floor", float(S.cfg["allocation"]["universal_new_appointment_floor"]), "{:.0f}", "คน")
    Rg.claim("c51_cap_2026_total", float(np.floor((S.cfg["allocation"]["cap_fraction_of_opening_stock"] - ctx.dep["r"]) * ctx.H0 + 1e-9).sum()), "int", "คน")
    Rg.claim("c51_target_2025", ctx.k * ctx.pop[ctx.pop.year == by].population.sum(), "int", "คน")
    Rg.claim("c51_attain_2025", ctx.H0.sum() / (ctx.k * ctx.pop[ctx.pop.year == by].population.sum()), "{:.2f}", "")
    Rg.claim("c51_steady_state", float(ctx.pool[0] / ((ctx.dep["d"] - ctx.dep["r"]) * ctx.H0).sum() * ctx.H0.sum()), "int", "คน",
             note="stock at which expected net departures equal the pool, national hazard mix of 2025")
    man = Rg.finalize()
    return dict(ctx=ctx, manifest=man)


# ----------------------------------------------------------------------------- stage: plans

def stage_plans(S, workers=None, which=("principal", "variant", "sensitivity", "benchmark"), jobs=None) -> dict:
    t0 = time.time()
    jobs = jobs or catalogue(S, which)
    rt = [j for j in jobs if j["kind"] == "milp" and j["spec"].mobility == "recruitment_and_transfers"]
    first = [j for j in jobs if j not in rt]
    res = run_jobs(first, workers, base_cfg=S.overrides)
    attach_incumbents(rt, {r["job_id"]: r for r in res})
    res = res + run_jobs(rt, workers, base_cfg=S.overrides)
    d = S.dirs()
    import pickle
    with open(d["cache"] / "plan_results.pkl", "wb") as fh:
        pickle.dump(dict(results=res, config_hash=S.hash(), inputs=I.inputs_fingerprint(),
                         run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), fh)
    print(f"{len(res)} plan jobs in {time.time() - t0:.0f} s; failures: "
          f"{[r['job_id'] for r in res if r.get('status') not in ('exploratory_policy_scenario', 'solved') and not str(r.get('status','')).startswith('exploratory')]}")
    return dict(results=res)


def rerun(S, job_ids, workers=None):
    """Re-run selected jobs and merge them into the cached results (same config and inputs)."""
    import pickle
    old = {r["job_id"]: r for r in load_plan_results(S)}
    jobs = [j for j in catalogue(S) if j["job_id"] in set(job_ids)]
    attach_incumbents(jobs, old)
    new = run_jobs(jobs, workers, base_cfg=S.overrides)
    old.update({r["job_id"]: r for r in new})
    with open(S.dirs()["cache"] / "plan_results.pkl", "wb") as fh:
        pickle.dump(dict(results=list(old.values()), config_hash=S.hash(), inputs=I.inputs_fingerprint(),
                         run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), fh)
    return new


def load_plan_results(S):
    import pickle
    p = S.dirs()["cache"] / "plan_results.pkl"
    if not p.exists():
        raise FileNotFoundError("plans not built - run: python -m chapter5.build --plans")
    z = pickle.load(open(p, "rb"))
    if z["config_hash"] != S.hash() or z["inputs"] != I.inputs_fingerprint():
        raise RuntimeError("cached plans were built from a different configuration or input state - rebuild with --plans")
    return z["results"]
