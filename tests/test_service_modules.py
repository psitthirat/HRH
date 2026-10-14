"""Data-ready service modules: contracts, calibration rules, accounting identities, browser JSON path."""
import copy
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from services import cancer, esrd, lab_modules as LM, older_care, synthetic  # noqa: E402
from services.contract import AGE_GROUPS  # noqa: E402

PROVS = [11, 12, 13]
POP = pd.DataFrame([dict(prov_code=p, year=y, **{g: 1e5 * (1 + 0.01 * (y - 2025)) * (1 + i / 8) for i, g in enumerate(AGE_GROUPS)})
                    for p in PROVS for y in range(2025, 2031)])
INPUTS = json.dumps({"service_population": {"columns": list(POP.columns), "rows": POP.values.tolist(), "source": "test"}})


def _synthetic(module):
    return json.loads(LM.synthetic_json(module, INPUTS))


@pytest.mark.parametrize("module", ["older_care", "esrd", "cancer"])
def test_synthetic_runs_are_labelled_and_complete(module):
    r = json.loads(LM.run_json(json.dumps({"module": module, "datasets": _synthetic(module)}), INPUTS))
    assert r["status"] == "completed" and r["evidence_label"] == "synthetic_demo"
    assert r["years"] == [2025, 2030]
    assert all(m["synthetic"] for m in r["provenance"]["datasets"].values())
    assert len(r["tables"]["national_by_year"]) == 6


@pytest.mark.parametrize("module,required", [("older_care", "older_care_state"), ("esrd", "esrd_incidence"),
                                             ("cancer", "cancer_incidence")])
def test_run_refused_without_required_dataset(module, required):
    ds = {k: v for k, v in _synthetic(module).items() if k != required}
    r = json.loads(LM.run_json(json.dumps({"module": module, "datasets": ds}), INPUTS))
    assert r["status"] == "invalid" and any(required in e for e in r["errors"])


def test_schema_errors_are_reported_not_filled():
    ds = _synthetic("esrd")
    d = pd.read_csv(pd.io.common.StringIO(ds["esrd_incidence"]["text"]))
    d = d[d.age_group != "80+"]                                 # an incomplete age grid
    ds["esrd_incidence"]["text"] = d.to_csv(index=False)
    v = json.loads(LM.validate_json(json.dumps({"module": "esrd", "datasets": ds}), INPUTS))
    assert not v["ok"] and any("80+" in e for e in v["errors"])
    bad = _synthetic("cancer")
    bad["cancer_incidence"]["text"] = bad["cancer_incidence"]["text"].replace("breast", "brest", 1)
    v = json.loads(LM.validate_json(json.dumps({"module": "cancer", "datasets": bad}), INPUTS))
    assert not v["ok"]


def test_policy_parameters_are_never_calibrated_and_overrides_win():
    ds = _synthetic("esrd")
    cfg = {"module": "esrd", "datasets": ds, "overrides": {"hd_sessions_per_week": 3.0}}
    v = json.loads(LM.validate_json(json.dumps(cfg), INPUTS))
    par = {p["id"]: p for p in v["parameters"]}
    assert par["hd_sessions_per_week"]["source"] == "user"
    assert par["incidence_per_million"]["source"] == "dataset:esrd_incidence"
    assert par["modality_mix_policy"]["source"] == "default" and par["modality_mix_policy"]["kind"] == "policy"


def test_esrd_patient_balance_and_stationary_start():
    tabs = {k: pd.read_csv(pd.io.common.StringIO(v["text"])) for k, v in _synthetic("esrd").items()}
    cal, _ = esrd.calibrate(tabs)
    p = {q.id: q.default for q in esrd.SPEC.params} | {k: v["value"] for k, v in cal.items()}
    stock = esrd.project(p, POP, list(range(2025, 2031)))
    assert esrd.check_balance(stock, p) < 1e-8
    # stationary start with constant population stays constant
    const = POP.assign(**{g: 1e5 for g in AGE_GROUPS})
    p2 = dict(p, starting_stock={})
    s2 = esrd.project(p2, const, list(range(2025, 2031))).groupby("year").patients.sum()
    assert np.allclose(s2, s2.iloc[0])


def test_cancer_early_detection_shift_keeps_cases_and_moves_stage():
    tabs = {k: pd.read_csv(pd.io.common.StringIO(v["text"])) for k, v in _synthetic("cancer").items()}
    cal, _ = cancer.calibrate(tabs)
    p = {q.id: q.default for q in cancer.SPEC.params} | {k: v["value"] for k, v in cal.items()}
    a = cancer.project(p, POP, [2025])
    b = cancer.project(dict(p, early_detection_shift={**p["early_detection_shift"], "cervix": 0.5}), POP, [2025])
    za, zb = a[a.site == "cervix"], b[b.site == "cervix"]
    assert np.allclose(za.cases, zb.cases)
    assert (zb.stage_IV < za.stage_IV).all() and (zb.stage_I > za.stage_I).all()
    assert np.allclose(zb[[f"stage_{s}" for s in cancer.STAGES]].sum(axis=1), zb.cases)


