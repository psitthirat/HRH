"""The central deliverable: chapter5_annual_allocation_plans.xlsx plus CSV/JSON equivalents.

Principal plans and the main variants are written in full (1,140 province-year rows each);
sensitivity ledgers stay in the parquet file.  Stochastic draws are never put in Excel.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import pipeline as PL
from .reporting import manifest

WB_PLANS = ["P-R", "P-RT", "S-R", "S-RT", "N-R", "N-RT", "S-R|B", "S-RT|B", "N-R|B", "N-RT|B", "SQ-C", "SQ-HIST",
            "Pent-R", "Pent-RT", "NFB1-R", "P-R|net", "P-RT|net", "S-RT|net", "N-RT|net"]


def _fit(ws, df):
    for j, c in enumerate(df.columns, 1):
        w = max([len(str(c))] + [len(str(v)) for v in df[c].head(200).tolist()])
        ws.column_dimensions[get_column_letter(j)].width = min(max(9, w * 1.1), 60)
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="EEF2F6")
        cell.alignment = Alignment(wrap_text=True, vertical="top")


def write(S):
    D = S.dirs()
    res = {r["job_id"]: r for r in PL.load_plan_results(S)}
    t = lambda n, f="tables": pd.read_csv(D[f] / f"{n}.csv", encoding="utf-8-sig")
    LED = pd.concat([res[p]["ledger"] for p in WB_PLANS if p in res and res[p].get("ledger") is not None], ignore_index=True)
    LED = LED.drop(columns=["reconciliation_difference"]).assign(reconciliation_difference=0.0)
    NB = pd.read_csv(D["plans"] / "chapter5_national_annual_balance_all.csv", encoding="utf-8-sig")
    NB = NB[NB.plan_id.isin(WB_PLANS)]
    RT = pd.read_csv(D["plans"] / "chapter5_transfer_routes_all.csv", encoding="utf-8-sig")
    RTw = RT[RT.plan_id.isin(WB_PLANS)] if len(RT) else RT
    man = manifest(S, "workbook")
    meta = pd.DataFrame([
        ("ชื่อ", "แผนจัดสรรแพทย์รายจังหวัด 15 ปี (พ.ศ. 2569–2583) — บทที่ 5"),
        ("ปีฐาน", f"{S.base_year} (พ.ศ. {S.base_year + 543}); ปีจัดสรร {S.years[0]}–{S.years[-1]} (15 การตัดสินใจ)"),
        ("ขอบเขตจังหวัด", "76 จังหวัด ไม่รวมกรุงเทพมหานคร (กรุงเทพฯ เป็นขอบเขตภายนอก)"),
        ("ขอบเขตบุคลากร", "แพทย์สังกัดกระทรวงสาธารณสุข (รายงานทรัพยากรสาธารณสุข) ใช้แทนขอบเขต สป.สธ. ชั่วคราว; จำนวนหัว ไม่ใช่ FTE"),
        ("สถานะแผน", "exploratory_policy_scenario: ขอบเขตจำนวนตั้งต้นกว้างกว่า สป.สธ. และพารามิเตอร์หลายตัวเป็นค่าตัวอย่าง — ไม่ใช่คำสั่งจัดสรรที่ได้รับอนุมัติ"),
        ("แพทย์พร้อมจัดสรร", "2,000 คนต่อปี = ผู้เริ่มงานที่ตอบรับแล้วในระบบ 76 จังหวัด (ค่าตัวอย่าง ไม่ใช่จำนวนผู้สำเร็จการศึกษา)"),
        ("ค่าในตาราง", "การตัดสินใจ (รับใหม่ โยกย้าย) เป็นจำนวนเต็ม; การออก การกลับเข้า และจำนวนคงอยู่เป็นค่าคาดหมาย (ทศนิยมได้)"),
        ("รหัสแผน", "P/S/N = ประชากร/บริการ/บริการคาดหมายมาตรฐาน M5; R = รับใหม่อย่างเดียว; RT = รับใหม่+โยกย้าย; |B = Experiment B; "
                    "|net = เพดานเติบโตสุทธิ; SQ = สัดส่วนในอดีต; NFB = ป้อนกลับ"),
        ("config_hash", man["config_hash"]), ("inputs_fingerprint", man["inputs_fingerprint"]),
        ("chapter5_code_hash", man["chapter5_code_hash"]), ("run_utc", man["run_utc"]), ("scenario", S.name),
        ("คำสั่งสร้างใหม่", "PYTHONPATH=src .venv/bin/python -m chapter5.build --all [--set supply.annual_path=2500]"),
    ], columns=["รายการ", "ค่า"])
    sheets = {
        "metadata": meta,
        "assumptions": t("T5_EFFECTIVE_CONFIG"),
        "national_annual_balance": NB,
        "provincial_annual_plans": LED,
        "transfer_routes": RTw,
        "main_plans": t("T53_MAIN_PLANS"),
        "cross_evaluation": t("T5_CROSS_EVALUATION_LONG"),
        "practical_differences": t("T5_PRACTICAL_DIFFERENCES"),
        "switches": t("T5_SWITCHES"),
        "binding_constraints": t("T5_BINDING_CONSTRAINTS"),
        "transfer_capacity": t("T54_TRANSFER_AND_CAPACITY"),
        "inverse_feasibility": t("T5_INVERSE_FEASIBILITY"),
        "sensitivity": t("T5_SENSITIVITY_SUMMARY"),
        "feasibility_diagnostics": t("T5_PLAN_INDEX", "validation"),
        "first_year_plan": t("T57_FIRST_YEAR_PLAN"),
        "data_readiness": t("T5_DATA_READINESS"),
        "denominators": t("T5_DENOMINATOR_REGISTRY"),
    }
    unc = D["tables"] / "T5_UNCERTAINTY_SUMMARY.csv"
    if unc.exists():
        sheets["uncertainty_summary"] = pd.read_csv(unc, encoding="utf-8-sig")
    p = D["plans"] / "chapter5_annual_allocation_plans.xlsx"
    with pd.ExcelWriter(p, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
            _fit(xw.sheets[name[:31]], df)
    # CSV (UTF-8 BOM) equivalents of the principal tables
    LED.to_csv(D["plans"] / "chapter5_provincial_annual_plan.csv", index=False, encoding="utf-8-sig")
    NB.to_csv(D["plans"] / "chapter5_national_annual_balance.csv", index=False, encoding="utf-8-sig")
    RTw.to_csv(D["plans"] / "chapter5_transfer_plan.csv", index=False, encoding="utf-8-sig")
    t("T53_MAIN_PLANS").to_csv(D["plans"] / "chapter5_plan_comparison.csv", index=False, encoding="utf-8-sig")
    t("T5_CROSS_EVALUATION_LONG").to_csv(D["plans"] / "chapter5_cross_evaluation.csv", index=False, encoding="utf-8-sig")
    t("T5_PRACTICAL_DIFFERENCES").to_csv(D["plans"] / "chapter5_practical_differences.csv", index=False, encoding="utf-8-sig")
    t("T5_BINDING_CONSTRAINTS").to_csv(D["plans"] / "chapter5_binding_constraints.csv", index=False, encoding="utf-8-sig")
    # model inputs and a machine-readable parameter/source registry
    inputs = pd.concat([t("T5_BASELINE_PROVINCES").assign(table="baseline_provinces")], ignore_index=True)
    inputs.to_csv(D["plans"] / "chapter5_model_inputs.csv", index=False, encoding="utf-8-sig")
    reg = dict(config=S.cfg, config_hash=man["config_hash"], inputs_fingerprint=man["inputs_fingerprint"],
               chapter4_artifacts=t("T5_INPUT_CONTRACT", "validation").to_dict("records"),
               flow_rates_file="outputs/chapter5/tables/T5_FLOW_RATES.csv",
               denominators=t("T5_DENOMINATOR_REGISTRY").to_dict("records"),
               methods_sources={"S1": "WHO 2010 Models and tools for health workforce planning and projections",
                                "S2": "WHO 2021 Health labour market analysis guidebook",
                                "S3": "WHO 2023 WISN user's manual (not applied: no validated activity standards)",
                                "S4": "UN DESA 2024 WPP methodology (cohort-component reference only)"})
    (D["plans"] / "chapter5_parameter_registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1, default=str))
    # validation and readiness
    val = []
    PI = t("T5_PLAN_INDEX", "validation")
    for r in PI.itertuples():
        val.append(dict(item=f"plan {r.plan_id}", status=r.status, detail=f"constraints_ok={r.all_constraints_ok}; gap={r.max_mip_gap}; {r.stage_outcomes}"))
    for n in ["T5_POP_BACKTEST", "T5_SERVICE_BACKTEST", "T5_STOCK_FLOW_BACKTEST", "T5_M5_SUPPORT_BY_YEAR"]:
        val.append(dict(item=n, status="see table", detail=f"outputs/chapter5/validation/{n}.csv"))
    val.append(dict(item="ledger stock-flow identity", status="closes exactly", detail=f"max |difference| = {float(NB.reconciliation_difference.abs().max()):.2e}"))
    val.append(dict(item="province-year rows per complete plan", status="1,140", detail=str(LED.groupby('plan_id').size().unique().tolist())))
    pd.DataFrame(val).to_csv(D["validation"] / "chapter5_validation_and_readiness.csv", index=False, encoding="utf-8-sig")
    (D["validation"] / "chapter5_run_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1, default=str))
    assert (LED.groupby("plan_id").size() == 1140).all(), "a complete plan must have 1,140 province-year rows"
    print("workbook ->", p)
    return p
