"""Chapter 5 stress and boundary tests (task section 13.3).

Small synthetic problems test the allocator and simulator; a few integration tests use the
real Chapter 4 inputs (skipped if the processed tables are absent).

    PYTHONPATH=src .venv/bin/python -m pytest tests/test_chapter5.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chapter5 import allocation as AL  # noqa: E402
from chapter5 import evaluation as EV  # noqa: E402
from chapter5 import simulation as SIM  # noqa: E402


def small(P=5, T=3, A=20, d=0.05, r=0.0, H0=None, targets=None, **kw):
    H0 = np.array([50., 80., 30., 120., 60.][:P]) if H0 is None else np.asarray(H0, float)
    tg = np.tile(np.array([100., 90., 80., 130., 70.][:P]), (T, 1)) if targets is None else targets
    return AL.Problem(provs=np.arange(P), years=list(range(T)), H0=H0, T=tg, d=np.full(P, d), r=np.full(P, r),
                      A=np.full(T, A), region=np.array([1, 1, 2, 2, 2][:P]), **kw)


def test_zero_recruits_zero_departures_keeps_stock():
    pb = small(A=0, d=0.0, floor=0)
    sol = AL.solve(pb)
    assert sol.status == "solved"
    assert np.allclose(sol.H[-1], pb.H0)


def test_transfers_only_conserve_total_stock():
    pb = small(A=0, d=0.0, floor=0, transfers=True, tau=0.1, nat_budget=0.1, cap_mode="net_growth", cap=0.5)
    sol = AL.solve(pb)
    assert sol.status == "solved" and sol.zout.sum() > 0
    assert np.isclose(sol.H[-1].sum(), pb.H0.sum())
    assert (sol.zin.sum(1) == sol.zout.sum(1)).all()


def test_recruitment_without_departures_adds_exactly_the_entries():
    pb = small(A=20, d=0.0, r=0.01, floor=1, cap=0.5)
    sol = AL.solve(pb)
    Hp = pb.H0.copy(); expect = pb.H0.sum()
    for t in range(pb.nT):
        expect += pb.A[t] + (pb.r[t] * Hp).sum()
        Hp = sol.H[t]
    assert np.isclose(sol.H[-1].sum(), expect)


def test_proportional_growth_leaves_relative_inequality_unchanged():
    H = np.array([10., 20., 30., 40.]); D = np.array([15., 15., 30., 40.])
    assert np.isclose(EV.gini(H / D, D), EV.gini(1.37 * H / D, D))


def test_pool_below_universal_floor_is_reported_infeasible():
    pb = small(A=3, floor=1)
    sol = AL.solve(pb)
    assert sol.status == "infeasible_under_selected_constraints"
    assert sol.diagnostics["floor_infeasible_years"]


def test_insufficient_receiving_capacity_keeps_the_excess_visible():
    pb = small(A=60, cap=0.05)          # capacity ~ 0.05 * 340 = 17 < 60
    sol = AL.solve(pb)
    assert sol.status == "infeasible_under_selected_constraints"
    assert sum(sol.diagnostics["min_unplaced_by_year"]) > 0     # not silently lost


def test_small_high_exit_province_gross_vs_net_cap():
    # one province with a 20% exit probability: a 10% gross-arrival cap cannot replace its exits
    kw = dict(P=2, H0=[40., 400.], targets=np.tile([100., 400.], (5, 1)), T=5, A=30)
    g = small(**kw, cap_mode="gross_arrivals", cap=0.10)
    g.d[:, 0] = 0.20
    n = small(**kw, cap_mode="net_growth", cap=0.10)
    n.d[:, 0] = 0.20
    sg, sn = AL.solve(g), AL.solve(n)
    assert sg.H[-1, 0] < 40            # declines under the gross cap
    assert sn.H[-1, 0] > sg.H[-1, 0]   # the net cap allows gross replacement


def test_invalid_zero_target_is_rejected():
    tg = np.tile(np.array([100., 0., 80., 130., 70.]), (3, 1))
    with pytest.raises(AssertionError):
        small(targets=tg)


def test_targets_met_everywhere_secondary_objective_defined():
    pb = small(targets=np.tile(np.array([10., 10., 10., 10., 10.]), (3, 1)))
    sol = AL.solve(pb)
    assert sol.status == "solved"
    assert AL.objective_exact(pb, sol.H) == 0
    assert any(s["stage"] == "distribution" for s in sol.stages)


def test_transfer_bounds_and_regional_routes():
    pb = small(A=10, transfers=True, tau=0.1, nat_budget=0.1, cap_mode="net_growth", cap=0.5,
               network="within_health_region")
    sol = AL.solve(pb)
    chk = AL.check(pb, sol)
    assert chk["all_ok"] and chk["regional_balance"]
    Hp = np.vstack([pb.H0[None], sol.H[:-1]])
    assert (sol.zout <= np.floor(pb.tau * (1 - pb.d) * Hp + 1e-9)).all()
    dist = np.ones((5, 5)) - np.eye(5)
    for t in range(pb.nT):
        for i, j, n in AL.route(sol.zout[t], sol.zin[t], dist, pb.region, pb.network):
            assert pb.region[i] == pb.region[j] and i != j


def test_integer_apportionment_preserves_total():
    sh = np.array([0.333, 0.333, 0.334, 1e-6])
    for tot in [0, 1, 7, 2000]:
        a = AL.apportion(tot, sh)
        assert a.sum() == tot and (a >= 0).all()


def test_solver_decisions_respect_every_hard_bound():
    pb = small(A=25, transfers=True, tau=0.05, nat_budget=0.05)
    sol = AL.solve(pb)
    assert AL.check(pb, sol)["all_ok"]
    assert all(np.issubdtype(a.dtype, np.integer) for a in (sol.x, sol.zin, sol.zout))


def test_switch_count_is_half_l1():
    xm = np.array([[3, 2, 0]]); xn = np.array([[1, 2, 2]])
    sw, pct = EV.switches(xm, xn, pool=np.array([5]))
    assert sw[0] == 2 and np.isclose(pct[0], 40)


def test_adaptive_decisions_use_no_future_information():
    P, T = 5, 4
    pb = small(T=T)
    args = lambda U: (0, dict(H0=pb.H0, provs=pb.provs), pb.T, "common_total", pb.d[0], pb.r[0], U,
                      np.full((T, P), 0.5), np.ones((T, P)), pb.d[0] * 100, np.full(P, 100.), pb.r[0] * 100 + 1e-6,
                      np.full(P, 100.), pb.A, dict(floor=1, cap=0.10))
    U1 = np.full((T, P), 0.5)
    U2 = U1.copy(); U2[2:] = 0.99                        # change only the future (years >= 2)
    a, b = SIM.simulate_adaptive_path(args(U1)), SIM.simulate_adaptive_path(args(U2))
    assert (a["X"][:3] == b["X"][:3]).all()              # decisions up to year 2 unchanged


def test_greedy_benchmark_is_close_to_milp():
    pb = small(A=20)
    sol = AL.solve(pb)
    g = AL.greedy(pb)
    # the MILP optimises the tangent approximation of s^2 (error <= step^2/4 per weighted term),
    # so on the exact objective it may trail the heuristic by at most that bound plus the gap
    bound = pb.nT * pb.tangent_step ** 2 / 4 + pb.mip_rel_gap * g["objective_exact"]
    assert AL.objective_exact(pb, sol.H) <= g["objective_exact"] + bound


# ----------------------------------------------------------------------------- integration (real inputs)

def _have_inputs():
    return (Path(__file__).resolve().parents[1] / "data/processed/province_panel_76.csv").exists()


@pytest.mark.skipif(not _have_inputs(), reason="Chapter 4 processed tables absent")
def test_fixed_reference_m5_ignores_physician_stock():
    from chapter5 import pipeline as PL, responsibilities as R
    ctx = PL.context("{}", "{}")
    cov, res = ctx.fb._rows(2030)
    a = R.m5_rate(ctx.pkg, "adjrw", cov, res, np.log(np.full(76, 10.0)), 2023, reference=True)
    b = R.m5_rate(ctx.pkg, "adjrw", cov, res, np.log(np.full(76, 90.0)), 2023, reference=True)
    assert np.allclose(a, b)


@pytest.mark.skipif(not _have_inputs(), reason="Chapter 4 processed tables absent")
def test_zero_feedback_reduces_to_nstd():
    from chapter5 import pipeline as PL
    ctx = PL.context("{}", "{}")
    for y in [2026, 2033, 2040]:
        D0, eta = ctx.fb.nfb_D(y, ctx.H0 * 1.7, 0.0)
        Dn = ctx.idx[ctx.idx.year == y].sort_values("prov_code").D_N.to_numpy()
        assert np.allclose(D0, Dn) and np.allclose(eta, 0)


@pytest.mark.skipif(not _have_inputs(), reason="Chapter 4 processed tables absent")
def test_demography_base_year_and_national_control():
    from chapter5 import config as C, demography as D
    S = C.load()
    arr, provs, years = D.register_array()
    proj, _, _ = D.project(arr, provs, years, 2025, 2030, (2013, 2024), (2022, 2025), m=1.5, national_control=True)
    nat, _, _ = D.project(arr.sum(0, keepdims=True), np.array([0]), years, 2025, 2030, (2013, 2024), (2022, 2025),
                          national_control=False)
    assert np.allclose(proj[2025].sum((1, 2)), arr[..., list(years).index(2025)].sum((1, 2)))
    assert np.isclose(proj[2030].sum(), nat[2030].sum(), rtol=1e-9)


@pytest.mark.skipif(not _have_inputs(), reason="Chapter 4 processed tables absent")
def test_departure_probabilities_are_proper():
    from chapter5 import pipeline as PL
    ctx = PL.context("{}", "{}")
    assert ((ctx.dep["d"] > 0) & (ctx.dep["d"] < 1)).all()
    assert np.allclose(sum(ctx.dep["shares"].values()), 1)


def test_surplus_only_blocks_net_outflow_below_target():
    # every province below target: no province may lose existing staff through transfers
    pb = small(A=10, transfers=True, tau=0.2, nat_budget=0.2, cap_mode="net_growth", cap=0.5,
               protect_mode="surplus_only")
    sol = AL.solve(pb)
    assert sol.status == "solved" and AL.check(pb, sol)["all_ok"]
    assert (sol.zout <= sol.zin).all()


def test_burden_index_definitions():
    """B family: D_B (expected DALYs at 2022 age-specific rates) and D_Basr (population x ASR) are
    scaled to the 2025 population; expected DALYs reproduce the 2022 BOD counts (the civil register
    is within ~1% of the BOD mid-year population) and equal the Chapter 4 panel in the 2025 base year;
    D_Basr / D_P is the relative ASR."""
    from chapter4 import config as C4
    if not (C4.PROCESSED / "bod_province_age.csv").exists():
        pytest.skip("processed tables not built")
    from chapter4 import panels as P4
    from chapter5 import pipeline as PL
    ix = PL.context().idx
    g = ix.groupby("year")[["D_P", "D_B", "D_Basr"]].sum()
    assert abs(g.loc[2025, "D_B"] / g.loc[2025, "D_P"] - 1) < 1e-12
    assert abs(g.loc[2025, "D_Basr"] / g.loc[2025, "D_P"] - 1) < 1e-12
    z = ix[ix.year == 2025].set_index("prov_code")
    assert np.allclose(z.D_Basr / z.D_P, z.asr_daly / np.average(z.asr_daly, weights=z.population))
    # 2022 register x 2022 rates reproduces the BOD counts; the 2025 base year reproduces the register
    e = P4.burden_expected_panel().set_index(["year", "prov_code"]).bod_daly_expected
    cnt = P4.burden_wide().set_index("prov_code").bod_daly_count_2022.reindex(z.index)
    assert ((e.loc[2022].reindex(z.index) / cnt) - 1).abs().max() < 0.03
    assert np.allclose(z.B_B, e.loc[2025].reindex(z.index))
    # ageing: expected DALYs per person rise between 2025 and 2040 at fixed age-specific rates
    per = ix.groupby("year").B_B.sum() / ix.groupby("year").population.sum()
    assert per.loc[2040] > per.loc[2025]


def test_health_gain_zero_at_counterfactual_and_sign():
    """A plan that keeps the counterfactual stock averts nothing; more physicians everywhere avert
    a positive amount for a negative elasticity; upper amenable ages are honoured."""
    from chapter4 import config as C4
    if not (C4.PROCESSED / "bod_province_age.csv").exists():
        pytest.skip("processed tables not built")
    from chapter5 import pipeline as PL, health_gain as HG
    ctx = PL.context()
    years = ctx.S.years
    Hcf = np.vstack([ctx.res.set_index(["year", "prov_code"]).loc[y].reindex(ctx.provs).H_cf.to_numpy(float) for y in years])
    # H such that the annual average equals H_cf exactly: solve the recursion of 0.5 * (H_{t-1} + H_t)
    H = np.zeros_like(Hcf)
    prev = ctx.H0.astype(float)
    for t in range(len(years)):
        H[t] = 2 * Hcf[t] - prev
        prev = H[t]
    S, _, _ = HG.evaluate(ctx, {"P-R": {"H": H}, "UP": {"H": H * 1.1}}, ["P-R", "UP"])
    assert np.allclose(S[S.plan_id == "P-R"].averted_total, 0, atol=1e-6)
    assert (S[S.plan_id == "UP"].averted_total > 0).all()
    r = HG.amenable_rates("yll")
    assert (r[r.age_group == 8].amenable == 0).all()          # every amenable limit is below 80