def test_older_care_defaults_match_the_documented_package():
    t = tomllib.loads((ROOT / "config/services/older_person_home_care.toml").read_text(encoding="utf-8"))
    d = older_care.DEFAULT_PACKAGE
    assert t["prevalence"] == d["prevalence"] and t["package"]["coverage"] == d["package"]["coverage"]
    for a, v in d["activities"].items():
        for k in ["per_recipient", "settings", "task_minutes"]:
            assert t["activities"][a][k] == v[k]
        assert t["activities"][a].get("travel_minutes", {}) == v.get("travel_minutes", {})
    assert t["support_hours"] == d["support_hours"] and t["cadres"] == d["cadres"]


def test_dataset_hash_changes_rerun_identity():
    ds = _synthetic("older_care")
    r1 = json.loads(LM.run_json(json.dumps({"module": "older_care", "datasets": ds}), INPUTS))
    ds2 = copy.deepcopy(ds)
    ds2["older_care_state"]["text"] = ds2["older_care_state"]["text"].replace("\n", "\n", 1) + ""
    d = pd.read_csv(pd.io.common.StringIO(ds2["older_care_state"]["text"]))
    d.loc[0, "in_state"] = d.loc[0, "in_state"] + 1
    ds2["older_care_state"]["text"] = d.to_csv(index=False)
    r2 = json.loads(LM.run_json(json.dumps({"module": "older_care", "datasets": ds2}), INPUTS))
    h1 = r1["provenance"]["datasets"]["older_care_state"]["sha256"]
    h2 = r2["provenance"]["datasets"]["older_care_state"]["sha256"]
    assert h1 != h2 and r1["tables"]["national_by_year"] != r2["tables"]["national_by_year"]


# ----------------------------------------------------------------------------- provider workload, screening,
# informal care, staged comparisons (next-phase plan §3.1, §4.1, §4.3, §8.4)

def _run(module, ds, overrides=None, inputs=INPUTS):
    return json.loads(LM.run_json(json.dumps({"module": module, "datasets": ds, "overrides": overrides or {}}), inputs))


@pytest.mark.parametrize("module,flows", [("esrd", "esrd_referral"), ("cancer", "cancer_referral")])
def test_referral_moves_workload_but_preserves_national_totals(module, flows):
    ds = _synthetic(module)
    assert flows in ds
    r = _run(module, ds)
    assert r["checks"]["provider_basis"] == "referral_flows"
    assert r["checks"]["referral_totals_preserved_max_gap"] < 1e-6
    res = pd.DataFrame(r["tables"]["province_last_year"]).set_index("prov_code")
    prov = pd.DataFrame(r["tables"]["province_last_year_provider"]).set_index("prov_code")
    col = "hd_sessions" if module == "esrd" else "surgeon_hours"
    assert not np.allclose(res[col].sort_index(), prov[col].reindex(res.index).fillna(0).sort_index())
    assert np.isclose(res[col].sum(), prov[col].sum())
    r0 = _run(module, {k: v for k, v in ds.items() if k != flows})          # default provider = residence
    assert r0["checks"]["provider_basis"] == "residence_default"
    res0 = pd.DataFrame(r0["tables"]["province_last_year"]).set_index("prov_code").sort_index()
    prov0 = pd.DataFrame(r0["tables"]["province_last_year_provider"]).set_index("prov_code").sort_index()
    assert np.allclose(res0[col], prov0[col])


def test_referral_shares_above_one_are_rejected():
    ds = _synthetic("esrd")
    ds["esrd_referral"]["text"] = "from_prov,to_prov,share\n12,11,0.7\n12,13,0.6\n"
    v = json.loads(LM.validate_json(json.dumps({"module": "esrd", "datasets": ds}), INPUTS))
    assert not v["ok"] and not v["datasets"]["esrd_referral"]["ok"]
    assert any("เกิน 1" in e for e in v["datasets"]["esrd_referral"]["errors"])


