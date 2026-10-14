# Next-phase plan — progress against the acceptance gates

Date: 14 October 2026. Tracks [next_phase_development_plan_2026-10-14.md](next_phase_development_plan_2026-10-14.md).

## First actionable backlog (plan §9)

| # | Item | Status | Deliverable |
|---|---|---|---|
| 1 | Root-vs-authoring change map; canonical ownership | **Done** (ownership is the plan's default, reversible) | [phase0_reconciliation_map.md](phase0_reconciliation_map.md); `scripts/sync_scientific_source.py`; `make sync-lab-check` / `sync-lab-source` |
| 2 | Single validation table from the Chapter 4/5 artifacts | **Done** | `src/chapter5/validation.py` → `outputs/chapter5/validation/T5_VALIDATION_INVENTORY.csv`; Chapter 5 report appendix ก (`T5A_VALIDATION_SUMMARY`) |
| 3 | Data inventory: PC, CKD, cancer, palliative, BOD, specialists | **Done** | [data_readiness_inventory.md](data_readiness_inventory.md); `scripts/data_readiness_inventory.py` → `outputs/shared/data_readiness_*.csv` |
| 4 | Activity/FTE ledger + one older-person package, worked example, overlap rule | **Done** (placeholders; practitioner review pending) | [activity_fte_ledger.md](activity_fte_ledger.md); `src/services/ledger.py`; `config/services/older_person_home_care.toml`; `tests/test_services_ledger.py` |
| 5 | Classify every Lab control; Tier 1/2 destination | **Done as a proposal** | authoring `docs/workforce_lab_two_tier_controls.md`, `docs/workforce_lab_control_classification.csv` |
| 6 | Prototype one dataset replacement locally | **Done** (one schema) | `src/workspace/replace.py`; `config/workspace/examples/`; `tests/test_workspace_replace.py` |
| 7 | Spatial mechanism diagram and data request | **Done** | [spatial_anchoring_framework.md](spatial_anchoring_framework.md); rows 9–16 in [data_requests.md](data_requests.md), 11–12 in [chapter5_data_requests.md](chapter5_data_requests.md) |

## Phase gates

| Phase | Gate (plan §9) | Status |
|---|---|---|
| 0 Reconcile | New BOD/B/health features preserve Lab functionality | **Met.** Authoring Python tests: 96 passed. Browser tests: no new failures against the unchanged `HEAD`. |
| | Native/browser fixtures agree within tolerance | **Met.** The Pyodide runtime tests serve the merged `src/` and pass. Since 14 Oct (second round), the three service modules also match native runs to a relative 1e-8. |
| | Release provenance complete | **Partly.** Handoff manifest with SHA-256 and code hashes exists. The research tree is not committed (owner decision). |
| | September remains reproducible | **Met.** All 3,148 claims of sections 4.1–4.4 rebuilt with the merged code equal the September copy. Authoring `main` and the promoted release are unchanged. |
| | One coherent snapshot | **Met.** Full rebuild on 14 Oct with frozen code (`outputs/chapter5/logs/rebuild_2026-10-14c_phase0.log`). Stages 5_1, 5_3, 5_4 and 5_5 record the same Chapter 4 and Chapter 5 code hashes (`49d09a46…`, `ac222366…`), configuration and input fingerprint. |
| 1 Validation & contracts | Existing backtests correctly labelled; simple baselines reported | **Met** (validation inventory; persistence, M0, M1, no-change and linear comparators) |
| | An incompatible dataset is rejected | **Met** (missing province, negative value, checksum mismatch) |
| | One compatible replacement gives a traceable sandbox run | **Met.** `outputs/workspaces/demo-bod-minus10/` is a demonstration file lowering two provinces' DALYs by 10%. It contains validation, affected components, family-B target changes, the re-solved B-R plan (2.4% annual destination change) and the health-gain comparison, all with input and code hashes. Canonical outputs were untouched (tested). |
| | UI version/evidence labels | **Not started.** This is authoring work and needs the owner's migration decisions (items 1–3 of the controls note). |
| 2 Task/FTE + ageing pilot | Accounting reconciles; no duplicated time; required ≠ deliverable; unavailable evidence labelled | **Met structurally**, enforced by tests. The package also runs as a data-ready Lab module (`src/services/older_care.py`). **Blocked** for real use until uploaded or obtained dependency prevalence, activity–time data and practitioner review exist. |
| 3 Tier 2 MVP | Accounts, isolation, uploads, jobs | **Partly, local only.** Upload → validate → calibrate → run works in the browser for the three service modules. Nothing is sent or stored, so isolation holds by construction. Missing: accounts, saved and shared workspaces, server-side jobs, and replacement of the study's own allocation inputs in the Lab. |
| 4 First disease module | ESRD cohort model validated against independent aggregates | **Structure built, gate not met.** ESRD and five-site cancer modules exist as draft structures (patient balance tested). They need real data (request 15–16), validation against independent aggregates and clinical review. |
| 5 Anchoring | Donor losses, balanced transfers, zero/adverse cases | **Specified**, not implemented. A descriptive concentration audit can start with the facility returns; effect parameters stay at zero. |
| 6 Monitored releases | Recurring | Not yet applicable |

## Decisions for the owner

1. Commit the research tree. `src/`, `config/` and `notebooks/` are untracked in Git.
2. Merge or discard authoring branch `phase0-october-research-sync`.
3. Whether, and when, to promote and publish an October release. The public site still shows the September release.
4. Lab control migrations (morbidity free edits, solver/seed controls) and whether to expose family B in the Lab.
5. Clinical review of the ESRD and cancer structures and practitioner review of the older-person package, before the service modules are published.
6. Local draft releases on the authoring branch: `20261014T081116Z-993297e241d8` (Phase 0 sync), `20261014T111323Z-f455b6968a16` and `20261014T111958Z-1dd387d08ca4` (service modules; the last is the tested one). Keep the last, discard the others, or promote after review.

## Added later on 14 Oct 2026: data-ready service modules

Owner decision: build older-person care, ESRD and five-site cancer modules now. Users upload the data; the modules validate and calibrate in the browser. See [service_modules.md](service_modules.md).

| Item | Status |
|---|---|
| Engines and contract (`src/services/`) | Done. 12 tests cover balance, refusal without required data, schema rejection, policy never calibrated, stage-shift invariance, provenance. |
| Lab view `labview=modules` (authoring branch) | Done. Synthetic → validate → run in Chromium; malformed upload rejected; no data posted (browser tests). Allocation Lab unaffected (135 authoring tests pass; only the pre-existing S29 layout failure remains). |
| Fixes found while testing | The modules view was reset to the allocation view on page load (`setPolicyContext`). `data/workforce_lab/service_population.json` was excluded by `.gitignore` and would have been dropped on commit. Both are fixed. |
| Clinical/practitioner review | Pending |
| Public release | Not done; needs owner approval |

## Plan items not yet done (checked section by section on 14 Oct 2026)

### A. Possible now with existing data and code — done on 14 Oct 2026 (second round)

| Plan § | Item | What was built | Result or limit |
|---|---|---|---|
| 5.2 B–C | Integrated, cutoff-safe hindcast with fuller metrics | `config/validation.toml` (design and acceptance criteria **declared before the run**, SHA-256 recorded); `src/chapter5/hindcast.py`; tables `T5_HINDCAST_*`; Chapter 5 appendix paragraph | Origins 2020–2023 (after the 2019→2020 HRR break, a deviation from the plan's 2019 origin), horizons 1–5 to 2025. Population is re-projected from each origin and hazards re-estimated on fiscal years ≤ origin. **C1 passed** (stock-flow MAE at 3 years 28.1 vs persistence 33.3 and population-only 32.8). **C2 failed:** the 90% intervals cover 44%, so they are read as scenario ranges. **C3 failed:** lowest-19 Jaccard 0.59 (persistence 0.72), so the priority group is re-identified every year. Services are not hindcast; the score is physician stock only. |
| 5.2 F | Native/browser numeric agreement for the service modules | authoring `tests/test_lab_modules_browser.py::test_browser_and_native_runs_agree` (test hook `?labdebug` only) | All three modules on synthetic data: every table, parameter and check equal to a relative 1e-8 |
| 6.1 | Coverage matrix, missing vs zero, unit definitions | Notebook 4.6 part A (`T46_COVERAGE_MATRIX`, `T46_COVERAGE_BREAKS`, `T46_UNIVERSE_DEFINITIONS`, `F46_COVERAGE`); Chapter 4 appendix ข | 15,246 cells: 9 unreported, 3,881 reported zero. 24 national breaks over 25% (10 private, 5 MOPH). All universes are headcounts, not FTE. |
| 6.1 / 7.3 | Descriptive specialist concentration audit | Notebook 4.6 part B (facility returns joined to the facility register, 100% match); Chapter 4 §4.3.6 | The returns reconcile with HRR at 0.94–0.99 in 2021–2024 (0.77–0.87 earlier), so trends rest on 2021–2024. Specialist share of the top 10% of facilities is about 63%, unchanged. In MOPH, the community-hospital share rose from 13.2% to 17.8%. Centre and community growth co-move (ρ +0.31): no sign of backwash, but also no causal design. |
| 6.1 | Where P, S, N and B rankings disagree | Notebook 4.6 part C (`T46_RANK_DISAGREEMENT*`, `F46_RANK_DISAGREEMENT_MAP`); Chapter 4 §4.3.6 | 8 provinces are low under all four. 11 are low by burden but not by service (mostly Isan; 1.82 OP visits per person). 11 are the reverse (west and south; 3.04). |
| 6.1 | Validation summary in Chapter 4 | `T46_VALIDATION_SUMMARY` (inventory, Chapter 4 rows); Chapter 4 appendix ค | M5 does not beat persistence in 6 of 6 temporal checks |
| 3.1 / 4.1 | Informal caregiver hours; residence vs provider workload | `older_care`: dataset `older_caregiver_time`, table `informal_care_national` (never added to FTE, tested). `src/services/referral.py`; ESRD and cancer `province_last_year_provider` | National totals preserved (checked each run). Gaps are recomputed at the provider. The default provider is the residence. |
| 4.3 | Screening as its own pathway | `cancer.screening` (breast, cervix, colorectal): screened, positives, diagnostic follow-ups, six screening cadres, FTE separate. Dataset `cancer_screening` calibrates positivity and completion. Women by age group added to the population export (`make services-population`). | Screening never changes cases or stage (tested); the stage shift stays a separate policy. Programme defaults are illustrative; breast is off. |
| 8.4 | Staged comparisons; comparability contract | `src/services/compare.py` (`comparability`, `staged`; Lab op `staged`); `src/chapter5/lab_compare.py`, attached to each `compare_runs` pair (guard unchanged) | Effects of new data, refitting/method and policy sum to the total (tested). Verdicts: not comparable / common reference required / directly comparable. |
| 8.2 | Compact validation view; provider/resident switch | Lab main view: "แบบจำลองทำนายได้ดีแค่ไหน" panel from `lab.json.validation` (synced from `outputs/chapter5/validation/lab_validation.json`). Module results: residence/provider toggle; staged-comparison panel. | **Partly.** The side-by-side narrative (population, service, burden, care package) and provider/resident **maps** in the allocation Lab are not done; they belong with the Tier 1 interface decisions (B). |

#### Verification of the second round (14 Oct 2026, 21:30)

- **Full rebuild:** `make chapter4 && make chapter5`, log `outputs/chapter5/logs/full_rebuild_groupA_201634.log`.
  - Chapter 4: 670 claims and 51 assets. Chapter 5: 284 claims and 28 assets. No unresolved claim in either report.
  - Stages 5_1, 5_3, 5_4 and 5_5 record the same Chapter 4 and Chapter 5 code hashes (`a45b9fdd…`, `7fd1bade…`) and the same input fingerprint (`c21bd7c5…`).
  - The same four sensitivity plans fail as in every earlier build (`NFB1-R|ols` and three `pool2500` plans).
- **Research-tree tests:** 129 passed (including `tests/test_service_modules.py` and `tests/test_lab_compare.py`). `tests/test_web_bundle.py` fails because it needs the untracked legacy folder `output/analyse/ch4x`, which is absent; this predates this work.
- **Authoring workspace:**
  - Python tests: 111 passed.
  - Story browser tests on a fresh server: 26 passed. The only failure is the earlier S29 viewport check on the promoted September release.
  - `LAB_UI_TEST=1`: 7 passed. These cover browser/native agreement for three modules, the provider view, the staged comparison and the validation view.
  - `LAB_RUNTIME_TEST=1`: 4 passed, including the comparability verdict on `compare_runs`.
- **Sync and draft release:** the source is synced (50 identical files). Draft release `20261014T131708Z-dc5aa8f7c72c` has 0 errors and is **not promoted**.

### B. Waiting for owner decisions

| Plan § | Item |
|---|---|
| 2.3 / 9 | Commit the research tree; merge the authoring branch; promote and publish an October release. |
| 8.1 | Tier 1 interface: "Reproduce study baseline" versus "Explore policy" modes, baseline/sensitivity/user-scenario badges, and moving controls to Tier 2 per the classification proposal. |
| 6.2 / 8.1 | Family B in the Lab. It needs aggregate BOD inputs in the public release and its own tested adaptive rule; adaptive replanning still covers P/S/N only. |

### C. Waiting for data, expert review or infrastructure

| Plan § | Item | Needs |
|---|---|---|
| 4.1 | Dependency-state transitions; functional/QoL outcomes | Longitudinal care-state data; an outcome model |
| 4.2 | Calibrated ESRD module; initiation policy versus unmet need; discrete-event model of chairs and queues; costs | TRT registry/NHSO data (request 15); clinical review; unit costs |
| 4.3 | Calibrated cancer modules; discrete-event radiotherapy queue model | Registry incidence, stage and treatment (request 16); waiting-time data |
| 5.2 D | Care-package validation against service logs or time-use samples | Practitioner review; activity–time study (request 14) |
| 6.2 | Multi-cadre supply and teams; packages combining retention, task sharing, contracting and technology; budget feasibility | Cadre supply/training pipelines; task–time data; costs |
| 7.2–7.3 | Anchor-policy scenario module with measured mechanisms; empirical evaluation of centres | Workforce origin–destination moves, referral flows, opening dates, travel times (requests 9–12) |
| 8.1–8.3 | Tier 2 proper: accounts, saved and shared workspaces, server jobs, replacement of the study's allocation inputs | Hosting, authentication and storage decisions |
| 9 (Phase 6) | Monitored releases with a validation dashboard | Earlier gates |
