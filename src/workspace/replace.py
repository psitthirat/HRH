"""Prototype: replace one dataset, validate it, invalidate what depends on it, run a sandbox.

Next-phase plan §8.3 and backlog item 6.  One schema is implemented, `bod_province_age/1` (the
S15 BOD 2022 age-specific file layout).  Canonical outputs are never written; a sandbox run goes
to outputs/workspaces/<name>/ with a run manifest that ties every result to its inputs.

    PYTHONPATH=src .venv/bin/python -m workspace.replace --manifest m.json --data f.csv --name try1 [--solve]

Steps
  1. read the dataset manifest (declared metadata, plan §8.3) and check its declared checksum;
  2. validate the file against the schema: columns, keys, duplicates, non-negative values,
     DALY = YLL + YLD, rate = count / mid_pop, province codes, completeness.  Missing provinces
     are never filled with zeros: an incomplete file is rejected;
  3. list the dependent components (DEPENDENCIES) and the action each needs (recompute, refit,
     evaluation only) - nothing that does not depend on the dataset is touched;
  4. recompute in a sandbox: expected burden and family B targets; optionally re-solve B-R; the
     illustrative health gain of the canonical plans with the new amenable burden;
  5. write the run manifest (input hashes for canonical and replacement data, code hashes,
     configuration hash, affected components, warnings) and old-vs-new comparison tables.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from chapter4 import config as C4

SANDBOX = C4.OUTPUTS / "workspaces"

SCHEMAS = {
    "bod_province_age/1": dict(
        required_columns=["area_name", "area_name_th", "codv", "codv_name_eng", "codv_name_th", "age_grp8",
                          "sex_name_th", "year_ce", "DALY", "YLL", "YLD_NEW", "deaths", "mid_pop",
                          "DALY_rate", "YLL_rate", "YLD_rate", "death_rate"],
        keys=["area_name", "codv", "age_grp8"],
        nonnegative=["DALY", "YLL", "YLD_NEW", "deaths", "mid_pop"],
        age_groups=8, causes=174, provinces=77,
        description="BOD Thailand provincial burden by 8 age groups (layout of S15_BOD_AGE)"),
}

MANIFEST_FIELDS = ["dataset_id", "schema", "title", "source", "permitted_use", "period", "geography", "units",
                   "definitions", "coverage", "missingness", "replaces", "sha256"]

# dataset -> dependent components; action: recompute (no fitted quantity changes), refit, evaluation_only
DEPENDENCIES = {
    "bod_province_age": [
        ("chapter4.panels.burden_age_rates / expected burden panel", "recompute", "age-specific rates change"),
        ("chapter4 section 4.5 burden analyses (A6, D, E)", "recompute", "crude burden, decomposition, burden denominators"),
        ("chapter5 family B indices (D_B, D_Byld; D_Basr via re-standardization)", "recompute", "targets of B plans"),
        ("chapter5 plans B-R, B-RT, B-R|B, B-R|yld, B-R|asr, B-R|net, B-RT|net", "recompute", "targets change; solver re-run"),
        ("chapter5 health-gain evaluation", "evaluation_only", "amenable burden changes; plans unchanged"),
        ("chapter4 M0-M5 fits and N-STD", "unaffected", "the models do not use the age-specific BOD file"),
        ("chapter5 P, S, N, N-FB plans", "unaffected", "their targets do not depend on BOD"),
    ],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_manifest(path: Path) -> dict:
    m = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [f for f in MANIFEST_FIELDS if f not in m]
    if missing:
        raise ValueError(f"dataset manifest lacks {missing}")
    if m["schema"] not in SCHEMAS:
        raise ValueError(f"unsupported schema {m['schema']}; supported: {sorted(SCHEMAS)}")
    return m


def validate(manifest: dict, data: Path) -> dict:
    """Returns {'ok': bool, 'errors': [...], 'warnings': [...], 'table': canonical frame or None}."""
    sch = SCHEMAS[manifest["schema"]]
    errs, warns = [], []
    actual = sha256(data)
    if manifest["sha256"] not in ("", actual):
        errs.append(f"checksum mismatch: manifest {manifest['sha256'][:12]}..., file {actual[:12]}...")
    d = pd.read_csv(data)
    d.columns = [c.replace("﻿", "") for c in d.columns]
    miss = [c for c in sch["required_columns"] if c not in d.columns]
    if miss:
        return dict(ok=False, errors=errs + [f"missing columns {miss}"], warnings=warns, table=None, sha256=actual)
    if d.duplicated(sch["keys"]).any():
        errs.append(f"{int(d.duplicated(sch['keys']).sum())} duplicate {sch['keys']} keys")
    num = d[sch["nonnegative"]].apply(pd.to_numeric, errors="coerce")
    if num.isna().any().any():
        errs.append("non-numeric or missing values in " + ", ".join(num.columns[num.isna().any()]))
    if (num < 0).any().any():
        errs.append("negative values in " + ", ".join(num.columns[(num < 0).any()]))
    if d.area_name.nunique() != sch["provinces"]:
        errs.append(f"{d.area_name.nunique()} provinces, expected {sch['provinces']} (missing provinces are never zero-filled)")
    if d.codv.nunique() != sch["causes"] or d.age_grp8.nunique() != sch["age_groups"]:
        errs.append(f"{d.codv.nunique()} causes x {d.age_grp8.nunique()} age groups, expected {sch['causes']} x {sch['age_groups']}")
    if len(d) != sch["provinces"] * sch["causes"] * sch["age_groups"]:
        errs.append(f"{len(d)} rows, expected the complete grid of {sch['provinces'] * sch['causes'] * sch['age_groups']}")
    if not errs:
        if (d.DALY - d.YLL - d.YLD_NEW).abs().max() > 1e-6:
            errs.append("DALY != YLL + YLD")
        if (1e5 * d.DALY / d.mid_pop - d.DALY_rate).abs().max() > 1e-6:
            errs.append("DALY_rate != DALY / mid_pop x 100,000")
    if errs:
        return dict(ok=False, errors=errs, warnings=warns, table=None, sha256=actual)
    # canonical conversion with the same reader as the pipeline (ASR cross-check skipped: rates may differ)
    from chapter4 import ingest
    key = ingest.load("province_key")
    try:
        table = ingest.read_bod_age(key, ingest.load("bod_province"), path=data, check_asr=False)
    except (AssertionError, ValueError, KeyError) as e:
        return dict(ok=False, errors=[f"canonical conversion failed: {e}"], warnings=warns, table=None, sha256=actual)
    base = ingest.load("bod_province_age")
    m = table.merge(base, on=["prov_code", "cause_code", "age_group"], suffixes=("", "_base"))
    changed = m[(m.daly - m.daly_base).abs() > 1e-9]
    warns.append(f"{len(changed)} of {len(m)} province-cause-age cells differ from the canonical file "
                 f"({changed.prov_code.nunique()} provinces)")
    if (m.mid_pop - m.mid_pop_base).abs().max() > 0:
        warns.append("mid-year population differs from the canonical file; rates, not counts, drive the projection")
    return dict(ok=True, errors=[], warnings=warns, table=table, sha256=actual)


def burden_inputs_from(table: pd.DataFrame) -> dict:
    """Family-B inputs (as chapter5.responsibilities.burden_inputs) from a canonical bod_province_age table;
    the age-standardized rate is re-standardized with the WHO weights of the source."""
    cfg = C4.CFG["burden"]
    keep = ~table.cause_code.isin(cfg["exclude_causes"])
    g = table[keep].groupby(["prov_code", "age_group"])[["daly", "yld"]].sum()
    pop = table.groupby(["prov_code", "age_group"]).mid_pop.first()
    rate = g.div(pop, axis=0)
    who = np.array(cfg["who_standard"], float)
    edges = [0, 1, 3, 6, 9, 12, 14, 16, len(who)]
    w8 = np.array([who[a:b].sum() for a, b in zip(edges[:-1], edges[1:])])
    w8 = w8 / w8.sum()
    rd = rate.daly.unstack("age_group").sort_index(axis=1)
    return dict(rate_daly=rd, rate_yld=rate.yld.unstack("age_group").sort_index(axis=1),
                asr_daly=pd.Series(1e5 * rd.to_numpy() @ w8, index=rd.index))


def sandbox(manifest: dict, data: Path, name: str, solve: bool = False) -> dict:
    from chapter5 import config as C5, health_gain as HG, pipeline as PL, responsibilities as R
    from chapter5 import reporting as R5
    v = validate(manifest, data)
    out = SANDBOX / name
    out.mkdir(parents=True, exist_ok=True)
    run = dict(schema="hrh-workspace-run/1", name=name, created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               dataset=dict(manifest=manifest, file=str(data), sha256=v["sha256"]),
               validation=dict(ok=v["ok"], errors=v["errors"], warnings=v["warnings"]))
    if not v["ok"]:
        (out / "run_manifest.json").write_text(json.dumps(run, ensure_ascii=False, indent=1))
        return run
    did = manifest["schema"].split("/")[0]
    run["affected_components"] = [dict(component=c, action=a, reason=r) for c, a, r in DEPENDENCIES[did]]
    S = C5.load()
    ctx = PL.context()
    run.update(config_hash=S.hash(), chapter4_code_hash=C4.code_hash(), chapter5_code_hash=R5.code_hash(),
               canonical_inputs_fingerprint=__import__("chapter5.inputs", fromlist=["x"]).inputs_fingerprint())
    burden = burden_inputs_from(v["table"])
    idx, reg, _ = R.build_indices(S, ctx.base, ctx.pop, ctx.ent, ctx.svc, ctx.pkg, w=ctx.w, burden=burden)
    ctx2 = dataclasses.replace(ctx, idx=idx)
    by, last = S.base_year, S.years[-1]
    cmp_ = []
    for y in [by, last]:
        a = ctx.idx[ctx.idx.year == y].set_index("prov_code")
        b = idx[idx.year == y].set_index("prov_code")
        cmp_.append(pd.DataFrame({"year": y, "prov_code": a.index, "province": [ctx.names[p] for p in a.index],
                                  "B_share_canonical": a.D_B / a.D_B.sum(), "B_share_replacement": b.D_B / b.D_B.sum(),
                                  "expected_daly_canonical": a.B_B, "expected_daly_replacement": b.B_B}))
    CMP = pd.concat(cmp_, ignore_index=True)
    CMP["share_change_pct"] = 100 * (CMP.B_share_replacement / CMP.B_share_canonical - 1)
    CMP.to_csv(out / "family_B_target_comparison.csv", index=False, encoding="utf-8-sig")
    reg.to_csv(out / "denominator_registry.csv", index=False, encoding="utf-8-sig")
    res = {r["job_id"]: r for r in PL.load_plan_results(S)}
    plans = [p for p in ["P-R", "S-R", "N-R", "B-R"] if p in res]
    HGn, _, _ = HG.evaluate(ctx, res, plans, bod=v["table"])
    HGo, _, _ = HG.evaluate(ctx, res, plans)
    hg = HGo.merge(HGn, on=["plan_id", "measure", "elasticity_label"], suffixes=("_canonical", "_replacement"))
    hg[["plan_id", "measure", "elasticity_label", "averted_total_canonical", "averted_total_replacement",
        "averted_vs_PR_pct_canonical", "averted_vs_PR_pct_replacement"]].to_csv(
        out / "health_gain_comparison.csv", index=False, encoding="utf-8-sig")
    summary = dict(max_abs_B_share_change_pct=float(CMP.share_change_pct.abs().max()),
                   provinces_B_share_changed=int((CMP[CMP.year == last].share_change_pct.abs() > 1e-9).sum()))
    if solve:
        spec = next(j["spec"] for j in PL.catalogue(S) if j["job_id"] == "B-R")
        T = PL.T_of(ctx2, "D_B", "common_total")
        from chapter5 import allocation as AL, simulation as SIM
        pb = SIM.make_problem(ctx2, spec, T)
        sol = AL.solve(pb)
        pk = PL._package(ctx2, spec, pb, sol, "milp")
        old = res["B-R"]
        sw = 0.5 * np.abs(pk["x"] - old["x"]).sum(1) / old["x"].sum(1)
        pk["ledger"].to_csv(out / "B-R_ledger_replacement.csv", index=False, encoding="utf-8-sig")
        summary.update(B_R_status=pk["status"], B_R_mean_annual_switch_pct=float(100 * sw.mean()),
                       B_R_objective_replacement=pk.get("objective_exact"), B_R_objective_canonical=old.get("objective_exact"))
        run["recomputed"] = ["family B indices", "health gain (evaluation)", "B-R plan"]
    else:
        run["recomputed"] = ["family B indices", "health gain (evaluation)"]
        run["not_recomputed"] = ["B plans (pass --solve)"]
    run["summary"] = summary
    run["outputs"] = sorted(p.name for p in out.iterdir() if p.name != "run_manifest.json")
    (out / "run_manifest.json").write_text(json.dumps(run, ensure_ascii=False, indent=1, default=str))
    return run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="validate a replacement dataset and run a sandbox")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--solve", action="store_true", help="also re-solve the B-R plan (about 20 s)")
    a = ap.parse_args(argv)
    run = sandbox(read_manifest(a.manifest), a.data, a.name, a.solve)
    print(json.dumps({k: run[k] for k in ["validation", "summary"] if k in run}, ensure_ascii=False, indent=1, default=str))
    return 0 if run["validation"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
