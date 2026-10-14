"""Raw sources -> canonical normalized tables in data/processed/.

Each reader keeps source lineage (source_id, file, sheet) and distinguishes a missing
value from an observed zero.  `build_processed()` writes every table with a metadata
file recording input hashes and the code hash, so a later run can reuse the tables only
when nothing that produced them has changed.

Canonical tables (all keyed on the DOPA two-digit province code `prov_code`):

    province_key            prov_code, province, province_en, health_region, is_bangkok
    workforce_province      year, prov_code, cadre, sector, headcount, source_columns
    services_province       year, prov_code, tier, metric, value, unit
    casemix_hospital        fiscal_year, hospital_code, prov_code, ... (one row per return)
    casemix_province        fiscal_year, prov_code, hospitals, beds, cases_calculated, ip_days, sum_adjrw, cmi
    population_single_age   year, prov_code, sex, age, n             (civil register, age-attributed)
    population_registers    year, prov_code, register, population    (civil_age, civil_grand, nhso_rights)
    population_register_parts  national decomposition of the civil register by year
    nhso_scheme_national    year, right_code, persons
    hdc_indicators          year, prov_code, indicator, numerator, denominator, value, unit
    gpp_province            year, prov_code, gpp_per_capita, gpp_status
    flow_events             fiscal_year, prov_code, row_label, cadre, direction, category, employment_type, events, blank
    flow_published_totals   workbook footers and subtotal columns, for reconciliation
    bod_province            year, prov_code, cause_code, cause_group, cause_en, cause_th,
                            asr_daly, asr_yll, asr_yld, asr_death  (BOD Thailand 2022, per 100,000)
    bod_province_age        year, prov_code, cause_code, cause_group, age_group, age_lo, age_hi,
                            daly, yll, yld, deaths (counts), mid_pop  (BOD Thailand 2022, 8 age groups)
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from . import config as C

PROCESSED = C.PROCESSED
META = PROCESSED / "_build_meta.json"

# ----------------------------------------------------------------------------- helpers

def _norm_name(s) -> str:
    """Thai province label -> canonical name (strip prefix, BOM, whitespace)."""
    s = str(s).replace("﻿", "").strip()
    s = re.sub(r"^จังหวัด", "", s).strip()
    return s


def _log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ----------------------------------------------------------------------------- province key

def read_province_key() -> pd.DataFrame:
    """DOPA province codes and names; English names from the Health Resource Report;
    health regions from the HROPS entry workbook (checked for consistency across years)."""
    f = C.source_path("S03_POP_GRAND", year=C.Y1)
    g = pd.read_excel(f)
    g.columns = [str(c).replace("﻿", "").strip() for c in g.columns]
    prov = g[(g["รหัสจังหวัด"] != 0) & (g["รหัสสำนักทะเบียน"] == 0)]
    key = pd.DataFrame({"prov_code": prov["รหัสจังหวัด"].astype(int),
                        "province": prov["ชื่อจังหวัด"].map(_norm_name)}).drop_duplicates()
    hrr = pd.read_excel(C.source_path("S01_HRR"), sheet_name=str(C.Y1))
    en = dict(zip(hrr["Province (Thai)"].map(_norm_name), hrr["Province (English)"].astype(str).str.strip()))
    key["province_en"] = key.province.map(en)
    # health region from HROPS (col A = region, B = province code, C = province)
    wb = openpyxl.load_workbook(C.source_path("S09_ENTRY"), read_only=True, data_only=True)
    reg_rows = []
    for ws in wb.worksheets:
        for r in ws.iter_rows(min_row=7, values_only=True):
            if isinstance(r[1], (int, float)) and r[2] and isinstance(r[0], (int, float)):
                reg_rows.append((int(r[1]), _norm_name(r[2]), int(r[0]), ws.title))
    reg = pd.DataFrame(reg_rows, columns=["prov_code", "province", "health_region", "sheet"])
    conflicts = reg.groupby("prov_code").health_region.nunique()
    assert (conflicts <= 1).all(), f"health region changes across HROPS sheets: {conflicts[conflicts > 1]}"
    name_conf = reg.merge(key, on="prov_code", suffixes=("_hrops", ""))
    assert (name_conf.province_hrops == name_conf.province).all(), "HROPS province code/name disagrees with DOPA"
    key = key.merge(reg.drop_duplicates("prov_code")[["prov_code", "health_region"]], on="prov_code", how="left")
    key.loc[key.province == C.BANGKOK, "health_region"] = 13
    key["health_region"] = key.health_region.astype(int)
    key["is_bangkok"] = key.province == C.BANGKOK
    assert len(key) == 77 and key.prov_code.is_unique and key.province.is_unique
    assert key.province_en.notna().all()
    return key.sort_values("prov_code").reset_index(drop=True)


def name_to_code(key: pd.DataFrame) -> dict:
    return dict(zip(key.province, key.prov_code))


# ----------------------------------------------------------------------------- Health Resource Report

_SVC_TIER = {"": "all_reporting", "RH": "rh", "GH": "gh", "CH": "ch", "PC": "pc"}
_SVC_METRIC = {"OPDVisits": "op_visits", "Outpatients": "op_persons", "Inpatients": "ip_admissions",
               "LengthofStay": "ip_days", "NoofBeds": "beds"}
SVC_UNIT = {"op_visits": "visits", "op_persons": "persons", "ip_admissions": "admissions",
            "ip_days": "days", "beds": "beds"}


def read_hrr(key: pd.DataFrame):
    """Province-level workforce (cadre x sector) and services (tier x metric), 2013-2025."""
    code = name_to_code(key)
    sectors = C.CFG["sectors"]
    cadres = C.CADRES + C.CFG["cadres"]["diagnostic"]
    xl = pd.ExcelFile(C.source_path("S01_HRR"))
    wf, svc = [], []
    for y in C.YEARS:
        d = xl.parse(str(y))
        prov = d["Province (Thai)"].map(_norm_name)
        assert prov.is_unique and len(prov) == 77, f"{y}: province rows not unique/77"
        pc = prov.map(code)
        assert pc.notna().all(), f"{y}: unmapped province {prov[pc.isna()].tolist()}"
        for col in d.columns:
            c = re.sub(r"\s*\(.*$", "", str(col)).strip()       # drop the Thai gloss
            m = re.match(r"WF_([^_]+)_([A-Za-z]+)$", c)
            if m and m.group(1) in cadres and m.group(2) in sectors:
                wf.append(pd.DataFrame({"year": y, "prov_code": pc.values, "cadre": m.group(1),
                                        "sector": sectors[m.group(2)], "source_column": m.group(2),
                                        "headcount": pd.to_numeric(d[col], errors="coerce").values}))
                continue
            m = re.match(r"SVC_(?:([A-Z]{2})_)?([A-Za-z]+)$", c)
            if m and (m.group(1) or "") in _SVC_TIER and m.group(2) in _SVC_METRIC:
                svc.append(pd.DataFrame({"year": y, "prov_code": pc.values,
                                         "tier": _SVC_TIER[m.group(1) or ""],
                                         "metric": _SVC_METRIC[m.group(2)],
                                         "value": pd.to_numeric(d[col], errors="coerce").values}))
    wf = pd.concat(wf, ignore_index=True)
    # LocalGovernment -> LocalAdministration rename and the several other_public columns are summed
    # into one disjoint sector; min_count keeps an all-missing group missing.
    wf = (wf.groupby(["year", "prov_code", "cadre", "sector"], as_index=False)
            .agg(headcount=("headcount", lambda s: s.sum(min_count=1)),
                 source_columns=("source_column", lambda s: "+".join(sorted(set(s))))))
    wf["source_id"] = "S01_HRR"
    svc = pd.concat(svc, ignore_index=True)
    dup = svc.duplicated(["year", "prov_code", "tier", "metric"])
    assert not dup.any(), "duplicate service columns after gloss removal"
    svc["unit"] = svc.metric.map(SVC_UNIT)
    svc["source_id"] = "S01_HRR"
    return wf, svc


# ----------------------------------------------------------------------------- population

def read_population_age(key: pd.DataFrame):
    """Civil register by single year of age and sex (village rows summed to province),
    plus the file's own decomposition of the published total."""
    code = name_to_code(key)
    frames, audit = [], []
    for y in C.YEARS:
        f = C.source_path("S02_POP_AGE", year=y)
        d = pd.read_excel(f)
        d.columns = [str(c).replace("﻿", "").strip() for c in d.columns]
        ym = str(d["ปีเดือน"].iloc[0]).replace("﻿", "")
        agecols = [c for c in d.columns if c.startswith(("ชาย", "หญิง"))]
        lunar = [c for c in agecols if "จันทรคติ" in c]
        single = [c for c in agecols if c not in lunar]
        d["prov_code"] = pd.to_numeric(d["รหัสจังหวัด"], errors="coerce").astype(int)
        grp = d.groupby("prov_code")
        num = grp[single].sum(numeric_only=True)
        long = num.reset_index().melt(id_vars="prov_code", var_name="col", value_name="n")
        long["sex"] = np.where(long.col.str.startswith("ชาย"), "M", "F")
        txt = long.col.str.replace("ชาย", "", regex=False).str.replace("หญิง", "", regex=False).str.strip()
        long["age"] = np.where(txt.str.startswith("<"), 0,
                               np.where(txt.str.startswith(">"), 101,
                                        pd.to_numeric(txt.str.replace("ปี", "", regex=False).str.strip(),
                                                      errors="coerce")))
        assert long.age.notna().all(), f"{y}: unparsed age columns"
        long = long.groupby(["prov_code", "sex", "age"], as_index=False).n.sum()
        long["year"] = y
        frames.append(long)

        def col_sum(name):
            return float(pd.to_numeric(d[name], errors="coerce").fillna(0).sum()) if name in d else np.nan

        parts = dict(age_attributed=float(long.n.sum()),
                     lunar_birth_year=col_sum("ผลรวมประชากรที่เกิดปีจันทรคติ"),
                     central_household_registry=col_sum("ผลรวมประชากรที่มีชื่ออยู่ในทะเบียนบ้านกลาง"),
                     non_thai_nationality=col_sum("ผลรวมประชากรที่มิใช่สัญชาติไทย"),
                     in_transit=col_sum("ผลรวมประชากรที่อยู่ระหว่างการย้าย"))
        audit.append(dict(year=y, reference_month=ym, **parts,
                          file_grand_total=col_sum("ผลรวมประชากรทั้งหมด")))
        # province-level decomposition too (needed for the province bridge)
        _log(f"population age file {y}: {long.n.sum():,.0f} persons")
    out = pd.concat(frames, ignore_index=True)[["year", "prov_code", "sex", "age", "n"]]
    out["age"] = out.age.astype(int)
    assert set(out.prov_code) == set(key.prov_code)
    parts = pd.DataFrame(audit)
    parts["sum_of_parts"] = parts[["age_attributed", "lunar_birth_year", "central_household_registry",
                                   "non_thai_nationality", "in_transit"]].sum(axis=1)
    parts["identity_gap"] = parts.sum_of_parts - parts.file_grand_total
    return out, parts


