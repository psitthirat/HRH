"""Illustrative health-gain evaluation of finished plans: amenable burden averted (scenario).

The plans never see this.  For each plan's expected physicians H_pt, the amenable burden of
province p in year t is scaled from its counterfactual by a constant elasticity of physicians per
population:

    A_pt(H) = A_cf_pt * (H_pt / H_cf_pt) ** e,      averted_pt = A_cf_pt - A_pt(H)

A_cf_pt   amenable YLL (or DALY) at the province's 2022 BOD age-specific rates x projected age
          groups; amenable = the 32 causes of the GBD 2015 HAQ Index with their upper ages
H_cf_pt   2025 provincial physician density held (ctx.res.H_cf), the reference path already used
          for resource-responsive services
H_pt      the annual-average expected stock of the plan (mean of opening and closing)
e         an assumed elasticity from config/chapter5_health_gain.toml (low / central / high)

Because H/H_cf enters as a ratio, one more physician averts more where a province's stock is
small relative to its amenable burden.  The numbers are scenario arithmetic: a single BOD
cross-section cannot identify e, and the output must never be read as an estimated effect.
"""
from __future__ import annotations

import tomllib

import numpy as np
import pandas as pd

from chapter4 import config as C4
from chapter4.ingest import load as load4

CFG_PATH = C4.ROOT / "config" / "chapter5_health_gain.toml"
GCOLS = [f"g{i}" for i in range(1, 9)]


def load_cfg() -> dict:
    with open(CFG_PATH, "rb") as fh:
        return tomllib.load(fh)


def amenable_rates(measure: str, cfg: dict | None = None, bod: pd.DataFrame | None = None) -> pd.DataFrame:
    """Province x age group amenable burden per person-year (2022), honouring each cause's upper
    amenable age; a limit inside a source age group keeps the covered share of its single years.
    bod: a canonical-format bod_province_age table to use instead of the processed one."""
    cfg = cfg or load_cfg()
    max_age = cfg["amenable"]["max_age"]
    b = load4("bod_province_age") if bod is None else bod
    b = b[b.cause_code.isin(max_age)].copy()
    missing = set(max_age) - set(b.cause_code)
    assert not missing, f"amenable causes absent from BOD: {missing}"
    m = b.cause_code.map(max_age).to_numpy(float)
    lo = b.age_lo.to_numpy(float)
    hi = np.minimum(b.age_hi.to_numpy(float), 100.0)            # open 80+ group; never covered (all limits < 80)
    frac = np.clip((m - lo + 1) / (hi - lo + 1), 0, 1)
    b["amenable"] = b[measure].to_numpy(float) * frac
    out = b.groupby(["prov_code", "age_group"]).agg(amenable=("amenable", "sum"), mid_pop=("mid_pop", "first"))
    out["rate"] = out.amenable / out.mid_pop
    return out.reset_index()


def counterfactual_burden(ctx, measure: str, cfg=None, bod=None) -> np.ndarray:
    """[T, P] amenable burden at fixed 2022 rates on the projected age groups of the plan years."""
    r = amenable_rates(measure, cfg, bod).pivot(index="prov_code", columns="age_group", values="rate")
    r = r.reindex(ctx.provs).to_numpy(float)
    pop = ctx.pop.set_index(["year", "prov_code"])
    A = np.zeros((len(ctx.S.years), len(ctx.provs)))
    for t, y in enumerate(ctx.S.years):
        N = pop.loc[y].reindex(ctx.provs)[GCOLS].to_numpy(float)
        A[t] = (N * r).sum(1)
    return A


