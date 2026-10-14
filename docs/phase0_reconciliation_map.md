# Phase 0 — reconciling the research tree and the Lab authoring workspace

Date: 14 October 2026. Implements backlog item 1 of the [next-phase plan](next_phase_development_plan_2026-10-14.md) (§2.3, Phase 0).

## Decision: one owner for the scientific source

| Layer | Owner | Location |
|---|---|---|
| Scientific code: `src/chapter4/*.py`, `src/chapter5/*.py` (including the Lab adapter modules) | **Research tree** | this repository |
| Analysis configuration: `config/analysis.toml`, `source_registry.toml`, `chapter5.toml`, `chapter5_health_gain.toml` | **Research tree** | this repository |
| Raw and processed data, analysis outputs, Thai reports | Research tree | this repository |
| Presentation, Lab interface, Lab registries (`config/workforce_lab/`, `config/web/`), release assembly (`scripts/webstory/`), story site | **Authoring workspace** | `workspaces/HRH-authoring` (separate private Git repository) |

The authoring workspace receives a byte-identical copy of the scientific files through
`make sync-lab-source` (`scripts/sync_scientific_source.py`). That copy carries
`SCIENTIFIC_SOURCE_MANIFEST.json` with each file's SHA-256, both code hashes and the research
tree's commit. The script refuses to overwrite a file edited in the workspace. A scientific
change made while working on the Lab is moved into the research tree first and then synced back.
`make sync-lab-check` lists any drift.

This is the plan's default recommendation. It is reversible: nothing has been pushed, and the authoring change sits on a local branch.

## Method

Both trees descend from the handoff snapshot in authoring commit `835fad5` (27 Sep 2026, release
`20260927T131223Z-d9cf7dc92a81`). Each file was compared with that base:

| File | Research tree since base | Authoring since base | Resolution |
|---|---|---|---|
| `chapter4/build.py`, `config.py`, `ingest.py`, `metrics.py`, `reporting.py` | BOD sources, section 4.5, `source_fingerprint`, concentration index | — | research tree |
| `chapter4/models.py` | `bod`/`bod3` design blocks | `design()` moved to `model_design.py` | conflict: authoring structure, burden blocks moved into `model_design.py` |
| `chapter4/panels.py` | burden tables, expected burden, panel merge | constants imported from `model_design.py` | conflict: authoring import plus burden constants |
| `chapter4/model_design.py` | — | new (browser-loadable design, no fitting packages) | authoring, plus `BURDEN`/`BURDEN_GROUPS` and the two blocks |
| `chapter5/allocation.py` | — | optional population-reserved quota (inactive at share 0) | authoring |
| `chapter5/analysis.py` | B family, health gain, T56 by code | `path_targets`/`path_metrics` moved to `uncertainty.py`; T56 by code | conflict: authoring move; research T56 (adds B) |
| `chapter5/uncertainty.py` | — | new; also fixes the IP-days weight of N paths (`conv_N`) | authoring, plus B in the population branch |
| `chapter5/responsibilities.py` | B family (age-specific), registry rows | `panel=` injection; `model_design` import; lazy panel import | clean merge; B made injectable (`burden=None` native, dict injected, `False` omitted) |
| `chapter5/simulation.py` | B columns in the ledger | reserved quota, year-varying hazards, adaptive diagnostics | clean merge; B ledger columns only when present |
| `chapter5/pipeline.py` | B plans, claims | — | research tree; `eval_targets` skips absent families |
| `chapter5/lab_adapter.py`, `lab_adaptive.py`, `lab_experiments.py` | — | new | authoring; adapter passes `burden=False` unless inputs supply BOD |
| `chapter5/health_gain.py`, `config/chapter5_health_gain.toml` | new | — | research tree |
| `chapter5/demography.py`, `figures.py`, `inputs.py` | BOD age groups, B figure/colour, readiness row | — | research tree |
| `config/analysis.toml`, `source_registry.toml` | `[burden]`, S14/S15 | — | research tree |

## Verification (14 October 2026)

| Check | Result |
|---|---|
| Research-tree tests | 32 passed |
| Re-solve with merged code vs the 12:22 plan cache | P-R, N-R, B-R: identical objective, targets and appointments. S-R: objective +0.018% with 844 switched appointments. Its secondary stage hit the 240 s limit in both runs, so this is the known non-uniqueness of near-optimal schedules, not a code effect. |
| Authoring Python tests on synced code | 96 passed, 8 skipped |
| Authoring browser tests (Pyodide engine served from `src/`) | Same result set as the unchanged authoring `HEAD`. Of the 13 failures seen on both, 12 came from a stale server left on port 8780 since 27 Sep (it serves another site). Against a fresh server, 27 of 28 story/export tests pass. The remaining failure (scene S29 overflows at 1440×900) also fails on the unchanged `HEAD`. |
| Story build | `story-check`: 0 errors, 1 standing freshness warning. A local **draft** release `20261014T081116Z-993297e241d8` was built on branch `phase0-october-research-sync`; it is not promoted or published. The public site still serves `20260927T223014Z-e20170082d16`. |

## What the Lab does and does not get

- The Lab runs with family B omitted (`burden=False`). Exposing B needs three things: aggregate BOD inputs in the Lab package, parameter/outcome registry entries, and interface labels. The plan places this in Phase 1, behind evidence labels.
- `health_gain.py` is synced but not wired into the Lab. It remains a research-side evaluation layer.
- The September public release remains reproducible: authoring `main` (`85ecb8f`) and its promoted release are unchanged.

## Open items needing the owner's decision

1. **Commit the research tree.** `src/`, `config/`, `notebooks/`, `reports/templates/` and the October work are untracked in Git. The only copy of the pre-merge state is a temporary scratch backup. The manifest records `canonical_files_uncommitted: true`.
2. **Merge or keep the authoring branch.** `phase0-october-research-sync` holds the synced source and the draft release.
3. **Public release.** Promoting or publishing an October release is an outward-facing step for the owner to decide.
