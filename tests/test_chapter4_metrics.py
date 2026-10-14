"""Checks of the shared Chapter 4 formulas on values whose answers are known by hand."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from chapter4 import metrics as M  # noqa: E402


def test_cagr_uses_elapsed_intervals():
    assert abs(M.cagr(100, 121, 2) - 0.10) < 1e-12
    assert np.isnan(M.cagr(0, 10, 3)) and np.isnan(M.cagr(-1, 10, 3))


def test_ratio_identity():
    gw, gp = M.cagr(100, 150, 12), M.cagr(50, 51, 12)
    assert abs(M.ratio_cagr_identity(gw, gp) - M.cagr(2, 150 / 51, 12)) < 1e-12


def test_contributions_keep_negative_and_over_100():
    c = M.contributions(pd.Series({"a": 10, "b": 10}), pd.Series({"a": 25, "b": 5}))
    assert abs(c.loc["a", "share_of_net_change_pct"] - 150) < 1e-9
    assert abs(c.loc["b", "share_of_net_change_pct"] + 50) < 1e-9


def test_gini_known_values():
    assert abs(M.weighted_gini([1, 1, 1], [1, 1, 1])) < 1e-12
    # two equal-weight units, one with everything: G = 0.5 for n = 2
    assert abs(M.weighted_gini([0, 2], [1, 1]) - 0.5) < 1e-12
    # integer weights equal replicated observations
    assert abs(M.weighted_gini([1, 3], [2, 1]) - M.weighted_gini([1, 1, 3], [1, 1, 1])) < 1e-12


def test_theil_decomposition_is_exact():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"W": rng.integers(1, 100, 30).astype(float), "D": rng.integers(100, 1000, 30).astype(float),
                       "g": np.repeat(range(5), 6)})
    d = M.theil_decomposition(df, "g")
    assert abs(d["identity_gap"]) < 1e-12
    assert abs(M.theil_t([1, 2], [1, 2])) < 1e-12


def test_op_decomposition_identity():
    r = M.op_decomposition(100, 130, 20, 22, 5)
    assert abs(r["identity_residual"]) < 1e-12
    assert abs(r["share_from_persons_pct"] + r["share_from_frequency_pct"] - 100) < 1e-9


def test_shapley_additive():
    s = M.shapley_two_factor(lambda a, b: a * b, 2.0, 3.0, 5.0, 7.0)
    assert abs(s["residual"]) < 1e-12


def test_pct_for_10pct():
    assert abs(M.pct_for_10pct(1.0) - 10.0) < 1e-12


def test_concentration_index_known_values():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    # equal weights, x ranked by itself: CI = 2 cov(x, R) / mean(x) = 0.25
    assert abs(M.concentration_index(x, x) - 0.25) < 1e-12
    assert abs(M.concentration_index(x, -x) + 0.25) < 1e-12           # reversed ranking flips the sign
    assert abs(M.concentration_index(np.ones(4), x)) < 1e-12           # equal density: no concentration
    assert abs(M.concentration_index(x, np.ones(4))) < 1e-12           # all tied ranks: no ordering
    # integer weights equal duplicating the units
    w = np.array([2, 1, 1, 3])
    assert abs(M.concentration_index(x, x, w) - M.concentration_index(np.repeat(x, w), np.repeat(x, w))) < 1e-12


def test_burden_table_contract():
    """BOD 2022 canonical table: 77 provinces x 174 causes, DALY = YLL + YLD, groups add to the total."""
    import pytest
    from chapter4 import config as C, panels as P
    if not (C.PROCESSED / "bod_province.csv").exists():
        pytest.skip("processed tables not built")
    from chapter4.ingest import load
    b = load("bod_province")
    assert b.prov_code.nunique() == 77 and b.groupby("prov_code").cause_code.nunique().eq(174).all()
    assert (b.asr_daly - b.asr_yll - b.asr_yld).abs().max() < 1e-6
    w = P.burden_wide().set_index("prov_code")
    groups = w[[f"bod_daly_{g.lower()}" for g in C.CFG["burden"]["groups"]]].sum(axis=1)
    assert np.allclose(groups, w.bod_daly)
    excl = b[b.cause_code.isin(C.CFG["burden"]["exclude_causes"])].groupby("prov_code").asr_daly.sum()
    assert np.allclose(w.bod_daly_allcause - w.bod_daly, excl.reindex(w.index).fillna(0))