def read_population_grand(key: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in C.YEARS:
        f = C.source_path("S03_POP_GRAND", year=y)
        d = pd.read_excel(f)
        d.columns = [str(c).replace("﻿", "").strip() for c in d.columns]
        nat = float(d.loc[d["รหัสจังหวัด"] == 0, "จำนวนประชากรทั้งหมด"].iloc[0])
        p = d[(d["รหัสจังหวัด"] != 0) & (d["รหัสสำนักทะเบียน"] == 0)]
        g = pd.DataFrame({"year": y, "prov_code": p["รหัสจังหวัด"].astype(int),
                          "population": p["จำนวนประชากรทั้งหมด"].astype(float), "national_row": nat})
        assert abs(g.population.sum() - nat) < 1, f"{y}: provinces do not sum to the national row"
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


def read_nhso(key: pd.DataFrame):
    """Entitlement register: persons by year x province x right code x age band x sex."""
    f = C.source_path("S04_NHSO")
    d = pd.read_csv(f, dtype={"month_no": str, "right_code": str, "province_code": str,
                              "hospital_code": str, "sex_code": str},
                    usecols=["month_no", "right_code", "province_code", "sex_code", "age_no", "m_population"])
    d["year"] = d.month_no.str[:4].astype(int)
    d["month"] = d.month_no.str[4:]
    d["prov_code"] = pd.to_numeric(d.province_code.str[:2], errors="coerce")
    d["age_band"] = pd.cut(d.age_no, [-10_000, -1, 14, 59, 200, 10_000],
                           labels=["invalid_negative", "0-14", "15-59", "60+", "invalid_over_200"])
    audit = (d.assign(unknown_province=d.prov_code.isna() | ~d.prov_code.isin(key.prov_code),
                      age_invalid=(d.age_no < 0) | (d.age_no > 110),
                      sex_unknown=~d.sex_code.isin(["1", "2"]))
               .groupby(["year", "month"])
               .apply(lambda g: pd.Series({
                   "persons": g.m_population.sum(),
                   "persons_unknown_province": g.loc[g.unknown_province, "m_population"].sum(),
                   "persons_age_invalid": g.loc[g.age_invalid, "m_population"].sum(),
                   "persons_sex_unknown": g.loc[g.sex_unknown, "m_population"].sum(),
                   "right_codes": g.right_code.nunique()}), include_groups=False)
               .reset_index())
    agg = (d.groupby(["year", "month", "prov_code", "right_code", "age_band", "sex_code"],
                     dropna=False, observed=True, as_index=False).m_population.sum()
             .rename(columns={"m_population": "persons"}))
    return agg, audit


# ----------------------------------------------------------------------------- case mix

def read_casemix(key: pd.DataFrame):
    code = name_to_code(key)
    frames = []
    for f in sorted(C.source_path("S05_CASEMIX").glob("CMI_*.xlsx")):
        fy = int(re.search(r"(\d{4})", f.name).group(1))
        d = pd.read_excel(f)
        d.columns = [str(c).strip() for c in d.columns]
        prov = d["จังหวัด"].map(_norm_name)
        frames.append(pd.DataFrame({
            "fiscal_year": fy, "prov_code": prov.map(code), "province_raw": prov,
            "hospital_code": d["รหัส ร.พ."].astype(str).str.strip(),
            "hospital": d["โรงพยาบาล"].astype(str), "hospital_type": d["ประเภท"].astype(str),
            "beds": pd.to_numeric(d["เตียง"], errors="coerce"),
            "months_sent": pd.to_numeric(d["จำนวนเดือนที่ส่ง"], errors="coerce"),
            "cases_sent": pd.to_numeric(d["จำนวนส่ง"], errors="coerce"),
            "cases_calculated": pd.to_numeric(d["จำนวนคำนวณ"], errors="coerce"),
            "ip_days": pd.to_numeric(d["วันนอนรวม"], errors="coerce"),
            "sum_adjrw": pd.to_numeric(d["SumAdjRW"], errors="coerce"),
            "cmi_reported": pd.to_numeric(d["CMI"], errors="coerce"),
            "source_file": f.name}))
    h = pd.concat(frames, ignore_index=True)
    assert h.prov_code.notna().all(), "case-mix province not mapped"
    h["prov_code"] = h.prov_code.astype(int)
    assert not h.duplicated(["fiscal_year", "hospital_code"]).any(), "duplicate hospital returns"
    # CMI identity at hospital level: reported CMI == SumAdjRW / calculated cases (4 d.p. rounding)
    h["cmi_recomputed"] = h.sum_adjrw / h.cases_calculated
    h["cmi_identity_gap"] = h.cmi_reported - h.cmi_recomputed
    prov = (h.groupby(["fiscal_year", "prov_code"], as_index=False)
              .agg(hospitals=("hospital_code", "nunique"), beds=("beds", "sum"),
                   cases_calculated=("cases_calculated", "sum"), ip_days=("ip_days", "sum"),
                   sum_adjrw=("sum_adjrw", "sum"),
                   hospitals_partial_year=("months_sent", lambda s: int((s < 12).sum()))))
    prov["cmi"] = prov.sum_adjrw / prov.cases_calculated          # ratio of sums, never a mean of CMIs
    return h, prov


# ----------------------------------------------------------------------------- HDC and GPP

HDC_PREVALENCE = {
    "prev_dm": ("s_dm_pop_age.csv", "result", "pop", "เบาหวาน"),
    "prev_ht": ("s_ht_pop_age.csv", "result", "pop", "ความดันโลหิตสูง"),
    "prev_copd": ("s_copd_pop_age.csv", "result", "pop", "ปอดอุดกั้นเรื้อรัง"),
    "prev_stroke": ("s_stroke_pop_age.csv", "result", "pop", "โรคหลอดเลือดสมอง"),
    "prev_chd": ("s_coronary_pop_age.csv", "result", "pop", "โรคหลอดเลือดหัวใจ"),
}
HDC_ACTIVITY = {
    "dental_visits": ("s_dental_2.csv", "visits", "ทันตแพทย์", "ครั้งบริการทันตกรรม (ทุกสิทธิ)", "visits"),
    "op_prescriptions": ("s_pharm1.csv", "op_prescriptions", "เภสัชกร", "ใบสั่งยาผู้ป่วยนอก", "prescriptions"),
    "pharm_ip_days": ("s_pharm2.csv", "length_of_stay", "เภสัชกร", "วันนอน (ตัวแทนงานเภสัชกรรมผู้ป่วยใน)", "days"),
}


def read_hdc(key: pd.DataFrame) -> pd.DataFrame:
    code = name_to_code(key)
    d0 = C.source_path("S06_HDC_PREV")
    rows = []
    for ind, (fn, num, den, label) in HDC_PREVALENCE.items():
        d = pd.read_csv(d0 / fn)
        d["prov_code"] = d.prov.map(_norm_name).map(code)
        assert (d.prov_code == d.prov_id).all(), f"{fn}: prov_id disagrees with name"
        n = pd.to_numeric(d[num], errors="coerce")
        p = pd.to_numeric(d[den], errors="coerce")
        v = 100 * n / p
        # the file's own percentage must equal numerator/denominator (unit check)
        gap = (v - pd.to_numeric(d.prevalence_pct, errors="coerce")).abs().max()
        assert gap < 1e-6, f"{fn}: prevalence_pct is not 100*result/pop (gap {gap})"
        rows.append(pd.DataFrame({"year": d.year, "prov_code": d.prov_code, "indicator": ind,
                                  "label_th": label, "numerator": n, "denominator": p, "value": v,
                                  "unit": "percent", "source_file": fn}))
    ckd = pd.read_csv(d0 / "s_ckd_stage_typearea.csv")
    ckd["prov_code"] = ckd.prov.map(_norm_name).map(code)
    n = ckd[["stage3", "stage4", "stage5"]].sum(axis=1, min_count=3)
    p = pd.to_numeric(ckd["pop"], errors="coerce")
    rows.append(pd.DataFrame({"year": ckd.year, "prov_code": ckd.prov_code, "indicator": "prev_ckd_3_5",
                              "label_th": "โรคไตเรื้อรังระยะ 3–5", "numerator": n, "denominator": p,
                              "value": 100 * n / p, "unit": "percent",
                              "source_file": "s_ckd_stage_typearea.csv"}))
    for aid, (fn, col, cadre, label, unit) in HDC_ACTIVITY.items():
        d = pd.read_csv(d0 / fn)
        d["prov_code"] = d.prov.map(_norm_name).map(code)
        rows.append(pd.DataFrame({"year": d.year, "prov_code": d.prov_code, "indicator": aid,
                                  "label_th": label, "numerator": pd.to_numeric(d[col], errors="coerce"),
                                  "denominator": pd.to_numeric(d.get("pop"), errors="coerce") if "pop" in d else np.nan,
                                  "value": pd.to_numeric(d[col], errors="coerce"), "unit": unit,
                                  "source_file": fn, "cadre": cadre}))
    out = pd.concat(rows, ignore_index=True)
    assert out.prov_code.notna().all(), "HDC province not mapped"
    out["prov_code"] = out.prov_code.astype(int)
    dup = out.duplicated(["year", "prov_code", "indicator"])
    assert not dup.any(), f"duplicate HDC rows: {out[dup].head()}"
    return out


# NESDC English spellings that differ from the Health Resource Report's (documented aliases)
_GPP_ALIAS_TH = {"BANGKOKMETROPOLIS": "กรุงเทพมหานคร", "PHRANAKHONSRIAYUTHAYA": "พระนครศรีอยุธยา",
                 "AMNATCHAREON": "อำนาจเจริญ", "BUENGKAN": "บึงกาฬ", "SAKAEW": "สระแก้ว",
                 "NONGBUALAMPHU": "หนองบัวลำภู", "PHACHUAPKHIRIKHAN": "ประจวบคีรีขันธ์"}


def read_bod(key: pd.DataFrame) -> pd.DataFrame:
    """Provincial burden of disease 2022 (BOD Thailand).  One row per province x Level-3 cause with
    the four age-standardized rates per 100,000.  The source's area code P<nn> is checked against
    the Thai name, and the source's own identity DALY = YLL + YLD is re-verified."""
    code = name_to_code(key)
    f = C.source_path("S14_BOD")
    d = pd.read_excel(f, sheet_name="Provincial_ASR")
    d["prov_code"] = d.area_name_th.map(_norm_name).map(code)
    assert d.prov_code.notna().all(), f"BOD province not mapped: {d.loc[d.prov_code.isna(), 'area_name_th'].unique()}"
    assert (d.area_name.str[1:].astype(int) == d.prov_code).all(), "BOD area code disagrees with province name"
    assert (d.sex_name_th == "รวมเพศ").all() and d.year_ce.nunique() == 1
    gap = (d.ASR_DALY - d.ASR_YLL - d.ASR_YLD).abs().max()
    assert gap < 1e-6, f"BOD: DALY != YLL + YLD (gap {gap})"
    assert not d.duplicated(["prov_code", "codv"]).any(), "duplicate BOD province-cause rows"
    assert d.groupby("prov_code").codv.nunique().eq(174).all() and d.prov_code.nunique() == 77
    num = d[["ASR_DALY", "ASR_YLL", "ASR_YLD", "ASR_Death"]]
    assert np.isfinite(num.to_numpy(float)).all() and (num >= 0).all().all()
    groups = C.CFG["burden"]["groups"]
    letter = d.codv.str[0]
    grp = letter.map({ch: g for g, chars in groups.items() for ch in chars})
    assert grp.notna().all(), f"BOD cause letters without a group: {letter[grp.isna()].unique()}"
    return pd.DataFrame({"year": d.year_ce.astype(int), "prov_code": d.prov_code.astype(int), "cause_code": d.codv,
                         "cause_group": grp, "cause_en": d.codv_name_eng, "cause_th": d.codv_name_th,
                         "asr_daly": d.ASR_DALY, "asr_yll": d.ASR_YLL, "asr_yld": d.ASR_YLD,
                         "asr_death": d.ASR_Death, "unit": "age-standardized per 100,000 (WHO standard)"})


def read_bod_age(key: pd.DataFrame, bod: pd.DataFrame, path=None, check_asr: bool = True) -> pd.DataFrame:
    """Provincial burden of disease 2022 by 8 age groups (counts and mid-year population).

    Checks: complete province x cause x age grid; DALY = YLL + YLD; each rate = count / mid_pop
    x 100,000; one mid_pop per province-age; and the age-specific rates, standardized with the WHO
    world standard collapsed to the same 8 groups, reproduce the S14_BOD age-standardized DALY
    rates of every province-cause to the rounding of the published weights (max relative gap
    3e-4), so both files are the same estimates."""
    code = name_to_code(key)
    d = pd.read_csv(path if path is not None else C.source_path("S15_BOD_AGE"))
    d.columns = [c.replace("\ufeff", "") for c in d.columns]
    d["prov_code"] = d.area_name_th.map(_norm_name).map(code)
    assert d.prov_code.notna().all() and (d.area_name.str[1:].astype(int) == d.prov_code).all()
    assert (d.sex_name_th == "รวมเพศ").all() and d.year_ce.nunique() == 1
    assert not d.duplicated(["prov_code", "codv", "age_grp8"]).any()
    assert len(d) == 77 * 174 * 8, f"BOD age grid incomplete: {len(d)} rows"
    assert (d.DALY - d.YLL - d.YLD_NEW).abs().max() < 1e-6, "BOD age: DALY != YLL + YLD"
    for cnt, rate in [("DALY", "DALY_rate"), ("YLL", "YLL_rate"), ("YLD_NEW", "YLD_rate"), ("deaths", "death_rate")]:
        assert (1e5 * d[cnt] / d.mid_pop - d[rate]).abs().max() < 1e-6, f"BOD age: {rate} != {cnt}/mid_pop"
    assert d.groupby(["prov_code", "age_grp8"]).mid_pop.nunique().eq(1).all()
    bands = C.CFG["burden"]["age_groups"]
    assert d.age_grp8.nunique() == len(bands)
    who = np.array(C.CFG["burden"]["who_standard"], float)
    edges = [0, 1, 3, 6, 9, 12, 14, 16, len(who)]                # 5-year WHO groups -> the 8 source groups
    w8 = np.array([who[a:b].sum() for a, b in zip(edges[:-1], edges[1:])])
    w8 = w8 / w8.sum()
    rt = d.pivot_table(index=["prov_code", "codv"], columns="age_grp8", values="DALY_rate").sort_index(axis=1)
    asr = pd.Series(rt.to_numpy() @ w8, index=rt.index)
    ref = bod.set_index(["prov_code", "cause_code"]).asr_daly.reindex(asr.index)
    # the WHO weights are published to 0.01 per 100, so agreement is to rounding, not to machine precision
    rel = float(((asr - ref).abs() / ref.clip(lower=1.0)).max())
    if check_asr:       # a replacement dataset (workspace) may legitimately change rates; it skips this check
        assert rel < 1e-3, f"BOD age rates do not reproduce the published ASR (max relative gap {rel:.2e})"
    grp = bod.drop_duplicates("cause_code").set_index("cause_code").cause_group
    lo = {i + 1: b[0] for i, b in enumerate(bands)}
    hi = {i + 1: b[1] for i, b in enumerate(bands)}
    return pd.DataFrame({"year": d.year_ce.astype(int), "prov_code": d.prov_code.astype(int), "cause_code": d.codv,
                         "cause_group": d.codv.map(grp), "age_group": d.age_grp8.astype(int),
                         "age_lo": d.age_grp8.map(lo), "age_hi": d.age_grp8.map(hi),
                         "daly": d.DALY, "yll": d.YLL, "yld": d.YLD_NEW, "deaths": d.deaths,
                         "mid_pop": d.mid_pop.astype(float)})


def read_gpp(key: pd.DataFrame) -> pd.DataFrame:
    d = pd.read_excel(C.source_path("S08_GPP"))
    k = d.province.astype(str).str.upper().str.replace(" ", "", regex=False)
    en2code = {str(e).upper().replace(" ", ""): c for e, c in zip(key.province_en, key.prov_code)}
    th2code = name_to_code(key)
    for a, th in _GPP_ALIAS_TH.items():
        en2code.setdefault(a, th2code[th])
    d["prov_code"] = k.map(en2code)
    assert d.prov_code.notna().all(), f"unmatched GPP provinces: {d.province[d.prov_code.isna()].tolist()}"
    long = d.drop(columns="province").melt(id_vars="prov_code", var_name="year_raw", value_name="gpp_per_capita")
    long["year"] = long.year_raw.astype(str).str.extract(r"(\d{4})")[0].astype(int)
    long["gpp_status"] = long.year_raw.astype(str).str.extract(r"\d{4}([rp]?)")[0].replace(
        {"r": "revised", "p": "preliminary", "": "final"})
    long["prov_code"] = long.prov_code.astype(int)
    assert not long.duplicated(["year", "prov_code"]).any()
    return long[["year", "prov_code", "gpp_per_capita", "gpp_status"]]


# ----------------------------------------------------------------------------- HROPS flows

ENTRY_CATEGORY = {"บรรจุ/จัดจ้างผู้ผ่านฯ/จ้าง": "recruitment_hiring", "บรรจุกลับ": "reinstatement",
                  "รับโอน": "transfer_in"}
EXIT_CATEGORY = {"1.ลาออก": "resignation", "2.เกษียณอายุ": "retirement", "3.โอน": "transfer_out",
                 "4.โทษทางวินัย": "disciplinary", "5.เสียชีวิต": "death"}
EMPLOYMENT = {"ขรก.": "civil_servant", "พรก.": "government_employee", "พกส.": "moph_employee",
              "ลจค.": "permanent_employee"}
HROPS_CADRE = {"นายแพทย์": "แพทย์", "ทันตแพทย์": "ทันตแพทย์", "เภสัชกร": "เภสัชกร",
               "พยาบาลวิชาชีพ": "พยาบาลวิชาชีพ", "นักกายภาพบำบัด": "นักกายภาพบำบัด",
               "นักเทคนิคการแพทย์": "นักเทคนิคการแพทย์", "นักวิชาการสาธารณสุข": "นักวิชาการสาธารณสุข"}


def _grid(ws, rows):
    """Header rows with merged ranges filled in, as {row: {col: value}}."""
    g = {r: {c.column: c.value for c in ws[r]} for r in rows}
    for rng in ws.merged_cells.ranges:
        v = ws.cell(rng.min_row, rng.min_col).value
        for r in range(rng.min_row, rng.max_row + 1):
            if r in g:
                for c in range(rng.min_col, rng.max_col + 1):
                    g[r][c] = v
    return g


def _clean(v):
    return re.sub(r"\s+", "", str(v)) if v is not None else None


def parse_entry(key: pd.DataFrame, path: Path | None = None):
    """Recorded entries: one row per province x cadre x category x employment type, plus
    every subtotal/total column and the workbook footer kept separately for reconciliation."""
    path = path or C.source_path("S09_ENTRY")
    code = name_to_code(key)
    wb = openpyxl.load_workbook(path, data_only=True)
    wbf = openpyxl.load_workbook(path, data_only=False)
    ev, pub, meta = [], [], []
    for ws in wb.worksheets:
        fy = int(re.search(r"(\d{2})", ws.title).group(1)) + 2500 - C.BE
        g = _grid(ws, [4, 5, 6])
        cols = {}
        for c in range(4, ws.max_column + 1):
            h4, h5, h6 = _clean(g[4].get(c)), _clean(g[5].get(c)), _clean(g[6].get(c))
            if h4 is None:
                continue
            if h4 == "รวมทั้งหมด":
                cols[c] = ("ALL", "grand_total", None, "total")
            elif h4.startswith("รวม"):
                cols[c] = (HROPS_CADRE[h4[3:]], "cadre_total", None, "total")
            else:
                cad = HROPS_CADRE[h4]
                if h5 == "รวม":
                    # a category subtotal belongs to the category immediately to its left
                    prev = cols.get(c - 1)
                    cols[c] = (cad, prev[1] if prev else None, None, "category_total")
                else:
                    cols[c] = (cad, ENTRY_CATEGORY[h5], EMPLOYMENT.get(h6, h6), "component")
        # a category subtotal must follow its components; verify every category_total resolved
        assert all(v[1] is not None for v in cols.values()), f"{ws.title}: unresolved subtotal column"
        for r in range(7, ws.max_row + 1):
            a, b, lab = ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value
            if lab is None and a is None:
                continue
            is_footer = str(a).strip() == "รวม"
            label = "FOOTER" if is_footer else _norm_name(lab)
            pcode = code.get(label, np.nan)
            row_type = "footer" if is_footer else ("province" if pcode == pcode else "central_office")
            for c, (cad, cat, emp, kind) in cols.items():
                v = ws.cell(r, c).value
                fcell = wbf[ws.title].cell(r, c).value
                formula = fcell if isinstance(fcell, str) and fcell.startswith("=") else None
                rec = dict(fiscal_year=fy, sheet=ws.title, row=r, row_type=row_type, row_label=label,
                           prov_code=pcode, health_region=a if row_type == "province" else np.nan,
                           cadre=cad, direction="entry", category=cat, employment_type=emp,
                           column_kind=kind, excel_col=c, events=np.nan if v is None else float(v),
                           blank=v is None, formula=formula)
                (ev if kind == "component" and row_type != "footer" else pub).append(rec)
        meta.append(dict(sheet=ws.title, fiscal_year=fy, title=ws.cell(1, 1).value,
                         note=ws.cell(2, 1).value, max_row=ws.max_row, max_col=ws.max_column))
    return pd.DataFrame(ev), pd.DataFrame(pub), pd.DataFrame(meta)


def parse_exit(key: pd.DataFrame):
    """Recorded exits from the per-cadre sheets (reason x fiscal year blocks)."""
    path = C.source_path("S10_EXIT")
    code = name_to_code(key)
    wb = openpyxl.load_workbook(path, data_only=True)
    wbf = openpyxl.load_workbook(path, data_only=False)
    ev, pub, meta = [], [], []
    for ws in wb.worksheets:
        if ws.title == "สรุป":
            continue
        g = _grid(ws, [4, 5, 6])
        cols = {}
        last_h5 = None
        for c in range(3, ws.max_column + 1):
            h4, h5, h6 = _clean(g[4].get(c)), g[5].get(c), _clean(g[6].get(c))
            if h4 is None:
                continue
            if h4.startswith("ผลรวมทั้งหมด"):
                cols[c] = (None, "all_years_total", "total")
                continue
            h5 = h5 if h5 is not None else last_h5      # unmerged year label: carry forward
            last_h5 = h5
            m = re.search(r"(\d{4})", str(h5))
            fy = int(m.group(1)) - C.BE
            if h6 == "ผลรวม":
                cols[c] = (fy, "total", "total")
            else:
                cols[c] = (fy, EXIT_CATEGORY[h6], "component")
        cad = HROPS_CADRE[_clean(ws.cell(4, 3).value)]
        for r in range(7, ws.max_row + 1):
            a, lab = ws.cell(r, 1).value, ws.cell(r, 2).value
            if a is None and lab is None:
                continue
            is_footer = str(a).strip().startswith("ผลรวม")
            label = "FOOTER" if is_footer else _norm_name(lab)
            pcode = code.get(label, np.nan)
            row_type = "footer" if is_footer else ("province" if pcode == pcode else "central_office")
            for c, (fy, cat, kind) in cols.items():
                v = ws.cell(r, c).value
                fcell = wbf[ws.title].cell(r, c).value
                formula = fcell if isinstance(fcell, str) and fcell.startswith("=") else None
                rec = dict(fiscal_year=fy, sheet=ws.title, row=r, row_type=row_type, row_label=label,
                           prov_code=pcode, health_region=a if row_type == "province" else np.nan,
                           cadre=cad, direction="exit", category=cat, employment_type=None,
                           column_kind=kind, excel_col=c, events=np.nan if v is None else float(v),
                           blank=v is None, formula=formula)
                (ev if kind == "component" and row_type != "footer" else pub).append(rec)
        meta.append(dict(sheet=ws.title, cadre=cad, title=ws.cell(1, 1).value, note=ws.cell(2, 1).value,
                         note2=ws.cell(3, 1).value, max_row=ws.max_row, max_col=ws.max_column))
    # the summary sheet (region x cadre x reason, all years pooled) is kept for reconciliation
    ws = wb["สรุป"]
    g = _grid(ws, [4, 5])
    for r in range(6, ws.max_row + 1):
        lab = ws.cell(r, 1).value
        if lab is None:
            continue
        for c in range(2, ws.max_column + 1):
            h4, h5 = _clean(g[4].get(c)), _clean(g[5].get(c))
            if h4 is None:
                continue
            pub.append(dict(fiscal_year=np.nan, sheet="สรุป", row=r, row_type="summary_region",
                            row_label=str(lab), prov_code=np.nan, health_region=lab, cadre=HROPS_CADRE.get(h4, h4),
                            direction="exit", category=EXIT_CATEGORY.get(h5, "total" if h5 == "ผลรวม" else h5),
                            employment_type=None, column_kind="summary", excel_col=c,
                            events=ws.cell(r, c).value, blank=ws.cell(r, c).value is None, formula=None))
    return pd.DataFrame(ev), pd.DataFrame(pub), pd.DataFrame(meta)


def parse_entry_condensed(key: pd.DataFrame) -> pd.DataFrame:
    """The condensed-layout copy of the entry extract: category totals per province/cadre."""
    path = C.source_path("S11_ENTRY_CONDENSED")
    code = name_to_code(key)
    wb = openpyxl.load_workbook(path, data_only=True)
    out = []
    for ws in wb.worksheets:
        fy = int(re.search(r"(\d{2})", ws.title).group(1)) + 2500 - C.BE
        # find the two header rows: the row whose col C is 'จังหวัด'
        hdr = next(r for r in range(1, 10) if _clean(ws.cell(r, 3).value) == "จังหวัด")
        g = _grid(ws, [hdr, hdr + 1])
        cols = {}
        for c in range(4, ws.max_column + 1):
            h1, h2 = _clean(g[hdr].get(c)), _clean(g[hdr + 1].get(c))
            if h1 is None or h1.startswith("รวม"):
                continue
            cad = HROPS_CADRE.get(h1)
            if cad is None:
                continue
            cols[c] = (cad, "total" if h2 == "รวม" else ENTRY_CATEGORY.get(h2, h2))
        for r in range(hdr + 2, ws.max_row + 1):
            lab = ws.cell(r, 3).value
            if lab is None:
                continue
            label = _norm_name(lab)
            for c, (cad, cat) in cols.items():
                v = ws.cell(r, c).value
                out.append(dict(fiscal_year=fy, row_label=label, prov_code=code.get(label, np.nan),
                                cadre=cad, category=cat, events=np.nan if v is None else float(v)))
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------- build / load

TABLES = ["province_key", "workforce_province", "services_province", "casemix_hospital",
          "casemix_province", "population_single_age", "population_registers",
          "population_register_parts", "nhso_province_scheme_age", "nhso_audit", "hdc_indicators",
          "gpp_province", "flow_events", "flow_published", "flow_sheet_meta",
          "flow_entry_condensed", "bod_province", "bod_province_age"]


def _inputs() -> dict:
    ids = ["S01_HRR", "S02_POP_AGE", "S03_POP_GRAND", "S04_NHSO", "S05_CASEMIX", "S06_HDC_PREV",
           "S07_HDC_ACTIVITY", "S08_GPP", "S09_ENTRY", "S10_EXIT", "S11_ENTRY_CONDENSED", "S14_BOD", "S15_BOD_AGE"]
    return {i: C.source_fingerprint(i) for i in ids}


def is_current() -> bool:
    if not META.exists():
        return False
    m = json.loads(META.read_text())
    if m.get("code_hash") != C.code_hash_ingest():
        return False
    if m.get("inputs") != _inputs():
        return False
    return all((PROCESSED / f"{t}.csv").exists() for t in TABLES)


def build_processed(force: bool = False) -> dict:
    """Read every raw source and write the canonical tables.  Returns the metadata."""
    if not force and is_current():
        _log("processed tables are current (inputs and code unchanged) - reusing")
        return json.loads(META.read_text())
    PROCESSED.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    key = read_province_key()
    _log("province key ok")
    wf, svc = read_hrr(key)
    _log(f"health resource report: {len(wf):,} workforce rows, {len(svc):,} service rows")
    h, cp = read_casemix(key)
    pop_age, parts = read_population_age(key)
    grand = read_population_grand(key)
    nhso, nhso_audit = read_nhso(key)
    _log("nhso register aggregated")
    hdc = read_hdc(key)
    bod = read_bod(key)
    bod_age = read_bod_age(key, bod)
    _log(f"burden of disease: {bod.prov_code.nunique()} provinces x {bod.cause_code.nunique()} causes")
    gpp = read_gpp(key)
    en_ev, en_pub, en_meta = parse_entry(key)
    ex_ev, ex_pub, ex_meta = parse_exit(key)
    cond = parse_entry_condensed(key)
    _log("HROPS workbooks parsed")

    # population registers at province level
    ages = pop_age.groupby(["year", "prov_code"], as_index=False).n.sum().rename(columns={"n": "population"})
    nh_dec = nhso[nhso.month == "12"] if (nhso.month == "12").any() else nhso
    nh_prov = (nh_dec[nh_dec.prov_code.isin(key.prov_code)].groupby(["year", "prov_code"], as_index=False)
               .persons.sum().rename(columns={"persons": "population"}))
    regs = pd.concat([ages.assign(register="civil_age"),
                      grand[["year", "prov_code", "population"]].assign(register="civil_grand"),
                      nh_prov.assign(register="nhso_rights")], ignore_index=True)
    regs["prov_code"] = regs.prov_code.astype(int)
    # national rows of the entitlement register include codes without a province; keep them
    nh_nat = nh_dec.groupby("year", as_index=False).persons.sum()
    parts = parts.merge(grand.groupby("year", as_index=False).national_row.first(), on="year")
    parts = parts.merge(nh_nat.rename(columns={"persons": "nhso_national_total"}), on="year", how="left")

    flows = pd.concat([en_ev, ex_ev], ignore_index=True)
    pub = pd.concat([en_pub.assign(workbook="entry"), ex_pub.assign(workbook="exit")], ignore_index=True)
    fmeta = pd.concat([en_meta.assign(workbook="entry"), ex_meta.assign(workbook="exit")], ignore_index=True)

    out = {"province_key": key, "workforce_province": wf, "services_province": svc,
           "casemix_hospital": h, "casemix_province": cp, "population_single_age": pop_age,
           "population_registers": regs, "population_register_parts": parts,
           "nhso_province_scheme_age": nhso, "nhso_audit": nhso_audit, "hdc_indicators": hdc,
           "gpp_province": gpp, "flow_events": flows, "flow_published": pub,
           "flow_sheet_meta": fmeta, "flow_entry_condensed": cond, "bod_province": bod,
           "bod_province_age": bod_age}
    for name, df in out.items():
        df.to_csv(PROCESSED / f"{name}.csv", index=False, encoding="utf-8")
    meta = dict(built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                code_hash=C.code_hash_ingest(), inputs=_inputs(),
                rows={k: int(len(v)) for k, v in out.items()}, seconds=round(time.time() - t0, 1))
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    _log(f"processed tables written in {meta['seconds']} s")
    return meta


_DTYPES = {"right_code": str, "sex_code": str, "month": str, "formula": str, "employment_type": str}


def load(name: str) -> pd.DataFrame:
    """Read one canonical table.  Raises with the build command if the table is missing or stale."""
    p = PROCESSED / f"{name}.csv"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing - run: .venv/bin/python -m chapter4.build --shared")
    return pd.read_csv(p, dtype={k: v for k, v in _DTYPES.items()}, low_memory=False)
