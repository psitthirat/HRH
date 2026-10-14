"""Build entry point for Chapter 5.

    PYTHONPATH=src .venv/bin/python -m chapter5.build --all                 # everything, canonical
    PYTHONPATH=src .venv/bin/python -m chapter5.build --inputs              # input contract, projections, indices
    PYTHONPATH=src .venv/bin/python -m chapter5.build --plans               # all deterministic plans (parallel)
    PYTHONPATH=src .venv/bin/python -m chapter5.build --uncertainty [--runs 500 --adaptive 60]
    PYTHONPATH=src .venv/bin/python -m chapter5.build --compare             # comparisons, figures, workbook
    PYTHONPATH=src .venv/bin/python -m chapter5.build --report              # Thai report (md + docx)
    PYTHONPATH=src .venv/bin/python -m chapter5.build --notebooks           # execute the three notebooks

What-if runs (never overwrite canonical outputs; written to outputs/chapter5_scenarios/<name>/):
    ... -m chapter5.build --all --set supply.annual_path=2500 --name pool2500
    ... -m chapter5.build --all --set allocation.cap_mode=net_growth --set allocation.main_transfer_fraction=0.05
    ... -m chapter5.build --all --set targets.reference_per_1000=0.5 --principal-only

`make chapter5` runs the canonical build.
"""
from __future__ import annotations

import argparse
import sys
import time

from . import config as C


def main(argv=None):
    ap = argparse.ArgumentParser(prog="chapter5.build")
    for f in ["inputs", "plans", "uncertainty", "compare", "report", "notebooks", "all"]:
        ap.add_argument(f"--{f}", action="store_true")
    ap.add_argument("--set", action="append", default=[], help="dotted.key=value override (repeatable)")
    ap.add_argument("--name", default=None, help="scenario folder name for overrides")
    ap.add_argument("--runs", type=int, default=None)
    ap.add_argument("--adaptive", type=int, default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--principal-only", action="store_true", help="plans: principal + variants only")
    a = ap.parse_args(argv)
    S = C.load(C.parse_overrides(a.set), a.name)
    for w in C.validate(S.cfg):
        print("WARNING:", w)
    print(f"chapter5 build: scenario={S.name} config_hash={S.hash()} -> {S.out}")
    t0 = time.time()
    if a.all or a.inputs:
        from . import pipeline as PL
        PL.stage_inputs(S)
        print(f"  inputs done ({time.time() - t0:.0f} s)")
    if a.all or a.plans:
        from . import pipeline as PL
        which = ("principal", "variant", "benchmark") if a.principal_only else \
            ("principal", "variant", "sensitivity", "benchmark")
        PL.stage_plans(S, a.workers, which)
        print(f"  plans done ({time.time() - t0:.0f} s)")
    if a.all or a.uncertainty:
        from . import analysis as AN
        AN.stage_uncertainty(S, a.runs, a.adaptive, a.workers)
        print(f"  uncertainty done ({time.time() - t0:.0f} s)")
    if a.all or a.compare:
        from . import analysis as AN, figures as FG, workbook as WB
        AN.stage_compare(S)
        FG.make_all(S)
        WB.write(S)
        print(f"  compare, figures and workbook done ({time.time() - t0:.0f} s)")
    if a.all or a.report:
        from . import report as RP
        RP.render(S)
        print(f"  report done ({time.time() - t0:.0f} s)")
    if a.notebooks:
        run_notebooks()
    if not any([a.all, a.inputs, a.plans, a.uncertainty, a.compare, a.report, a.notebooks]):
        ap.print_help()


def run_notebooks(timeout=7200):
    import nbformat
    from nbclient import NotebookClient
    for nb_name in ["chapter5_1_inputs_and_projection.ipynb", "chapter5_2_allocation_and_simulation.ipynb",
                    "chapter5_3_comparison_and_policy.ipynb"]:
        p = C.ROOT / "notebooks" / nb_name
        nb = nbformat.read(p, as_version=4)
        t0 = time.time()
        NotebookClient(nb, timeout=timeout, kernel_name="python3", resources={"metadata": {"path": str(p.parent)}}).execute()
        nbformat.write(nb, p)
        print(f"executed {p.name} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    sys.exit(main())
