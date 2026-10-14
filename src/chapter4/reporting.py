"""Figures, tables, the claim registry and the asset registry.

A `Section` collects everything a notebook produces:

    S = Section("4_3")
    S.table("T43_INEQUALITY", df, caption_th="...")               # CSV (UTF-8 BOM) + workbook sheet
    S.figure("F43_GINI", fig, data=df, caption_th="...")          # PNG/SVG/PDF + plotted data CSV
    S.claim("c43_gini_phys_2025", value, fmt="{:.3f}", unit="", table="T43_INEQUALITY",
            row="cadre=แพทย์,year=2025", variable="gini_weighted", scope=..., years=..., sample=...)
    S.finalize()                                                  # workbook, registries, manifest

Report prose lives in reports/templates/ and pulls every number from the claim registry
by id, so a changed result cannot leave a stale number in the text.
"""
from __future__ import annotations

import json
import platform
import re
import subprocess
import time
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C

ENC = C.CFG["figures"]["csv_encoding"]


# ----------------------------------------------------------------------------- style

def setup_style() -> str:
    """Register the bundled Prompt font and set white-background research rcParams."""
    if C.FONT_DIR.exists():
        for f in sorted(C.FONT_DIR.rglob("*.ttf")):
            matplotlib.font_manager.fontManager.addfont(str(f))
    avail = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
    font = next((f for f in C.CFG["figures"]["font_candidates"] if f in avail), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": [font], "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 9.5,
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 8.5,
        "axes.edgecolor": "#444444", "axes.linewidth": 0.8, "axes.spines.top": False,
        "axes.spines.right": False, "axes.facecolor": "white", "figure.facecolor": "white",
        "savefig.facecolor": "white", "savefig.bbox": "tight", "pdf.fonttype": 42,
        "svg.fonttype": "none", "axes.unicode_minus": False, "axes.grid": False})
    return font


CADRE_COLOR = C.CFG["figures"]["cadre_color"]
SECTOR_COLOR = C.CFG["figures"]["sector_color"]
GRID_KW = dict(axis="y", color="#dcdcdc", linewidth=0.6, zorder=0)
REFLINE_KW = dict(color="#8a8a8a", linewidth=0.9, linestyle=(0, (4, 3)), zorder=1)


def be_ticks(ax, years, step=2):
    ys = [y for y in years if (y - years[0]) % step == 0]
    ax.set_xticks(ys)
    ax.set_xticklabels([str(C.be(y)) for y in ys])


# ----------------------------------------------------------------------------- formatting

def fmt(value, spec: str) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "ไม่มีข้อมูล"
    if spec == "be":
        return str(C.be(value))
    if spec == "int":
        return f"{round(float(value)):,}"
    return spec.format(value)


# ----------------------------------------------------------------------------- section registry

