"""Research figures of Chapter 5 (white background, Thai font, one y-scale per panel).

Family colours are fixed by meaning, never by series order (validated all-pairs for CVD):
P = blue, S = orange, N = aqua; status quo = grey; N-FB = violet with line style by lambda.
Recruitment-only plans are solid, plans with transfers dashed.  Every figure exports its
plotted data to outputs/chapter5/plot_data/.
"""
from __future__ import annotations

from chapter4 import config as C4

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import FuncFormatter

from . import pipeline as PL
from .reporting import Registry, setup_style

COL = {"P": "#2a78d6", "S": "#eb6834", "N": "#1baf7a", "SQ": "#7a7a7a", "NFB": "#4a3aa7", "Pent": "#2a78d6", "B": "#b8337a"}
TH = {"P": "ประชากร (P)", "S": "บริการที่เกิดขึ้น (S)", "N": "บริการคาดหมายมาตรฐาน M5 (N-STD)"}
GRID = dict(axis="y", color="#e3e3e3", linewidth=0.6, zorder=0)
INK2 = "#52514e"


def _fam(pid):
    return "SQ" if pid.startswith("SQ") else ("NFB" if pid.startswith("NFB") else pid.split("-")[0])


def _style(pid):
    return dict(color=COL.get(_fam(pid), "#444"), lw=2, ls="--" if "RT" in pid.split("|")[0] else "-")


def _be_axis(ax, years, step=2):
    ys = [y for y in years if (y - years[0]) % step == 0]
    ax.set_xticks(ys)
    ax.set_xticklabels([str(y + 543) for y in ys])


def _end_label(ax, x, y, text, color):
    ax.annotate(text, (x, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)


def framework(Rg):
    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.set_xlim(0, 100); ax.set_ylim(0, 67); ax.axis("off")

    def box(x, y, w, h, t, fc="#f4f6f8", ec="#44515c"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6", fc=fc, ec=ec, lw=1.1))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=9, wrap=True)

    def arr(a, b, style="-", color="#44515c", text=None):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, color=color, lw=1.3, ls=style))
        if text:
            ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 1.5, text, fontsize=7.5, color=color, ha="center")
    box(2, 46, 22, 10, "ประชากรและสุขภาพ\nHamilton–Perry 77 จังหวัด\nทะเบียนสิทธิ ความชุกที่บันทึก")
    box(2, 26, 22, 10, "การเข้า–ออก\nการลาออก เกษียณ ฯลฯ (hazard)\nการกลับเข้า; ไม่รวมการรับใหม่")
    box(2, 6, 22, 10, "เป้าหมายและกฎปฏิบัติ\n1:1,000 (ตัวอย่าง) ขั้นต่ำ 1 คน\nเพดาน 10% โยกย้าย ≤2%")
    box(34, 46, 26, 10, "ตัวหารสามแบบ\nP ประชากร · S บริการที่เกิดขึ้น\nN-STD M5 ตรึงทรัพยากรอ้างอิง", fc="#eef4fb")
    box(34, 20, 26, 16, "จัดสรรแบบมีข้อจำกัด (MILP)\nรับใหม่ x และโยกย้าย z เป็นจำนวนเต็ม\nlexicographic: ขาดแคลน → กระจาย → โยกย้าย\nstock–flow เดียวกับการจำลอง", fc="#fff7ef")
    box(70, 46, 27, 10, "บริการที่ตอบสนองทรัพยากร\nM5 (ค่าบวก) ยึดกับฐานบริการ\nλ = 0, 0.5, 1", fc="#f2f0fb")
    box(70, 20, 27, 16, "ประเมินร่วมทุกแผน\nทุกตัวหาร: ความเพียงพอ ความขาดแคลน\nGini/Theil ภาระงาน\nการเปลี่ยนปลายทาง ความไม่แน่นอน", fc="#eefaf4")
    box(70, 2, 27, 10, "ตารางรายปี 2569–2583\nรายจังหวัด + เส้นทางโยกย้าย\n+ กฎปรับแผนรายปี")
    arr((24, 51), (34, 51)); arr((24, 31), (34, 28)); arr((24, 11), (34, 24))
    arr((47, 46), (47, 36)); arr((60, 28), (70, 28)); arr((60, 32), (70, 49))
    arr((83.5, 46), (83.5, 36))
    arr((83.5, 20), (83.5, 12))
    ax.add_patch(FancyArrowPatch((83.5, 57.2), (47, 57.2), arrowstyle="-|>", mutation_scale=12, color="#4a3aa7", lw=1.3,
                                 ls="--", connectionstyle="arc3,rad=0.25"))
    ax.text(65, 65.2, "N-FB: บริการปีก่อน → ตัวหารปีถัดไป (ล่าช้า 1 ปี; การทดลองเท่านั้น)", fontsize=8, color="#4a3aa7", ha="center")
    fig.tight_layout()
    Rg.figure("F51_MODEL_FRAMEWORK", fig, None, "โครงสร้างแบบจำลอง: ประชากรและสุขภาพ การเข้า–ออก ตัวหารสามแบบ การจัดสรรภายใต้ข้อจำกัด และการประเมินร่วม (เส้นประ = การป้อนกลับที่ใช้เฉพาะการทดลอง N-FB)", main=True)


