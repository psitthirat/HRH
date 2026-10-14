"""Comparability contract of Workforce Lab allocation runs (next-phase plan §8.4)."""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from chapter5 import lab_compare as LC  # noqa: E402

V = {k: "v1" for k in LC.VERSION_KEYS}
RUN = {"run_id": "a", "versions": V,
       "ledger": [{"year_ce": y, "prov_code": p} for y in (2026, 2027) for p in (11, 12)],
       "resolved_config": {"parameters": {"allocation.cap_fraction": 0.1, "targets.reference_per_1000": 1.0,
                                          "services.op_minutes": 10.0, "solver.mip_gap": 2e-4, "supply.licensing": 0.95,
                                          "geography.overrides": {}}}}


def _with(**params):
    r = copy.deepcopy(RUN)
    r["run_id"] = "b"
    r["resolved_config"]["parameters"].update(params)
    return r


def test_policy_and_assumption_changes_are_directly_comparable():
    c = LC.comparability(RUN, _with(**{"allocation.cap_fraction": 0.2, "supply.licensing": 0.9, "solver.mip_gap": 1e-3}))
    assert c["verdict"] == "directly_comparable"
    assert {g: [x["id"] for x in v] for g, v in c["changes"].items()} == \
        {"policy": ["allocation.cap_fraction"], "assumption": ["supply.licensing"], "method": ["solver.mip_gap"]}
    assert c["exclusions"] and c["own_context_results_kept"]


def test_denominator_target_or_weight_changes_need_a_common_reference():
    for k, v in [("targets.reference_per_1000", 1.2), ("services.op_minutes", 12.0), ("demography.scenario", "high")]:
        assert LC.comparability(RUN, _with(**{k: v}))["verdict"] == "common_reference_required", k


def test_versions_domain_and_geography_block_comparison():
    b = copy.deepcopy(RUN)
    b["versions"] = V | {"inputs_version": "v2"}
    assert LC.comparability(RUN, b)["verdict"] == "not_comparable"
    b = copy.deepcopy(RUN)
    b["ledger"] = b["ledger"][:2]
    assert LC.comparability(RUN, b)["verdict"] == "not_comparable"
    assert LC.comparability(RUN, _with(**{"geography.overrides": {"11": 12}}))["verdict"] == "not_comparable"
