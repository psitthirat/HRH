"""One validation inventory built from the existing Chapter 4/5 artifacts (plan §5, backlog item 2).

Every row states what kind of evidence a check is, which information it used, against which
simple comparator, over what horizon and metric, and what it cannot establish.  Nothing is
re-estimated here; values are read from the published tables so the inventory cannot drift from
them.  Verdict vocabulary:

    beats_comparator / does_not_beat_comparator   a predictive check with a stated baseline
    diagnostic_only                               reconciliation or support check, no baseline
    implementation_check                          software/optimiser property for tested cases
    scenario_only                                 no holdout exists; assumptions, not validation
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from chapter4 import config as C4

OUT4 = C4.OUTPUTS
COLS = ["check_id", "chapter", "component", "evidence_type", "forecast_origin", "information_set", "model",
        "comparator", "horizon", "metric", "value_model", "value_comparator", "verdict", "sample", "limitation",
        "source_artifact"]


def _read(rel: str) -> pd.DataFrame:
    return pd.read_csv(C4.ROOT / rel, encoding="utf-8-sig")


def inventory(S, hindcast: dict | None = None, chapter4_only: bool = False) -> pd.DataFrame:
    """All checks; chapter4_only=True returns the Chapter 4 rows (used by notebook 4.6, which runs
    before Chapter 5 and must not read Chapter 5 outputs)."""
    rows = []
    add = lambda **k: rows.append({c: k.get(c, "") for c in COLS})
    vdir = "outputs/chapter5/validation"
    # ---- Chapter 4: spatial (province-grouped) cross-validation of the service models
    rel = "outputs/chapter4_2/tables/T423_MODEL_VALIDATION.csv"
    sc = _read(rel)
    sc = sc[(sc.estimator == "ols") & (sc.age_groups == 3)].set_index(["outcome", "model"])
    for o in ["op_moph", "ip_moph", "adjrw"]:
        m5, m0 = sc.loc[(o, "M5"), "r2_pred_train_mean"], sc.loc[(o, "M0"), "r2_pred_train_mean"]
        add(check_id=f"C4-CV-{o}", chapter="4.2.3", component=f"service model M5 ({o})",
            evidence_type="spatial: repeated 5-fold province-grouped CV", forecast_origin="none (cross-section)",
            information_set="held-out provinces' observed covariates in the same years", model="M5 (OLS)",
            comparator="M0 (year effects only)", horizon="none", metric="R² vs training-fold mean",
            value_model=m5, value_comparator=m0, verdict="beats_comparator" if m5 > m0 else "does_not_beat_comparator",
            sample=f"{int(sc.loc[(o, 'M5'), 'n_rows'])} province-years, {int(sc.loc[(o, 'M5'), 'provinces'])} provinces, 2022–2025",
            limitation="prediction across provinces, not through time; supply terms make fit partly endogenous",
            source_artifact=rel)
    # ---- Chapter 4: temporal holdouts (forward information) against persistence
    rel = "outputs/chapter4_2/tables/T423_TEMPORAL_VALIDATION.csv"
    tv = _read(rel)
    for o in ["op_moph", "ip_moph", "adjrw"]:
        for ty in sorted(tv.test_year.unique()):
            z = tv[(tv.outcome == o) & (tv.test_year == ty) & (tv.information == "forward")]
            # the rule Chapter 4 reports (last-year effect), not the better of the two after the fact
            m5 = z[(z.model == "M5") & (z.year_rule == "last_year_effect")].iloc[0]
            pe = z[z.model == "persistence"].iloc[0]
            add(check_id=f"C4-TEMP-{o}-{ty}", chapter="4.2.3", component=f"service model M5 ({o})",
                evidence_type="temporal holdout (one year ahead)", forecast_origin=str(ty - 1),
                information_set="covariates carried forward from the last training year",
                model=f"M5, {m5.year_rule} year rule", comparator="persistence (last observed rate)", horizon="1 year",
                metric="R² vs training mean", value_model=m5.r2_pred_train_mean, value_comparator=pe.r2_pred_train_mean,
                verdict="beats_comparator" if m5.r2_pred_train_mean > pe.r2_pred_train_mean else "does_not_beat_comparator",
                sample=f"{int(m5.n)} provinces; training {ty - (3 if ty == 2025 else 2)}–{ty - 1}",
                limitation="short series (2022 onwards); explanatory fit is not forecasting skill", source_artifact=rel)
    # ---- Chapter 4.5: modeled burden as a predictor of recorded services
    rel = "outputs/chapter4_5/tables/T45_PAIRED_GAINS_BURDEN.csv"
    if (C4.ROOT / rel).exists():
        pg = _read(rel)
        for o in ["op_moph", "ip_moph", "adjrw"]:
            z = pg[(pg.outcome == o) & (pg.baseline == "M1") & (pg.model == "M2B")].iloc[0]
            add(check_id=f"C45-CV-{o}", chapter="4.5", component=f"BOD burden as service predictor ({o})",
                evidence_type="spatial: paired province-grouped CV", forecast_origin="none (cross-section)",
                information_set="BOD 2022 held fixed across 2022–2025", model="M2B (age + log ASR DALY)",
                comparator="M1 (age only)", horizon="none", metric="% SSE reduction (95% cluster bootstrap)",
                value_model=z.sse_reduction_pct, value_comparator=0.0,
                verdict="beats_comparator" if z.lo95 > 0 else "does_not_beat_comparator",
                sample=f"95% interval {z.lo95:.1f} to {z.hi95:.1f}",
                limitation="tests prediction of recorded hospital activity, not suitability as an equity criterion",
                source_artifact=rel)
    if chapter4_only:
        return pd.DataFrame(rows, columns=COLS)
    # ---- Chapter 5: population hindcast
    rel = f"{vdir}/T5_POP_BACKTEST.csv"
    pb = _read(rel).set_index("method")
    hp = pb.loc["hamilton_perry_national_control"]
    for comp in ["no_change_2019", "linear_trend_totals_2013_2019"]:
        add(check_id=f"C5-POP-{comp}", chapter="5.2", component="Hamilton–Perry population projection (national control)",
            evidence_type="hindcast (latest revised register)", forecast_origin="2019", information_set="registers 2013–2019",
            model="Hamilton–Perry, national control", comparator=comp.replace("_", " "), horizon="6 years (2025)",
            metric="province-total MAPE (%)", value_model=hp.mape_total_pct, value_comparator=pb.loc[comp, "mape_total_pct"],
            verdict="beats_comparator" if hp.mape_total_pct < pb.loc[comp, "mape_total_pct"] else "does_not_beat_comparator",
            sample=f"{int(hp.provinces)} provinces; share 60+ MAE {hp.mae_share60_pp:.2f} pp",
            limitation="one origin; not a test of each age group or of a 15-year horizon", source_artifact=rel)
    # ---- Chapter 5: service-rate benchmark backtest
    rel = f"{vdir}/T5_SERVICE_BACKTEST.csv"
    sb = _read(rel)
    for o, g in sb.groupby("outcome"):
        ch = g[g.chosen].iloc[0]
        pers = g[g.method == "constant_last"].iloc[0]
        alt = g[g.method != "constant_last"].sort_values("mape_pct").iloc[0]
        add(check_id=f"C5-SVC-{o}", chapter="5.3", component=f"service-rate benchmark ({o})",
            evidence_type="rolling-origin backtest, conditional on realised population", forecast_origin=f"{int(pers.cutoffs)} cutoffs",
            information_set="rates up to each cutoff; COVID years excluded from windows",
            model=(f"best alternative, not adopted: {alt.method}" if alt.method != ch.method else f"adopted: {alt.method}"),
            comparator="persistence (constant last rate)",
            horizon="1–3 years", metric="province MAPE (%)", value_model=alt.mape_pct, value_comparator=pers.mape_pct,
            verdict="beats_comparator" if alt.mape_pct < pers.mape_pct else "does_not_beat_comparator",
            sample=f"{int(pers.n)} province-cutoff-horizon cells; adopted: {ch.method}"
                   + (" (pre-declared rule: a non-persistence method needs >= 3 cutoffs)" if ch.method != alt.method and alt.mape_pct < pers.mape_pct else ""),
            limitation="uses the target year's actual population, so not a joint population-service forecast",
            source_artifact=rel)
    # ---- Chapter 5: integrated cutoff-safe hindcast (criteria declared beforehand)
    if hindcast is not None:
        pm = hindcast["metrics"]
        pm = pm[(pm.origin == "pooled") & (pm.stratum == "all")].set_index(["model", "horizon"])
        for comp in ["persistence", "population_only"]:
            for hh in [1, 3]:
                add(check_id=f"C5-HINDCAST-h{hh}-vs-{comp}", chapter="5 appendix", component="provincial physician stock (stock-flow engine)",
                    evidence_type="integrated cutoff-safe hindcast, origins 2020-2023", forecast_origin="2020-2023",
                    information_set="stock, events and registers available at each origin; hazards refitted per origin",
                    model="stock-flow, recruitment persistence (unconditional)", comparator=comp.replace("_", " "),
                    horizon=f"{hh} year(s)", metric="province MAE (physicians)",
                    value_model=pm.loc[("stock_flow_unconditional", hh), "mae"], value_comparator=pm.loc[(comp, hh), "mae"],
                    verdict="beats_comparator" if pm.loc[("stock_flow_unconditional", hh), "mae"] < pm.loc[(comp, hh), "mae"] else "does_not_beat_comparator",
                    sample=f"{int(pm.loc[('stock_flow_unconditional', hh), 'n'])} province-origin pairs",
                    limitation="post-2020-break origins only; stock and event universes differ", source_artifact="outputs/chapter5/validation/T5_HINDCAST_METRICS.csv")
        acc = hindcast["acceptance"]
        c2 = acc[acc.criterion.str.startswith("C2")].iloc[0]
        add(check_id="C5-HINDCAST-intervals", chapter="5 appendix", component="90% predictive intervals (hazard + event noise)",
            evidence_type="interval coverage in hindcast", forecast_origin="2020-2023", information_set="as above",
            model="stock-flow simulation", comparator="nominal 90%", horizon="1-5 years", metric="pooled coverage",
            value_model=c2.value, value_comparator=0.90, verdict="beats_comparator" if c2.passed else "does_not_beat_comparator",
            sample="criterion C2 declared in config/validation.toml", limitation=c2.consequence,
            source_artifact="outputs/chapter5/tables/T5A_HINDCAST_ACCEPTANCE.csv")
    # ---- Chapter 5: stock-flow replay
    rel = f"{vdir}/T5_STOCK_FLOW_BACKTEST.csv"
    sf = _read(rel).set_index("year")
    last = sf.index.max()
    add(check_id="C5-STOCK-replay", chapter="5.2", component="physician stock-flow (hazards + actual recruitment)",
        evidence_type="retrospective reconciliation (in-sample hazards, actual recruitment)", forecast_origin="2020",
        information_set="hazards fitted on FY2021–2025, the replay window itself", model="stock-flow identity",
        comparator="none", horizon=f"{len(sf)} years", metric=f"province MAPE {last} (%)",
        value_model=sf.loc[last, "mape_province_pct"], value_comparator=np.nan, verdict="diagnostic_only",
        sample=f"national residual {last}: {sf.loc[last, 'residual']:+.0f} physicians",
        limitation="not out-of-sample; stock (HRR MOPH) and events (HROPS OPS) differ in scope", source_artifact=rel)
    # ---- Chapter 5: M5 support under projected demography
    rel = f"{vdir}/T5_M5_SUPPORT_BY_YEAR.csv"
    ms = _read(rel).set_index("year")
    add(check_id="C5-M5-support", chapter="5.3", component="M5 standardized need (N-STD) under projected ageing",
        evidence_type="support / extrapolation diagnostic", forecast_origin=str(S.base_year), information_set="projected health covariates",
        model="M5 coefficients (Chapter 4)", comparator="training range and Mahalanobis bound", horizon=f"to {ms.index.max()}",
        metric="share of provinces outside support", value_model=ms.loc[ms.index.max(), "share_extrapolation"],
        value_comparator=np.nan, verdict="diagnostic_only",
        sample=f"{ms.loc[ms.index.max(), 'share_extrapolation'] * 76:.0f} of 76 provinces by {ms.index.max()}",
        limitation="long-horizon N-STD extrapolates; evaluate alternatives before using M5 as the sole response", source_artifact=rel)
    # ---- Chapter 5: optimiser / implementation checks
    rel = f"{vdir}/T5_PLAN_INDEX.csv"
    pi = _read(rel)
    ok = pi.all_constraints_ok.astype(str)
    checked = pi[ok.isin(["True", "False"]) & (pi.kind != "status_quo_hist")]
    passed = checked[ok.loc[checked.index] == "True"]
    add(check_id="C5-OPT-constraints", chapter="5.3–5.6", component="allocation MILP (constrained plan jobs)",
        evidence_type="implementation check", forecast_origin="", information_set="", model="HiGHS lexicographic MILP",
        comparator="hard constraints recomputed on the solution", horizon="2026–2040",
        metric="solved constrained plans passing every constraint check", value_model=len(passed), value_comparator=len(checked),
        verdict="implementation_check",
        sample=f"max primary-stage MIP gap {pd.to_numeric(pi.max_mip_gap, errors='coerce').max():.2e}; excluded: "
               f"SQ-HIST (historical rule, unconstrained by design), {int((pi.kind == 'inverse').sum())} inverse LP relaxations, "
               f"{int((~pi.status.isin(['exploratory_policy_scenario', 'solved'])).sum())} jobs infeasible or blocked by design",
        limitation="establishes feasibility and balance for tested cases; near-optimal schedules are not unique",
        source_artifact=rel)
    # ---- scenario-only layers
    add(check_id="C5-B-burden", chapter="4.5 / 5.3", component="expected burden (family B)", evidence_type="scenario_only",
        forecast_origin="2022", information_set="one subnational BOD year; rates fixed", model="age groups x 2022 rates",
        comparator="none possible", horizon="2026–2040", metric="—", verdict="scenario_only",
        limitation="no longitudinal subnational burden to test against; demographic projection under fixed rates",
        source_artifact="outputs/chapter4_5/tables/T45_BURDEN_INDEX.csv")
    add(check_id="C5-HG-health-gain", chapter="5.6", component="amenable burden averted", evidence_type="scenario_only",
        forecast_origin="", information_set="assumed elasticity grid", model="(H/H_cf)^e on amenable YLL",
        comparator="none possible", horizon="2026–2040", metric="—", verdict="scenario_only",
        limitation="no identified physician-to-health effect; ranking of plans is the usable output",
        source_artifact="outputs/chapter5/tables/T5_HEALTH_GAIN_SUMMARY.csv")
    return pd.DataFrame(rows, columns=COLS)


VERDICT_TH = {"beats_comparator": "ดีกว่าตัวเทียบ", "does_not_beat_comparator": "ไม่ดีกว่าตัวเทียบ",
              "diagnostic_only": "การตรวจวินิจฉัย", "implementation_check": "การตรวจการคำนวณ",
              "scenario_only": "ฉากทัศน์เท่านั้น"}


def summary_th(inv: pd.DataFrame) -> pd.DataFrame:
    """Compact Thai view for the report appendix."""
    fmt = lambda v: "" if (v == "" or (isinstance(v, float) and not np.isfinite(v))) else (f"{v:.3g}" if isinstance(v, float) else str(v))
    return pd.DataFrame({"รหัส": inv.check_id, "องค์ประกอบ": inv.component, "ชนิดหลักฐาน": inv.evidence_type,
                         "แบบจำลองที่ทดสอบ": inv.model, "ตัวเทียบ": inv.comparator, "ตัวชี้วัด": inv.metric,
                         "แบบจำลอง": inv.value_model.map(fmt), "ตัวเทียบ (ค่า)": inv.value_comparator.map(fmt),
                         "ผล": inv.verdict.map(VERDICT_TH), "ข้อจำกัด": inv.limitation})


CRITERIA_TH = {
    "C1 forecaster status": ("ทำนายจำนวนแพทย์รายจังหวัด 3 ปีข้างหน้าได้แม่นกว่าวิธีง่ายหรือไม่",
                             "คงจำนวนเดิม (persistence) และปรับตามประชากรอย่างเดียว"),
    "C2 interval calibration (unconditional)": ("ช่วงคาดการณ์ 90% ครอบค่าจริงได้ตามที่ระบุหรือไม่",
                                                "ควรครอบค่าจริงร้อยละ 80–98"),
    "C3 lowest-19 group stability": ("19 จังหวัดที่ขาดมากที่สุดที่ทำนายไว้ ตรงกับที่เกิดจริงหรือไม่",
                                     "Jaccard อย่างน้อย 0.60"),
}


def lab_summary(inv: pd.DataFrame, hindcast: dict) -> dict:
    """Compact, JSON-ready validation view for the Workforce Lab release (plan §8.2): what was held
    out, against which baseline, and where performance is weak."""
    acc = hindcast["acceptance"]
    M = hindcast["metrics"]
    pooled = M[(M.origin == "pooled") & (M.stratum == "all") & (M.horizon == 3)]
    clean = lambda v: None if isinstance(v, float) and not np.isfinite(v) else (float(v) if isinstance(v, (float, np.floating)) else v)
    crit = []
    for r in acc.itertuples(index=False):
        q, b = CRITERIA_TH.get(r.criterion, (r.criterion, r.benchmark))
        crit.append(dict(criterion=r.criterion, question_th=q, comparator_th=b, horizon=str(r.horizon), value=clean(r.value),
                         benchmark=str(r.benchmark), passed=bool(r.passed), consequence=r.consequence))
    models = [dict(model=r.model, mae=clean(r.mae), national_error_pct=clean(r.national_error_pct),
                   jaccard_lowest19=clean(r.jaccard_lowest19), interval_coverage=clean(r.interval_coverage))
              for r in pooled.itertuples(index=False)]
    rows = [{k: clean(v) if not isinstance(v, str) else v for k, v in r.items()}
            for r in inv[["check_id", "component", "evidence_type", "comparator", "metric", "value_model",
                          "value_comparator", "verdict", "limitation"]].to_dict("records")]
    return dict(schema="workforce-lab.validation/1", criteria_file_sha256=hindcast["config_sha256"],
                held_out_th="จำนวนแพทย์ สธ. รายจังหวัดหลังจุดตั้งต้นปี 2563–2566 (ใช้เฉพาะข้อมูลที่มี ณ จุดตั้งต้น) ทำนายถึงปี 2568",
                criteria=crit, hindcast_h3=models, verdict_th=VERDICT_TH, inventory=rows,
                weak=[r["check_id"] for r in rows if r["verdict"] == "does_not_beat_comparator"])