def make_all(S):
    font = setup_style()
    plt.rcParams["font.family"] = [font, "DejaVu Sans"]     # fallback for λ, ↔, −
    Rg = Registry(S, "5_5")
    ctx = PL.context(json.dumps(S.overrides, sort_keys=True), "{}")
    res = {r["job_id"]: r for r in PL.load_plan_results(S)}
    D = S.dirs()
    tab = lambda n, f="tables": pd.read_csv(D[f] / f"{n}.csv", encoding="utf-8-sig")
    years = S.years
    yrs0 = [S.base_year] + years
    framework(Rg)
    # ---------------- F52 population and supply
    pop = pd.read_parquet(D["tables"] / "T5_POP_PROJECTION.parquet")
    pop = pop[pop.prov_code.isin(ctx.provs)]
    fig, ax = plt.subplots(2, 2, figsize=(11.5, 7.2))
    rows = []
    for sc, ls in [("low", ":"), ("central", "-"), ("high", "--")]:
        z = pop[pop.scenario == sc].groupby("year")[["population", "n3_60+"]].sum()
        ax[0, 0].plot(z.index, z.population / 1e6, color=COL["P"], ls=ls, lw=2 if sc == "central" else 1.2,
                      label={"low": "ย้ายถิ่นต่ำ", "central": "กลาง", "high": "ย้ายถิ่นสูง"}[sc])
        rows.append(z.assign(scenario=sc).reset_index())
        if sc == "central":
            ax[0, 1].plot(z.index, 100 * z["n3_60+"] / z.population, color=COL["P"], lw=2, label="สัดส่วน 60+ (76 จังหวัด)")
    sup = pd.read_csv(D["validation"] / "T5_M5_SUPPORT_BY_YEAR.csv", encoding="utf-8-sig")
    ax[0, 1].plot(sup.year, 100 * sup.share_age60_out, color="#9a9a9a", lw=1.5, ls="--", label="% จังหวัดที่ 60+ เกินช่วงข้อมูล M5")
    ax[0, 0].set_title("ก. ประชากรทะเบียนราษฎร 76 จังหวัด (ล้านคน)")
    ax[0, 1].set_title("ข. โครงสร้างอายุ และการเกินช่วงข้อมูลของ M5 (ร้อยละ)")
    ax[0, 0].legend(frameon=False); ax[0, 1].legend(frameon=False)
    L = res["P-R"]["ledger"].groupby("year_ce")[["new_appointments_accepted_starts", "expected_departures_total",
                                                 "expected_reentries", "expected_closing_stock", "target_own"]].sum()
    ax[1, 0].plot(L.index, L.new_appointments_accepted_starts, color="#222", lw=2, label="รับใหม่ (ชุดจัดสรร)")
    ax[1, 0].plot(L.index, L.expected_departures_total, color="#b03a2e", lw=2, label="ออกที่คาด")
    ax[1, 0].plot(L.index, L.expected_reentries, color="#8a6d1f", lw=1.5, label="กลับเข้าที่คาด")
    ax[1, 0].set_title("ค. การไหลเข้า–ออกระดับประเทศ แผน P-R (คนต่อปี)"); ax[1, 0].legend(frameon=False)
    ax[1, 0].set_ylim(0, None)
    ax[1, 1].plot([S.base_year] + list(L.index), [ctx.H0.sum()] + list(L.expected_closing_stock), color="#222", lw=2, label="จำนวนคงอยู่ที่คาด")
    ax[1, 1].plot(L.index, L.target_own, color="#8a8a8a", lw=1.5, ls="--", label="เป้าหมาย 1:1,000 (ตัวอย่าง)")
    ax[1, 1].set_title("ง. แพทย์ที่คาดเทียบเป้าหมายรวม (คน)"); ax[1, 1].legend(frameon=False)
    ax[1, 1].set_ylim(0, None)
    for a_ in ax.ravel():
        a_.grid(**GRID); _be_axis(a_, yrs0, 3)
    for a_ in (ax[1, 0], ax[1, 1]):
        a_.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    fig.tight_layout()
    Rg.figure("F52_POPULATION_AND_SUPPLY", fig, pd.concat(rows).merge(L.reset_index().rename(columns={"year_ce": "year"}), on="year", how="left"),
              "ประชากรฉาย โครงสร้างอายุ การเข้า–ออกของแพทย์ และจำนวนคงอยู่เทียบเป้าหมาย (แผน P-R; ค่าคาดหมาย)", main=True)
    # ---------------- F53 annual allocations
    fig, ax = plt.subplots(1, 2, figsize=(12, 9.5), gridspec_kw=dict(width_ratios=[1.1, 1]))
    x0 = pd.DataFrame({f: res[f"{f}-R"]["x"][0] for f in ["P", "S", "N"]}, index=[ctx.names[p] for p in ctx.provs])
    x0 = x0.sort_values("P")
    yy = np.arange(len(x0))
    for f, mk in [("P", "o"), ("S", "s"), ("N", "^")]:
        ax[0].scatter(x0[f], yy, s=22, color=COL[f], marker=mk, label=TH[f], zorder=3)
    ax[0].set_yticks(yy); ax[0].set_yticklabels(x0.index, fontsize=6.5)
    ax[0].set_title("ก. แพทย์รับใหม่ปี 2569 รายจังหวัด (คน)"); ax[0].legend(frameon=False, loc="lower right")
    ax[0].grid(axis="x", color="#e3e3e3", lw=0.6)
    cum = pd.DataFrame({f: res[f"{f}-R"]["x"].sum(0) for f in ["P", "S", "N"]}, index=[ctx.names[p] for p in ctx.provs])
    cum["S−P"] = cum.S - cum.P; cum["N−P"] = cum.N - cum.P
    top = cum.reindex(cum[["S−P", "N−P"]].abs().max(1).sort_values(ascending=False).index[:16])
    top = top.iloc[::-1]
    yy = np.arange(len(top))
    ax[1].barh(yy + 0.2, top["S−P"], height=0.38, color=COL["S"], label="S − P")
    ax[1].barh(yy - 0.2, top["N−P"], height=0.38, color=COL["N"], label="N-STD − P")
    for i, (a_, b_) in enumerate(zip(top["S−P"], top["N−P"])):
        ax[1].text(a_, i + 0.2, f" {a_:+,}", va="center", ha="left" if a_ >= 0 else "right", fontsize=7, color=INK2)
        ax[1].text(b_, i - 0.2, f" {b_:+,}", va="center", ha="left" if b_ >= 0 else "right", fontsize=7, color=INK2)
    ax[1].axvline(0, color="#888", lw=0.8)
    ax[1].set_yticks(yy); ax[1].set_yticklabels(top.index, fontsize=8)
    ax[1].set_title("ข. ความต่างของการรับใหม่สะสม 15 ปี เทียบแผน P (คน)"); ax[1].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    Rg.figure("F53_ANNUAL_ALLOCATIONS", fig, cum.reset_index().rename(columns={"index": "province"}).merge(
        x0.reset_index().rename(columns={"index": "province", "P": "x2026_P", "S": "x2026_S", "N": "x2026_N"}), on="province"),
              "การรับใหม่ปีแรกรายจังหวัด และความต่างของการรับใหม่สะสม 15 ปีเมื่อเปลี่ยนหลักคิด (แผน R, เป้าหมายรวมร่วม)", main=True)
    # ---------------- F54 adequacy and inequality
    TR = pd.read_parquet(D["tables"] / "T5_TRAJECTORY_METRICS.parquet")
    fig, ax = plt.subplots(2, 3, figsize=(13.5, 7.8))
    pl = ["SQ-C", "S-R", "S-RT", "N-R", "N-RT", "P-R", "P-RT"]       # P drawn last so ties stay visible
    rowsF = []
    for i, (m, t) in enumerate([("national_attainment", "ก. ความเพียงพอรวม (แพทย์/เป้าหมาย)"),
                                ("bottom_quartile_attainment", "ข. ความเพียงพอของ 19 จังหวัดต่ำสุด"),
                                ("gini", "ค. Gini ของความเพียงพอ (ถ่วงเป้าหมาย)")]):
        a_ = ax[0, i]
        for pid in pl:
            z = TR[(TR.plan_id == pid) & (TR.criterion == "P|common_total")]
            if not len(z):
                continue
            st = _style(pid)
            st["lw"] = 3.0 if pid.startswith("P-") else 1.7
            a_.plot(z.year_ce, z[m], **st, label=pid)
            rowsF.append(z.assign(panel=m))
        a_.set_title(t + "\nเกณฑ์ประเมินร่วม: ประชากร", fontsize=9.5)
        a_.grid(**GRID); _be_axis(a_, years, 3)
    ax[0, 0].legend(frameon=False, ncol=2, fontsize=7.5)
    gaps = []
    for pid, off, lab in [("P-R", -0.2, "1:1,000"), ("P-R|ref0.5", 0.2, "0.5:1,000")]:
        Lg = res[pid]["ledger"].groupby("year_ce").apply(
            lambda g: pd.Series({"nat": max(g.target_own.sum() - g.expected_closing_stock.sum(), 0),
                                 "tot": (g.target_own - g.expected_closing_stock).clip(lower=0).sum()}), include_groups=False)
        Lg["sp"] = Lg.tot - Lg.nat
        gaps.append(Lg.assign(plan=pid))
        ax[1, 0].bar(Lg.index + off, Lg.nat, width=0.38, color="#8a8a8a" if off < 0 else "#c9c9c9",
                     label=f"ระดับประเทศ ({lab})")
        ax[1, 0].bar(Lg.index + off, Lg.sp, width=0.38, bottom=Lg.nat, color=COL["P"] if off < 0 else "#9cc3ee",
                     label=f"จากการกระจาย ({lab})")
    ax[1, 0].set_title("ง. ขาดแคลนระดับประเทศ vs จากการกระจาย (คน)\nแผน P-R ที่เป้า 1:1,000 และ 0.5:1,000", fontsize=9.5)
    ax[1, 0].legend(frameon=True, framealpha=0.9, edgecolor="none", fontsize=7, loc="upper right"); ax[1, 0].grid(**GRID); _be_axis(ax[1, 0], years, 3)
    for pid in ["P-R", "P-RT", "P-R|net", "P-RT|net"]:
        z = TR[(TR.plan_id == pid) & (TR.criterion == "P|common_total")]
        if len(z):
            st = _style(pid)
            if "net" in pid:
                st["color"] = "#1b3f73"
            ax[1, 1].plot(z.year_ce, z.bottom_quartile_attainment, **st, label=pid)
    ax[1, 1].set_title("จ. เพดานรับเข้ารวม vs เติบโตสุทธิ: 19 จังหวัดต่ำสุด", fontsize=9.5)
    ax[1, 1].legend(frameon=False, fontsize=7.5); ax[1, 1].grid(**GRID); _be_axis(ax[1, 1], years, 3)
    inv = tab("T5_INVERSE_FEASIBILITY")
    inv = inv[~inv.ramp_limited]
    lab = [f"{'รับเข้ารวม' if r.cap_mode == 'gross_arrivals' else 'เติบโตสุทธิ'}\n{'ทุกจังหวัด' if r.criterion == 'province' else 'รวมประเทศ'}"
           for r in inv.itertuples()]
    ax[1, 2].barh(range(len(inv)), inv.max_attainment_2040, color=["#8a8a8a" if c == "gross_arrivals" else "#1b3f73" for c in inv.cap_mode])
    for i, v in enumerate(inv.max_attainment_2040):
        ax[1, 2].text(v, i, f" {v:.2f}", va="center", fontsize=8, color=INK2)
    ax[1, 2].axvline(1, color="#b03a2e", lw=1, ls="--")
    ax[1, 2].set_yticks(range(len(inv))); ax[1, 2].set_yticklabels(lab, fontsize=8)
    ax[1, 2].set_title("ฉ. ความเพียงพอสูงสุดที่ถึงได้ใน 2583\nเมื่อไม่จำกัดจำนวนผลิต (เส้นแดง = เป้าหมาย)", fontsize=9.5)
    ax[1, 0].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    fig.tight_layout()
    Rg.figure("F54_ADEQUACY_AND_INEQUALITY", fig, pd.concat(rowsF), "ความเพียงพอรวม ความเพียงพอของจังหวัดกลุ่มล่าง และความเหลื่อมล้ำ พ.ศ. 2569–2583 (เส้นทึบ = รับใหม่อย่างเดียว; เส้นประ = รับใหม่และโยกย้าย) พร้อมการแยกขาดแคลนระดับประเทศกับจากการกระจาย และขีดจำกัดจากเพดาน", main=True)
    # ---------------- F55 feedback
    fig, ax = plt.subplots(2, 2, figsize=(11.5, 7.4))
    ix = ctx.idx.groupby("year")[["D_N", "D_P"]].sum()
    ax[0, 0].plot(ix.index, ix.D_N / 1e6, color=COL["N"], lw=2, label="N-STD (หน่วยเทียบเท่า)")
    ax[0, 0].plot(ix.index, ix.D_P / 1e6, color=COL["P"], lw=1.3, ls=":", label="ประชากร")
    ax[0, 0].set_title("ก. ตัวหารอ้างอิงคงที่ N-STD (ล้านหน่วย)\nไม่ขึ้นกับจำนวนแพทย์"); ax[0, 0].legend(frameon=False)
    resp = tab("T5_RESPONSE_EVALUATION")
    for lam, ls in [(0.5, "--"), (1.0, "-")]:
        for pid in ["N-R", "NFB1-R"]:
            z = resp[(resp.plan_id == pid) & (resp.lam == lam)]
            if len(z):
                ax[0, 1].plot(z.year_ce, z.responsive_minutes / 1e6 / 60, ls=ls, lw=1.8,
                              color=COL["N"] if pid == "N-R" else COL["NFB"], label=f"{pid}, λ={lam:g}")
    ax[0, 1].set_title("ข. บริการที่ตอบสนองทรัพยากร (ล้านชั่วโมงถ่วง)\nกลไกเดียวกันทุกแผน"); ax[0, 1].legend(frameon=False, fontsize=7.5)
    fbc = tab("T5_FEEDBACK_CONVERGENCE")
    for pid, ls in [("N-R", "-"), ("NFB0.5-R", "--"), ("NFB1-R", ":"), ("NFB1-R|B", "-.")]:
        z = fbc[fbc.plan_id == pid]
        if len(z):
            ax[1, 0].plot(z.year_ce, z.gini_vs_nstd, ls=ls, lw=2, color=COL["N"] if pid == "N-R" else COL["NFB"], label=pid)
    ax[1, 0].set_title("ค. Gini เทียบตัวหารอ้างอิง N-STD (ตัวหารร่วม)"); ax[1, 0].legend(frameon=False, fontsize=7.5)
    fbl = tab("T5_FEEDBACK_LOG")
    for pid, c in [("NFB1-R", COL["NFB"]), ("NFB0.5-R", "#9085e9"), ("NFB1-R|B", "#222")]:
        z = fbl[fbl.plan_id == pid]
        if len(z):
            ax[1, 1].plot(z.year, z.gain_B_mean, color=c, lw=2, label=f"{pid} เฉลี่ย")
            ax[1, 1].plot(z.year, z.gain_B_max, color=c, lw=1, ls="--", label=f"{pid} สูงสุด")
    ax[1, 1].axhline(1, color="#b03a2e", lw=1)
    ax[1, 1].set_title("ง. เป้าหมายเพิ่มขึ้นกี่คนต่อแพทย์ 1 คนที่เพิ่ม\n(เส้นแดง = 1: เป้าหมายวิ่งหนี)"); ax[1, 1].legend(frameon=False, fontsize=7)
    for a_ in ax.ravel():
        a_.grid(**GRID)
        _be_axis(a_, years if a_ is not ax[0, 0] else yrs0, 3)
    fig.tight_layout()
    Rg.figure("F55_FEEDBACK", fig, fbc, "การทดลองป้อนกลับ: ตัวหารอ้างอิงคงที่เทียบบริการที่ตอบสนองทรัพยากร (แยกแผงและหน่วย) ความเหลื่อมล้ำเทียบตัวหารร่วม และกำไรป้อนกลับต่อเป้าหมาย", main=True)
    # ---------------- F56 plan disagreement
    sw = tab("T5_SWITCHES")
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for (a_, b_), c in [(("P-R", "S-R"), COL["S"]), (("P-R", "N-R"), COL["N"]), (("S-R", "N-R"), "#4a3aa7"),
                        (("P-R", "SQ-C"), COL["SQ"])]:
        z = sw[(sw.plan_a == a_) & (sw.plan_b == b_)]
        ax[0].plot(z.year_ce, z.switched_pct, color=c, lw=2)
        _end_label(ax[0], z.year_ce.iloc[-1], z.switched_pct.iloc[-1], f"{a_} ↔ {b_}", c)
    ax[0].axhline(S.cfg["evaluation"]["switch_threshold_pct"], color="#b03a2e", lw=1, ls="--")
    pdt = tab("T5_PRACTICAL_DIFFERENCES")
    noise = pdt[pdt.near_optimal_alternative.astype(bool)].mean_annual_switched_pct.max() if "near_optimal_alternative" in pdt else float("nan")
    if noise == noise:
        ax[0].axhline(noise, color="#52514e", lw=1, ls=":")
    ax[0].set_title("ก. ร้อยละของการรับใหม่ที่ต้องเปลี่ยนปลายทาง\n(เส้นประแดง = เกณฑ์ 5%; เส้นจุดเทา = ระดับความไม่เป็นเอกลักษณ์ของคำตอบ)", fontsize=10)
    ax[0].grid(**GRID); _be_axis(ax[0], years, 3); ax[0].set_xlim(years[0] - .5, years[-1] + 3.5)
    prd = tab("T5_PROVINCE_DIFFERENCES")
    z = prd[(prd.plan_a == "P-R") & prd.plan_b.isin(["S-R", "N-R"])]
    piv = z.pivot(index="province", columns="plan_b", values="diff")
    piv = piv.reindex(piv.abs().max(1).sort_values(ascending=False).index[:12])
    im = ax[1].imshow(piv.to_numpy(), cmap="RdBu", aspect="auto", vmin=-np.abs(piv.to_numpy()).max(), vmax=np.abs(piv.to_numpy()).max())
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            ax[1].text(j, i, f"{piv.iloc[i, j]:+,}", ha="center", va="center", fontsize=8)
    ax[1].set_xticks(range(piv.shape[1])); ax[1].set_xticklabels([f"{c} − P-R" for c in piv.columns])
    ax[1].set_yticks(range(piv.shape[0])); ax[1].set_yticklabels(piv.index, fontsize=8)
    ax[1].set_title("ข. จังหวัดที่การรับใหม่สะสม 15 ปีต่างมากที่สุด (คน)")
    fig.tight_layout()
    Rg.figure("F56_PLAN_DISAGREEMENT", fig, sw, "จำนวนและสัดส่วนแพทย์ที่ต้องเปลี่ยนจังหวัดปลายทางเมื่อเปลี่ยนหลักคิด และจังหวัดที่ได้รับผลต่างมากที่สุด", main=True)

    # ---------------- F56 illustrative health gain (scenario)
    hg = tab("T5_HEALTH_GAIN_SUMMARY")
    hg = hg[hg.measure == hg.measure.iloc[0]]
    order = [p for p in ["SQ-C", "S-R", "N-R", "P-R", "B-R", "P-R|net", "B-R|net"] if p in set(hg.plan_id)]
    piv = hg.pivot(index="plan_id", columns="elasticity_label", values="averted_total").reindex(order)
    pct = hg.pivot(index="plan_id", columns="elasticity_label", values="averted_vs_PR_pct").reindex(order)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw=dict(width_ratios=[1.2, 1]))
    yy = np.arange(len(order))[::-1]
    for y_, pid in zip(yy, order):
        c = COL.get(_fam(pid), "#444")
        ax[0].plot([piv.loc[pid, "low"] / 1e6, piv.loc[pid, "high"] / 1e6], [y_, y_], color=c, lw=2, solid_capstyle="round")
        ax[0].plot(piv.loc[pid, "central"] / 1e6, y_, "o", color=c, ms=7, mec="white", mew=1.2)
        ax[1].barh(y_, pct.loc[pid, "central"], color=c, height=0.6)
        ax[1].annotate(f"{pct.loc[pid, 'central']:+.1f}%", (pct.loc[pid, "central"], y_), xytext=(4 if pct.loc[pid, "central"] >= 0 else -4, 0),
                       textcoords="offset points", ha="left" if pct.loc[pid, "central"] >= 0 else "right", va="center", fontsize=8, color=INK2)
    for a in ax:
        a.set_yticks(yy)
        a.set_yticklabels(order, fontsize=8.5)
        a.grid(axis="x", color="#e3e3e3", linewidth=0.6, zorder=0)
        a.set_axisbelow(True)
    ax[0].set_xlabel("ล้าน YLL ที่ป้องกันได้ สะสม 2569–2583 (จุด = ความยืดหยุ่นกลาง; เส้น = ต่ำ–สูง)")
    ax[0].set_title("ก. ภาระที่ระบบบริการช่วยได้ซึ่งป้องกันได้", fontsize=10, loc="left")
    ax[1].axvline(0, color="#8a8a8a", lw=0.9)
    ax[1].set_xlabel("ต่างจาก P-R (%) ที่ความยืดหยุ่นกลาง")
    ax[1].set_title("ข. เทียบแผนจัดสรรตามประชากร", fontsize=10, loc="left")
    lim = np.nanmax(np.abs(pct["central"].to_numpy())) * 1.35
    ax[1].set_xlim(-lim, lim)
    fig.tight_layout()
    Rg.figure("F56_HEALTH_GAIN", fig, hg, "ฉากทัศน์สมมติ: YLL ที่ระบบบริการช่วยได้ซึ่งป้องกันได้ของแต่ละแผน ภายใต้ความยืดหยุ่นที่สมมติ (ไม่ใช่ผลที่ประมาณจากข้อมูล)", main=True)
    # ---------------- appendix: population backtest, uncertainty, sensitivity
    det = pd.read_csv(D["validation"] / "T5_POP_BACKTEST_PROVINCES.csv", encoding="utf-8-sig")
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for m, c in [("hamilton_perry_national_control", COL["P"]), ("no_change_2019", "#9a9a9a")]:
        z = det[det.method == m].sort_values("ape_pct")
        ax[0].plot(np.arange(len(z)), z.ape_pct, color=c, lw=2,
                   label={"hamilton_perry_national_control": "Hamilton–Perry + ควบคุมระดับประเทศ", "no_change_2019": "ไม่เปลี่ยนจาก 2562"}[m])
    ax[0].set_title("ก. ความคลาดเคลื่อนสัมบูรณ์ร้อยละ (ฉาย 2562→2568) เรียงจังหวัด"); ax[0].legend(frameon=False)
    ax[0].grid(**GRID); ax[0].set_xlabel("จังหวัด (เรียงตามความคลาดเคลื่อน)")
    z = det[det.method == "hamilton_perry_national_control"]
    ax[1].scatter(100 * z.share60_observed, 100 * z.share60_predicted, s=14, color=COL["P"])
    lim = [100 * z.share60_observed.min() - 1, 100 * z.share60_observed.max() + 1]
    ax[1].plot(lim, lim, color="#888", lw=0.8)
    ax[1].set_xlabel("สัดส่วน 60+ จริง 2568 (%)"); ax[1].set_ylabel("ฉาย (%)"); ax[1].set_title("ข. โครงสร้างอายุ: ฉายเทียบจริง")
    fig.tight_layout()
    Rg.figure("F5A_POP_BACKTEST", fig, det, "ตรวจย้อนหลังการฉายประชากรรายจังหวัด 2562→2568")
    unc = D["tables"] / "T5_UNCERTAINTY_SUMMARY.csv"
    if unc.exists():
        fx = pd.read_parquet(D["plans"] / "chapter5_simulation_paths_fixed.parquet")
        ad_p = D["plans"] / "chapter5_simulation_paths_adaptive.parquet"
        ad = pd.read_parquet(ad_p) if ad_p.exists() else pd.DataFrame()
        fig, ax = plt.subplots(1, 3, figsize=(12.5, 4.2), sharey=False)
        for i, f in enumerate(["P", "S", "N"]):
            data, labs = [], []
            z = fx[(fx.plan_id == f"{f}-R") & (fx.criterion == f)]
            data.append(z.bottom_quartile_2040.to_numpy()); labs.append("แผนตายตัว")
            if len(ad):
                for mode, lb in [("adaptive_replanning", "ปรับแผนรายปี"), ("perfect_foresight_bound", "รู้อนาคต (อ้างอิง)")]:
                    q = ad[(ad.plan_id == f"{f}-R") & (ad["mode"] == mode) & (ad.status == "solved")]
                    if len(q):
                        data.append(q.bottom_quartile_2040.to_numpy()); labs.append(lb)
            bp = ax[i].boxplot(data, widths=0.5, patch_artist=True, showfliers=False)
            for b in bp["boxes"]:
                b.set(facecolor=COL[f], alpha=0.35, edgecolor=COL[f])
            ax[i].set_xticks(range(1, len(labs) + 1)); ax[i].set_xticklabels(labs, fontsize=8)
            ax[i].set_title(f"{TH[f]}\n19 จังหวัดต่ำสุด 2583 (เกณฑ์ของตนเอง)", fontsize=9)
            ax[i].grid(**GRID)
        fig.tight_layout()
        Rg.figure("F5A_UNCERTAINTY", fig, fx[fx.criterion.isin(["P", "S", "N"])].groupby(["plan_id", "criterion"]).bottom_quartile_2040.describe().reset_index(),
                  "การกระจายของความเพียงพอของจังหวัดกลุ่มล่างภายใต้ความไม่แน่นอน: แผนตายตัว การปรับแผนรายปี และขอบเขตแบบรู้อนาคต (เส้นทางจับคู่)")
    sens = tab("T5_SENSITIVITY_SUMMARY")
    sens = sens[sens.bottom_quartile_own_2040.notna()].copy()
    base = {p: res[p] for p in ["P-R", "S-R", "N-R"]}
    from . import evaluation as EV
    fig, ax = plt.subplots(figsize=(9.5, max(4, 0.22 * len(sens))))
    sens = sens.sort_values(["base_plan", "bottom_quartile_own_2040"])
    yy = np.arange(len(sens))
    ax.scatter(sens.bottom_quartile_own_2040, yy, s=18, color=[COL.get(_fam(b), "#444") for b in sens.base_plan], zorder=3)
    for f in ["P", "S", "N"]:
        L_ = res[f"{f}-R"]["ledger"]; L_ = L_[L_.year_ce == years[-1]]
        a40 = (L_.expected_closing_stock / L_.target_own).to_numpy(); o = np.argsort(a40)[:19]
        v = L_.expected_closing_stock.to_numpy()[o].sum() / L_.target_own.to_numpy()[o].sum()
        ax.axvline(v, color=COL[f], lw=0.8, ls="--")
    ax.set_yticks(yy); ax.set_yticklabels(sens.plan_id, fontsize=6.5)
    ax.set_title("ความเพียงพอของ 19 จังหวัดต่ำสุด 2583 ตามเกณฑ์ของแต่ละแผน (เส้นประ = แผนฐาน)", fontsize=9.5)
    ax.grid(axis="x", color="#e3e3e3", lw=0.6)
    fig.tight_layout()
    Rg.figure("F5A_SENSITIVITY", fig, sens, "ผลการวิเคราะห์ความไว: ความเพียงพอของจังหวัดกลุ่มล่างปี 2583")
    # map of 2040 attainment (population criterion) for the three R plans
    try:
        import geopandas as gpd
        g = gpd.read_file(C4.geo_path()).set_index("prov_id")
        g = g.loc[ctx.provs]
        TP = PL.eval_targets(ctx, "common_total")["P"][-1]
        fig, ax = plt.subplots(1, 3, figsize=(12, 6.2))
        vals = {f: res[f"{f}-R"]["H"][-1] / TP for f in ["P", "S", "N"]}
        vmin, vmax = min(v.min() for v in vals.values()), max(v.max() for v in vals.values())
        for i, f in enumerate(["P", "S", "N"]):
            g.assign(v=vals[f]).plot(column="v", ax=ax[i], cmap="Blues", vmin=vmin, vmax=vmax, edgecolor="#ffffff", linewidth=0.3)
            ax[i].set_axis_off(); ax[i].set_title(f"{f}-R", fontsize=10)
        sm = plt.cm.ScalarMappable(cmap="Blues", norm=plt.Normalize(vmin, vmax))
        fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, label="แพทย์ 2583 / เป้าหมายประชากร 1:1,000")
        Rg.figure("F5A_MAP_2040", fig, pd.DataFrame({"prov_code": ctx.provs, **{f"att_{f}": v for f, v in vals.items()}}),
                  "ความเพียงพอปี 2583 เทียบเกณฑ์ประชากร ของแผน P-R, S-R และ N-R (ค่าคาดหมาย)")
    except Exception as e:  # the map is an appendix convenience; its absence is reported, not hidden
        print("map skipped:", e)
    return Rg.finalize()