class Section:
    def __init__(self, section: str, scenario: C.Scenario | None = None):
        self.section = section
        self.scenario = scenario
        self.dirs = scenario.dirs(section) if scenario else C.section_dirs(section)
        self.tables: dict[str, pd.DataFrame] = {}
        self.assets: list[dict] = []
        self.claims: list[dict] = []
        self.started = time.time()
        # stale outputs from an earlier run must not survive: clear this section's generated files
        for sub in ("tables", "figures", "figure_data"):
            for f in self.dirs[sub].glob("*"):
                if f.is_file():
                    f.unlink()

    # -- tables
    def table(self, asset_id: str, df: pd.DataFrame, caption_th: str = "", main: bool = False,
              note: str = "") -> pd.DataFrame:
        p = self.dirs["tables"] / f"{asset_id}.csv"
        df.to_csv(p, index=False, encoding=ENC)
        self.tables[asset_id] = df
        self.assets.append(dict(asset_id=asset_id, kind="table", file=str(p.relative_to(C.ROOT)),
                                caption_th=caption_th, main_text=main, rows=len(df), note=note,
                                section=self.section, status="generated"))
        return df

    # -- figures
    def figure(self, asset_id: str, fig, data: pd.DataFrame | None = None, caption_th: str = "",
               main: bool = False, note: str = ""):
        stem = self.dirs["figures"] / asset_id
        for ext in C.CFG["figures"]["formats"]:
            fig.savefig(f"{stem}.{ext}", dpi=C.CFG["figures"]["dpi"])
        dfile = ""
        if data is not None:
            dp = self.dirs["figure_data"] / f"{asset_id}_data.csv"
            data.to_csv(dp, index=False, encoding=ENC)
            dfile = str(dp.relative_to(C.ROOT))
        self.assets.append(dict(asset_id=asset_id, kind="figure", file=str(Path(f"{stem}.png").relative_to(C.ROOT)),
                                data_file=dfile, caption_th=caption_th, main_text=main, note=note,
                                section=self.section, status="generated"))

    # -- claims
    def claim(self, claim_id: str, value, fmt_spec: str = "{:,.2f}", unit: str = "", table: str = "",
              row: str = "", variable: str = "", scope: str = "", years: str = "", sample: str = "",
              status: str = "computed", note: str = ""):
        if callable(value) or not isinstance(value, (int, float, np.integer, np.floating, bool, np.bool_)):
            raise TypeError(f"claim {claim_id}: value must be a number, got {type(value)}")
        v = float(value)
        self.claims.append(dict(claim_id=claim_id, section=self.section, value=v,
                                display=fmt(v, fmt_spec),
                                fmt=fmt_spec, unit=unit, table=table, row_keys=row, variable=variable,
                                scope=scope, years=years, sample=sample, status=status, note=note))
        return v

    def text_claim(self, claim_id: str, text: str, **kw):
        """A non-numeric result that the prose depends on (a list of provinces, a verdict)."""
        self.claims.append(dict(claim_id=claim_id, section=self.section, value=text, display=text,
                                fmt="text", unit="", table=kw.get("table", ""), row_keys=kw.get("row", ""),
                                variable=kw.get("variable", ""), scope=kw.get("scope", ""),
                                years=kw.get("years", ""), sample=kw.get("sample", ""),
                                status=kw.get("status", "computed"), note=kw.get("note", "")))

    # -- finalize
    def finalize(self, extra_manifest: dict | None = None):
        base = self.dirs["base"]
        wb = base / f"chapter{self.section}_tables.xlsx"
        with pd.ExcelWriter(wb, engine="openpyxl") as xw:
            idx = pd.DataFrame(self.assets)
            idx.to_excel(xw, sheet_name="index", index=False)
            for i, (name, df) in enumerate(self.tables.items()):
                sheet = re.sub(r"[\[\]\:\*\?\/\\]", "_", name)[:31]
                df.to_excel(xw, sheet_name=sheet, index=False)
        claims = pd.DataFrame(self.claims)
        dup = claims.claim_id[claims.claim_id.duplicated()].tolist() if len(claims) else []
        assert not dup, f"duplicate claim ids: {dup}"
        claims.to_csv(base / "claims.csv", index=False, encoding=ENC)
        pd.DataFrame(self.assets).to_csv(base / "assets.csv", index=False, encoding=ENC)
        manifest = run_manifest(self.section)
        manifest.update(seconds=round(time.time() - self.started, 1), n_tables=len(self.tables),
                        n_figures=sum(a["kind"] == "figure" for a in self.assets), n_claims=len(claims))
        if extra_manifest:
            manifest.update(extra_manifest)
        (base / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1, default=str))
        return manifest


def run_manifest(section: str) -> dict:
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=C.ROOT, capture_output=True,
                             text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "src", "notebooks", "config"],
                                    cwd=C.ROOT, capture_output=True, text=True).stdout.strip())
    except Exception:
        rev, dirty = "", None
    meta_p = C.PROCESSED / "_build_meta.json"
    import importlib.metadata as md
    vers = {p: md.version(p) for p in ["pandas", "numpy", "scipy", "statsmodels", "scikit-learn",
                                       "matplotlib", "openpyxl", "python-docx"]}
    return dict(section=section, run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                git_revision=rev, working_tree_has_uncommitted_pipeline_changes=dirty,
                code_hash=C.code_hash(), python=platform.python_version(), packages=vers,
                processed_data=json.loads(meta_p.read_text()) if meta_p.exists() else None,
                seed=C.SEED)


def load_claims() -> pd.DataFrame:
    frames = []
    for s in ["4_1", "4_2", "4_3", "4_4", "4_5", "4_6"]:
        p = C.OUTPUTS / f"chapter{s}" / "claims.csv"
        if p.exists():
            frames.append(pd.read_csv(p, encoding=ENC, dtype={"display": str}))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_assets() -> pd.DataFrame:
    frames = []
    for s in ["4_1", "4_2", "4_3", "4_4", "4_5", "4_6"]:
        p = C.OUTPUTS / f"chapter{s}" / "assets.csv"
        if p.exists():
            frames.append(pd.read_csv(p, encoding=ENC))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
