"""Table/figure/claim registry for Chapter 5 (same conventions as chapter4.reporting).

    R = Registry(S, "5_1")
    R.table("T5_...", df, caption_th, main=True)       # CSV UTF-8 with BOM (+ parquet when large)
    R.figure("F5_...", fig, data, caption_th)          # PNG/SVG/PDF + plotted data CSV
    R.claim("c5_...", value, "{:.1f}", unit, table=..., note=...)
    R.finalize(extra)                                  # assets.csv, claims.csv, manifest per stage

Every number in the Thai report comes from the claim registry by id, so changing a knob
changes the text together with the tables and figures.
"""
from __future__ import annotations

import json
import platform
import subprocess
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from chapter4 import config as C4
from chapter4.reporting import fmt, setup_style  # noqa: F401  (re-exported for the notebooks)

ENC = "utf-8-sig"


class Registry:
    def __init__(self, S, stage: str):
        self.S = S
        self.stage = stage
        self.dirs = S.dirs()
        self.assets: list[dict] = []
        self.claims: list[dict] = []
        self.started = time.time()

    def rel(self, p: Path) -> str:
        try:
            return str(Path(p).relative_to(C4.ROOT))
        except ValueError:
            return str(p)

    def table(self, asset_id, df: pd.DataFrame, caption_th="", main=False, folder="tables", note="", parquet=False):
        p = self.dirs[folder] / f"{asset_id}.csv"
        df = df.copy()
        df.attrs = {}
        df.to_csv(p, index=False, encoding=ENC)
        if parquet:
            df.to_parquet(self.dirs[folder] / f"{asset_id}.parquet", index=False)
        self.assets.append(dict(asset_id=asset_id, kind="table", file=self.rel(p), caption_th=caption_th,
                                main_text=main, rows=len(df), note=note, section=self.stage, status="generated"))
        return df

    def figure(self, asset_id, fig, data: pd.DataFrame | None = None, caption_th="", main=False, note=""):
        stem = self.dirs["figures"] / asset_id
        for ext in self.S.cfg["figures"]["formats"]:
            fig.savefig(f"{stem}.{ext}", dpi=self.S.cfg["figures"]["dpi"])
        plt.close(fig)
        dfile = ""
        if data is not None:
            dp = self.dirs["plot_data"] / f"{asset_id}_data.csv"
            data.to_csv(dp, index=False, encoding=ENC)
            dfile = self.rel(dp)
        self.assets.append(dict(asset_id=asset_id, kind="figure", file=self.rel(Path(f"{stem}.png")), data_file=dfile,
                                caption_th=caption_th, main_text=main, note=note, section=self.stage, status="generated"))

    def claim(self, cid, value, spec="{:,.2f}", unit="", table="", row="", note="", status="computed"):
        if isinstance(value, (np.bool_, bool)):
            value = float(value)
        v = float(value)
        self.claims.append(dict(claim_id=cid, section=self.stage, value=v, display=fmt(v, spec), fmt=spec, unit=unit,
                                table=table, row_keys=row, note=note, status=status))
        return v

    def text(self, cid, text, table="", note=""):
        self.claims.append(dict(claim_id=cid, section=self.stage, value=text, display=text, fmt="text", unit="",
                                table=table, row_keys="", note=note, status="computed"))

    def finalize(self, extra: dict | None = None):
        base = self.dirs["base"]
        c = pd.DataFrame(self.claims, columns=["claim_id", "section", "value", "display", "fmt", "unit", "table",
                                               "row_keys", "note", "status"])
        if len(c):
            dup = c.claim_id[c.claim_id.duplicated()].tolist()
            assert not dup, f"duplicate claim ids: {dup}"
        c.to_csv(base / f"claims_{self.stage}.csv", index=False, encoding=ENC)
        pd.DataFrame(self.assets).to_csv(base / f"assets_{self.stage}.csv", index=False, encoding=ENC)
        man = manifest(self.S, self.stage)
        man.update(seconds=round(time.time() - self.started, 1), n_assets=len(self.assets), n_claims=len(c))
        if extra:
            man.update(extra)
        (base / f"run_manifest_{self.stage}.json").write_text(json.dumps(man, ensure_ascii=False, indent=1, default=str))
        return man


def manifest(S, stage: str) -> dict:
    from . import inputs as I
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=C4.ROOT, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "src", "config", "notebooks"], cwd=C4.ROOT,
                                    capture_output=True, text=True).stdout.strip())
    except Exception:
        rev, dirty = "", None
    import importlib.metadata as md
    vers = {p: md.version(p) for p in ["pandas", "numpy", "scipy", "statsmodels", "matplotlib", "openpyxl",
                                       "python-docx", "pyarrow"]}
    import scipy
    return dict(stage=stage, run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), scenario=S.name,
                overrides=S.overrides, config_hash=S.hash(), inputs_fingerprint=I.inputs_fingerprint(),
                chapter4_code_hash=C4.code_hash(), chapter5_code_hash=code_hash(), git_revision=rev,
                working_tree_has_uncommitted_pipeline_changes=dirty, python=platform.python_version(),
                packages=vers, solver=f"HiGHS via scipy.optimize.milp (scipy {scipy.__version__})", seed=S.seed)


def code_hash() -> str:
    import hashlib
    h = hashlib.sha256()
    for f in sorted((C4.ROOT / "src" / "chapter5").glob("*.py")):
        h.update(f.read_bytes())
    h.update((C4.ROOT / "config" / "chapter5.toml").read_bytes())
    return h.hexdigest()[:16]


def load_registry(S, kind: str) -> pd.DataFrame:
    frames = [pd.read_csv(p, encoding=ENC, dtype={"display": str}) for p in sorted(S.out.glob(f"{kind}_*.csv"))
              if p.stat().st_size > 10]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