def test_screening_is_a_separate_pathway_that_never_changes_stage():
    ds = _synthetic("cancer")
    off = {"screening_policy": {s: {"target_age_groups": ["45-59"], "coverage": 0.0, "interval_years": 2}
                                for s in cancer.SCREEN_SITES}}
    on = {"screening_policy": {s: {"target_age_groups": ["45-59"], "coverage": 0.5, "interval_years": 2}
                               for s in cancer.SCREEN_SITES}}
    a, b = _run("cancer", ds, off), _run("cancer", ds, on)
    assert a["tables"]["national_by_site_year"] == b["tables"]["national_by_site_year"]   # cases and stages unchanged
    assert a["tables"]["national_by_year"] == b["tables"]["national_by_year"]
    assert all(v == 0 for r in a["tables"]["screening_national_by_year"] for k, v in r.items() if k.endswith("_fte"))
    s = pd.DataFrame(b["tables"]["screening_national_by_site_year"])
    assert (s.screened > 0).all() and (s.diagnostic_procedures <= s.positives + 1e-9).all()
    assert any("early_detection_shift" in w for w in b["warnings"])
    assert any("female_share" in w for w in b["warnings"])                 # test population has no F_ columns
    # with women by age group in the population, breast/cervix targets use them instead of the share assumption
    popf = POP.assign(**{f"F_{g}": POP[g] * 0.25 for g in AGE_GROUPS})
    inp = json.dumps({"service_population": {"columns": list(popf.columns), "rows": popf.values.tolist(), "source": "test"}})
    c = _run("cancer", ds, on, inp)
    sc = pd.DataFrame(c["tables"]["screening_national_by_site_year"]).set_index(["year", "site"])
    sb = s.set_index(["year", "site"])
    assert np.allclose(sc.loc[(2025, "cervix"), "target_population"], sb.loc[(2025, "cervix"), "target_population"] * 0.25 / 0.51)
    assert np.allclose(sc.loc[(2025, "colorectal"), "target_population"], sb.loc[(2025, "colorectal"), "target_population"])
    assert not any("female_share" in w for w in c["warnings"])


def test_informal_care_is_reported_separately_from_workforce_fte():
    ds = _synthetic("older_care")
    a = _run("older_care", ds)
    b = _run("older_care", ds, {"caregiver_full_time_hours": 1040.0})
    assert a["tables"]["national_by_year"] == b["tables"]["national_by_year"]           # FTE untouched
    ia, ib = pd.DataFrame(a["tables"]["informal_care_national"]), pd.DataFrame(b["tables"]["informal_care_national"])
    assert np.allclose(ib.caregiver_full_time_equivalents, 2 * ia.caregiver_full_time_equivalents)
    assert np.allclose(ia.informal_care_hours, ib.informal_care_hours)
    calibrated = {p["id"]: p for p in a["parameters"]}["informal_care_hours_per_week"]
    assert calibrated["source"] == "dataset:older_caregiver_time"


def test_staged_comparison_separates_data_refit_and_policy():
    base = _synthetic("esrd")
    new = copy.deepcopy(base)
    d = pd.read_csv(pd.io.common.StringIO(new["esrd_incidence"]["text"]))
    d["new_patients"] = (d.new_patients * 1.3).round()
    new["esrd_incidence"] = {"text": d.to_csv(index=False), "name": "v2.csv", "synthetic": True}
    cfg = {"op": "staged", "module": "esrd", "base": {"datasets": base}, "new": {"datasets": new},
           "overrides": {"transplant_multiplier": 1.5, "hd_session_hours": 4.5}}
    r = json.loads(LM.dispatch_json(json.dumps(cfg), INPUTS))
    assert r["status"] == "completed" and [s["id"] for s in r["stages"]] == \
        ["base", "new_data_fixed_calibration", "recalibrated", "policy"]
    s1, s2, s3 = r["steps"]
    assert s1["changes"]["data"] == ["esrd_incidence"] and not s1["changes"]["calibration"]
    assert "incidence_per_million" in s2["changes"]["calibration"] and s2["changes"]["assumption"] == ["hd_session_hours"]
    assert s3["changes"]["policy"] == ["transplant_multiplier"] and not s3["changes"]["data"]
    for h in r["headline"]:
        assert np.isclose(h["effect_new_data"] + h["effect_refit_or_method"] + h["effect_policy"], h["total_change"])
        assert abs(h["effect_new_data"]) <= 1e-9 * max(1.0, abs(h["base"]))   # incidence enters only through calibration


def test_comparability_contract_refuses_mismatched_runs():
    from services import compare as CMP
    ds = _synthetic("esrd")
    a = _run("esrd", ds)
    b = json.loads(LM.run_json(json.dumps({"module": "esrd", "datasets": ds, "years": [2025, 2028]}), INPUTS))
    c = _run("cancer", _synthetic("cancer"))
    assert CMP.comparability(a, a)["verdict"] == "comparable"
    assert CMP.comparability(a, b)["verdict"] == "not_comparable"
    assert CMP.comparability(a, c)["verdict"] == "not_comparable"
    d = copy.deepcopy(a)
    d["evidence_label"] = "user_data_unvalidated"
    assert CMP.comparability(a, d)["verdict"] == "comparable_with_caveats"
