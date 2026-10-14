"""Dataset-replacement prototype: incompatible files are rejected, a compatible one is traced."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SRC = ROOT / "data" / "epi" / "BOD_2022_Province_Disease_Age.csv"
MAN = json.loads((ROOT / "config" / "workspace" / "examples" / "bod_province_age_manifest.json").read_text())
pytestmark = pytest.mark.skipif(not SRC.exists() or not (ROOT / "data/processed/bod_province_age.csv").exists(),
                                reason="BOD data or processed tables absent")


@pytest.fixture(scope="module")
def base():
    return pd.read_csv(SRC)


def _write(tmp_path, d, name):
    p = tmp_path / name
    d.to_csv(p, index=False)
    return p


def test_missing_province_is_rejected_not_zero_filled(tmp_path, base):
    from workspace import replace as W
    p = _write(tmp_path, base[base.area_name != "P96"], "missing.csv")
    v = W.validate(MAN, p)
    assert not v["ok"] and any("never zero-filled" in e for e in v["errors"])


def test_negative_and_identity_errors_are_rejected(tmp_path, base):
    from workspace import replace as W
    d = base.copy()
    d.loc[0, "YLL"] = -1.0
    v = W.validate(MAN, _write(tmp_path, d, "neg.csv"))
    assert not v["ok"] and any("negative" in e for e in v["errors"])


def test_checksum_mismatch_is_rejected(tmp_path, base):
    from workspace import replace as W
    v = W.validate(dict(MAN, sha256="0" * 64), _write(tmp_path, base.head(10), "small.csv"))
    assert not v["ok"] and any("checksum" in e for e in v["errors"])


def test_compatible_replacement_is_accepted_and_traced(tmp_path, base):
    from workspace import replace as W
    d = base.copy()
    m = d.area_name.isin(["P36", "P46"])                  # two provinces: rates and counts 10% lower
    for c in ["DALY", "YLL", "YLD_NEW", "DALY_rate", "YLL_rate", "YLD_rate"]:
        d.loc[m, c] = d.loc[m, c] * 0.9
    p = _write(tmp_path, d, "ok.csv")
    v = W.validate(dict(MAN, sha256=W.sha256(p)), p)
    assert v["ok"], v["errors"]
    assert "2 provinces" in v["warnings"][0]
    b = W.burden_inputs_from(v["table"])
    canon = W.burden_inputs_from(pd.read_csv(ROOT / "data/processed/bod_province_age.csv"))
    assert (b["rate_daly"].loc[36] / canon["rate_daly"].loc[36]).round(6).eq(0.9).all()
    assert (b["rate_daly"].loc[10] == canon["rate_daly"].loc[10]).all()
    # re-standardization reproduces the published ASR of an unchanged province
    from chapter4 import panels as P
    assert abs(canon["asr_daly"].loc[10] / P.burden_wide().set_index("prov_code").bod_daly.loc[10] - 1) < 1e-3


def test_sandbox_writes_a_traceable_manifest_without_touching_canonical_outputs(tmp_path, base, monkeypatch):
    from workspace import replace as W
    from chapter5 import config as C5, pipeline as PL
    try:
        PL.load_plan_results(C5.load())
    except (FileNotFoundError, RuntimeError):
        pytest.skip("plan cache not current")
    d = base.copy()
    m = d.area_name == "P36"
    for c in ["DALY", "YLL", "YLD_NEW", "DALY_rate", "YLL_rate", "YLD_rate"]:
        d.loc[m, c] = d.loc[m, c] * 0.9
    p = _write(tmp_path, d, "ok.csv")
    monkeypatch.setattr(W, "SANDBOX", tmp_path / "workspaces")
    canon = (ROOT / "outputs/chapter5/tables/T5_INDICES.parquet").stat().st_mtime
    run = W.sandbox(dict(MAN, sha256=W.sha256(p)), p, "t", solve=False)
    assert run["validation"]["ok"] and run["dataset"]["sha256"] == W.sha256(p)
    assert {"config_hash", "chapter4_code_hash", "chapter5_code_hash", "canonical_inputs_fingerprint"} <= set(run)
    assert any(a["action"] == "unaffected" for a in run["affected_components"])
    cmp_ = pd.read_csv(tmp_path / "workspaces" / "t" / "family_B_target_comparison.csv", encoding="utf-8-sig")
    assert cmp_.set_index(["year", "prov_code"]).loc[(2040, 36), "share_change_pct"] < 0
    assert (ROOT / "outputs/chapter5/tables/T5_INDICES.parquet").stat().st_mtime == canon