def evaluate(ctx, res: dict, plans: list[str], cfg=None, bod=None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (summary per plan x elasticity x measure, province detail for the central elasticity
    and primary measure, assumptions table)."""
    cfg = cfg or load_cfg()
    years = ctx.S.years
    Hcf = np.vstack([ctx.res.set_index(["year", "prov_code"]).loc[y].reindex(ctx.provs).H_cf.to_numpy(float)
                     for y in years])
    popm = np.vstack([ctx.idx[ctx.idx.year == y].set_index("prov_code").reindex(ctx.provs).population.to_numpy(float)
                      for y in years])
    low19 = np.argsort(ctx.H0 / popm[0])[:19]                    # 19 provinces with the lowest 2025 density
    prim = cfg["amenable"]["primary_measure"]
    rows, prov = [], []
    for meas in [prim] + [m for m in ["yll", "daly"] if m != prim]:
        A = counterfactual_burden(ctx, meas, cfg, bod)
        for lab, e in cfg["elasticity"]["values"].items():
            for pid in plans:
                r = res.get(pid)
                if r is None or r.get("H") is None:
                    continue
                H = np.asarray(r["H"], float)
                Havg = 0.5 * (np.vstack([ctx.H0[None], H[:-1]]) + H)
                Ap = A * (Havg / Hcf) ** e
                av = A - Ap
                extra = Havg - Hcf
                rows.append(dict(plan_id=pid, measure=meas, elasticity_label=lab, elasticity=e,
                                 amenable_cf_total=A.sum(), averted_total=av.sum(), averted_2040=av[-1].sum(),
                                 averted_pct_of_amenable=100 * av.sum() / A.sum(),
                                 physician_years_above_cf=extra.sum(),
                                 averted_per_1000_physician_years=1000 * av.sum() / extra.sum() if extra.sum() > 0 else np.nan,
                                 averted_low19_share=av[:, low19].sum() / av.sum(),
                                 provinces_with_loss=int((av.sum(0) < 0).sum())))
                if meas == prim and lab == cfg["elasticity"]["central"]:
                    prov.append(pd.DataFrame(dict(plan_id=pid, prov_code=ctx.provs,
                                                  province=[ctx.names[p] for p in ctx.provs],
                                                  amenable_cf_total=A.sum(0), averted_total=av.sum(0),
                                                  density_2025=1e5 * ctx.H0 / popm[0],
                                                  density_2040=1e5 * H[-1] / popm[-1])))
    SUM = pd.DataFrame(rows)
    base = SUM[SUM.plan_id == "P-R"].set_index(["measure", "elasticity_label"]).averted_total
    SUM["averted_minus_PR"] = SUM.averted_total - [base.get((m, l), np.nan) for m, l in zip(SUM.measure, SUM.elasticity_label)]
    SUM["averted_vs_PR_pct"] = 100 * SUM.averted_minus_PR / [base.get((m, l), np.nan) for m, l in zip(SUM.measure, SUM.elasticity_label)]
    ASM = pd.DataFrame([
        dict(item="ภาระที่ระบบบริการช่วยได้", value=f"32 สาเหตุของ HAQ Index (GBD 2015) จับคู่รหัส BOD Thailand {len(cfg['amenable']['max_age'])} รหัส ตามอายุสูงสุดของแต่ละสาเหตุ",
             status="ข้อตกลง", source="GBD 2015 HAQ Collaborators, Lancet 2017; Nolte & McKee"),
        dict(item="ตัววัดหลัก", value=f"{prim.upper()} (ความไว: {'DALY' if prim == 'yll' else 'YLL'})", status="ข้อตกลง", source="HAQ Index ใช้การตาย"),
        dict(item="ภาระอ้างอิง", value="อัตรารายอายุของจังหวัดปี 2565 × ประชากรฉายรายกลุ่มอายุ", status="ข้อสมมติ", source="BOD Thailand 2565"),
        dict(item="แพทย์อ้างอิง", value="ความหนาแน่นแพทย์ปี 2568 ของแต่ละจังหวัดคงที่", status="ข้อตกลง", source="บทที่ 5"),
        *[dict(item=f"ความยืดหยุ่น ({k})", value=f"{v:+.2f}", status="ตัวอย่าง (ไม่ใช่ค่าประมาณ)",
               source={"low": "ขนาดใกล้ Basu et al. 2019 (สหรัฐฯ ระดับเคาน์ตี แพทย์ปฐมภูมิ)",
                       "central": "ค่ากลางเชิงสมมติ",
                       "high": "ปลายล่างของ Anand & Bärnighausen 2004 (ข้ามประเทศ บุคลากรทุกวิชาชีพ)"}.get(k, ""))
          for k, v in cfg["elasticity"]["values"].items()],
        dict(item="ช่วงเวลาของผล", value="ผลเกิดในปีเดียวกับจำนวนแพทย์เฉลี่ยของปี (ไม่มีความล่าช้า)", status="ข้อสมมติ", source="—"),
    ])
    return SUM, pd.concat(prov, ignore_index=True), ASM
