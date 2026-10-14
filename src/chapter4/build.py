"""Build entry point for Chapter 4.

    .venv/bin/python -m chapter4.build --shared          # canonical tables + shared audits
    .venv/bin/python -m chapter4.build --section 4.2     # execute one notebook (after its dependencies)
    .venv/bin/python -m chapter4.build --report          # render reports/chapter4_complete_th.{md,docx}
    .venv/bin/python -m chapter4.build --all             # everything, in order

(run from the repository root with PYTHONPATH=src, or use `make chapter4`).

Notebooks are executed in a fresh kernel with nbclient and saved with their outputs.  A
section whose inputs from an earlier section are missing or were produced from different
processed data stops with a message naming the target to build; nothing stale is loaded.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import pandas as pd

from . import config as C

NOTEBOOKS = {"4.1": "chapter4_1_counts_and_services.ipynb",
             "4.2": "chapter4_2_denominators_workload_and_need.ipynb",
             "4.3": "chapter4_3_distribution_and_inequality.ipynb",
             "4.4": "chapter4_4_entries_exits_and_growth.ipynb",
             "4.5": "chapter4_5_burden_of_disease.ipynb",
             "4.6": "chapter4_6_coverage_spatial_validation.ipynb"}
DEPENDS = {"4.1": [], "4.2": [], "4.3": ["4.2"], "4.4": ["4.3"], "4.5": ["4.2", "4.3"], "4.6": ["4.3", "4.5"]}


def build_shared(force: bool = False):
    from . import ingest, panels
    meta = ingest.build_processed(force=force)
    out = C.SHARED_OUT
    out.mkdir(parents=True, exist_ok=True)
    enc = C.CFG["figures"]["csv_encoding"]
    # source inventory with hashes, roles and downstream users
    rows = []
    for sid, s in C.SOURCES.items():
        p = C.ROOT / s["path"]
        files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file() and f.suffix in (".xlsx", ".csv"))
        for f in files:
            rows.append(dict(source_id=sid, path=str(f.relative_to(C.ROOT)), size_bytes=f.stat().st_size,
                             sha256=C.file_sha256(f), role=s["role"], title=s["title"], agency=s["agency"],
                             years=s["years"], year_basis=s["year_basis"], geography=s["geography"],
                             units=s["units"], used_by="; ".join(s["used_by"])))
    pd.DataFrame(rows).to_csv(out / "source_inventory.csv", index=False, encoding=enc)
    for name, df in panels.audit_tables().items():
        df.to_csv(out / f"{name}.csv", index=False, encoding=enc)
    panels.key().to_csv(out / "province_region_crosswalk.csv", index=False, encoding=enc)
    d, _ = panels.province_panel()
    d.to_csv(C.PROCESSED / "province_panel_76.csv", index=False, encoding="utf-8")
    json.dump(meta, open(out / "processed_build_meta.json", "w"), ensure_ascii=False, indent=1)
    print("shared audits written to", out.relative_to(C.ROOT))


def _check_dependency(dep: str):
    base = C.OUTPUTS / f"chapter{dep.replace('.', '_')}"
    man = base / "run_manifest.json"
    if not man.exists():
        raise SystemExit(f"section {dep} outputs missing - run: python -m chapter4.build --section {dep}")
    m = json.loads(man.read_text())
    cur = json.loads((C.PROCESSED / "_build_meta.json").read_text())
    if (m.get("processed_data") or {}).get("inputs") != cur.get("inputs"):
        raise SystemExit(f"section {dep} was built from different processed data - rebuild it: "
                         f"python -m chapter4.build --section {dep}")


def run_notebook(section: str, timeout: int = 3600):
    import nbformat
    from nbclient import NotebookClient
    for dep in DEPENDS[section]:
        _check_dependency(dep)
    path = C.ROOT / "notebooks" / NOTEBOOKS[section]
    nb = nbformat.read(path, as_version=4)
    t0 = time.time()
    client = NotebookClient(nb, timeout=timeout, kernel_name="python3",
                            resources={"metadata": {"path": str(path.parent)}})
    client.execute()
    nbformat.write(nb, path)
    print(f"executed {path.relative_to(C.ROOT)} in {time.time() - t0:.0f} s")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="chapter4.build")
    ap.add_argument("--shared", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-read raw sources even if unchanged")
    ap.add_argument("--section", action="append", choices=list(NOTEBOOKS))
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    if a.all or a.shared:
        build_shared(force=a.force)
    for s in (list(NOTEBOOKS) if a.all else (a.section or [])):
        run_notebook(s)
    if a.all or a.report:
        from . import report
        report.render()
    if not (a.all or a.shared or a.section or a.report):
        ap.print_help()


if __name__ == "__main__":
    sys.exit(main())
