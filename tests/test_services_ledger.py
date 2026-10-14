"""Activity/FTE ledger: the hand-worked example of docs/service_modules.md (activity → time → FTE ledger) and the accounting rules."""
import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from services import ledger as L  # noqa: E402

PKG = L.load(ROOT / "config" / "services" / "older_person_home_care.toml")
POP = pd.DataFrame({"province": ["ตัวอย่าง"], "60-69": [10_000], "70-79": [5_000], "80+": [2_000]})


def test_hand_worked_example():
    out = L.evaluate(PKG, POP, available_fte={"nurse": 5.0, "physician": 1.0, "physiotherapist": 5.0,
                                              "care_assistant": 40.0})
    act = out["activity"]
    assert act.recipients.iloc[0] == pytest.approx(720)                      # (200 + 300 + 400) x 0.8
    vol = act.groupby("activity").volume.sum()
    assert vol["nurse_home_visit"] == pytest.approx(8_640)
    assert vol["home_rehabilitation"] == pytest.approx(2_880)
    assert vol["care_assistant_visit"] == pytest.approx(37_440)
    assert act[act.activity == "physician_review"].set_index("setting").volume.to_dict() == pytest.approx(
        {"primary_care": 720, "remote": 720})
    H = out["hours"].groupby(["cadre", "component"]).hours.sum()
    assert H[("nurse", "task")] == pytest.approx(540 + 4_320)
    assert H[("nurse", "travel")] == pytest.approx(4_320)
    assert H[("nurse", "support")] == pytest.approx(1_440)
    fte = out["fte"].set_index("cadre")
    assert fte.loc["nurse", "hours"] == pytest.approx(10_620)
    assert fte.loc["nurse", "available_hours_per_fte"] == pytest.approx(1_536)
    assert fte.loc["nurse", "required_fte"] == pytest.approx(10_620 / 1_536)
    assert fte.loc["physiotherapist", "hours"] == pytest.approx(3_600)
    assert fte.loc["physician", "hours"] == pytest.approx(360)
    assert fte.loc["care_assistant", "hours"] == pytest.approx(46_800)
    hosp = out["hospital_required"].iloc[0]
    assert hosp.hospital_volume_change == pytest.approx(-1_440)
    assert hosp.hospital_hours_freed_physiotherapist == pytest.approx(480)
    d = out["deliverable"].set_index("activity")
    r = 5.0 / (10_620 / 1_536)
    assert d.loc["nurse_home_visit", "deliverable_share"] == pytest.approx(r)
    assert d.loc["assessment", "deliverable_share"] == pytest.approx(r)
    assert d.loc["home_rehabilitation", "deliverable_share"] == pytest.approx(1.0)
    assert (d.deliverable_volume <= d.volume + 1e-9).all()
    assert out["warnings"] and "placeholder" in out["warnings"][0]


def test_zero_coverage_gives_zero_activity_and_time():
    p = copy.deepcopy(PKG)
    p.coverage = 0.0
    out = L.evaluate(p, POP)
    assert out["activity"].volume.sum() == 0 and out["hours"].hours.sum() == 0


def test_setting_shares_must_sum_to_one():
    p = copy.deepcopy(PKG)
    p.activities[3].settings = {"primary_care": 0.5, "remote": 0.6}
    with pytest.raises(ValueError, match="sum to"):
        L.validate(p)


def test_numerator_allowance_cannot_also_be_deducted():
    p = copy.deepcopy(PKG)
    p.cadres["nurse"]["nonclinical_excludes"] = []           # travel and coordination now double counted
    with pytest.raises(ValueError, match="double counting"):
        L.validate(p)


def test_substitution_scales_with_delivered_activity():
    out = L.evaluate(PKG, POP, available_fte={"nurse": 99, "physician": 99, "physiotherapist": 1.0, "care_assistant": 99})
    req = out["hospital_required"].hospital_volume_change.iloc[0]
    dlv = out["hospital_deliverable"].hospital_volume_change.iloc[0]
    share = 1.0 / (3_600 / 1_536)
    assert dlv == pytest.approx(req * share)


def test_population_proportionality_and_units():
    two = pd.concat([POP, POP.assign(province="สองเท่า", **{"60-69": [20_000], "70-79": [10_000], "80+": [4_000]})])
    fte = L.evaluate(PKG, two)["fte"].pivot(index="province", columns="cadre", values="required_fte")
    assert np.allclose(fte.loc["สองเท่า"], 2 * fte.loc["ตัวอย่าง"])
