# Chapter 5 — completion report

Run: canonical configuration `config/chapter5.toml` (config hash in `outputs/chapter5/validation/chapter5_run_manifest.json`).
Rebuild: `make chapter5` (≈1 h on 10 cores: plans ≈40 min, uncertainty ≈16 min, the rest <2 min).

## Status

Every executed plan is an **`exploratory_policy_scenario`**: the baseline is the MOPH-wide 2025 stock
standing in for the OPS stock, and the pool (2,000 accepted starts/yr), 10% cap, 2% transfer limit,
95% origin protection, 10/90-minute service weights and 1:1,000 reference are illustrative. Other
statuses used: `infeasible_under_selected_constraints` (pool 2,500 under the gross-arrival cap: at
least 373 physicians cannot be placed in 2026, 1,078 over 2026–2030) and
`blocked_for_specific_reason` (N-FB with OLS M5 levels: non-positive AdjRW prediction for Pathum
Thani in 2040).

## Acceptance checklist

| Item | Result |
|---|---|
| 15 allocation years 2026–2040; 2025 baseline | yes (validated in config) |
| 76 provinces in every complete plan | yes; 1,140 province-year rows asserted per plan |
| Scope, headcount, calendar conventions explicit | yes (config `[scope]`, report 5.2, methods §1) |
| Production vs appointments vs accepted starts | three supply modes; plans use accepted starts; graduate/intake modes exported with illustrative parameters |
| Stock–flow reconciliation, no CAGR multiplier | ledger identity closes to <1e-6; national balance difference 0 |
| Integer decisions, exact pool conservation | independent check on every plan (0 of 73 optimised plans fail) |
| Floors and each cap type enforced or flagged | gross-arrival and net-growth caps both run; infeasibility reported with minimum unplaced balance |
| Origin protection, eligibility, transfer conservation | checked; routes reconcile with outflows; regional-network and surplus-only variants |
| Shared assumptions across P/S/N | one context; differences in realised totals come only from province-specific departure risk |
| N-STD vs resource-responsive services separate | yes; N-STD invariance to physicians tested |
| Feedback timing rule, not self-certified | lagged one year; evaluated against the fixed N-STD reference |
| Invalid/out-of-support M5 visible | support table by year (93% of province-years outside the training range by 2040); OLS attempt blocked, not clipped |
| Physician-specific adequacy reference | 1 per 1,000, labelled illustrative (not WHO 4.45) |
| Objective distinguishes allocations | squared proportional shortfall; lexicographic stages |
| No future information in adaptive decisions | tested (`test_adaptive_decisions_use_no_future_information`) |
| Constraints under stochastic realisations | cap breaches (21% of province-years in P-R) and cancelled transfers reported, not repaired |
| Cross-evaluation against every denominator | `T5_CROSS_EVALUATION_LONG`, `T56_CROSS_EVALUATION` |
| Practical differences in doctors, provinces, years | `T5_PRACTICAL_DIFFERENCES`, `T5_PROVINCE_DIFFERENCES`, `T5_SWITCHES` |
| Annual workbook | `outputs/chapter5/plans/chapter5_annual_allocation_plans.xlsx` |
| Reproducible from one configuration | claim registry drives the report; `--set` overrides write to scenario folders |
| Blockers named with the affected claim | `docs/chapter5_data_requests.md` |

## Main results (canonical run)

* National adequacy rises from 0.38 to 0.54 of 1:1,000 by 2040 in every plan (≈30,000 physicians).
  All provinces stay below target, so the whole shortfall is national scarcity; the spatial
  component is zero at 1:1,000 and appears only at a 0.5:1,000 reference.
* The denominator changes *where* physicians go: population vs services switches 9.6% of new
  appointments per year (2,887 over 15 years), population vs M5 need proxy 6.0%, services vs need
  10.0%, population vs historical shares 14.8%. Near-optimal allocations are not unique: re-solving
  P-R with a finer tangent grid, a greedy heuristic or rolling replanning changes 4.6–5.7% of
  destinations at <0.1% objective difference, so P↔N is only just above that level.
* Against the population criterion, P-R lowers the Gini of attainment from 0.121 to 0.083 by 2040,
  N-R to 0.094, S-R raises it to 0.140 and the historical pattern (SQ-C) to 0.182. Regret across
  criteria is smallest for N-R (≤1.2%) and largest for S-R (≤1.8%).
* The cap definition matters more than the denominator for the worst-off: under the 10% gross-arrival
  cap Bueng Kan (13.4% annual exit probability) cannot replace its exits (72 → 37 physicians);
  under a 10% net-growth cap it reaches the common level (0.54) and destinations change by 20%/yr.
* Controlled transfers (2–5%) add essentially nothing once new appointments are targeted: zero
  transfers under the gross cap; under the net cap 545–976 events change J by only 0.01–0.06%.
* Inverse feasibility: 1:1,000 by 2040 is unreachable under the gross cap at any production level
  (national maximum 0.73; every-province maximum 0.11, bound by Bueng Kan). Under the net cap the
  national reference needs ≈58,000 appointments over 15 years (ramping to ≈6,900 in 2040) but no
  production level brings every province to it (maximum 0.80).
* Feedback (N-FB, λ=1): own-target adequacy looks better (bottom quartile 0.449, Gini 0.041), but
  against the fixed N-STD reference the Gini stays at 0.114 vs 0.073 for N-R — the rule preserves
  existing concentration. Mean target gain per added physician 0.85 in 2026; >1 in 7 provinces.
* Uncertainty (500 paired paths): S-R below P-R for the bottom quartile in every path; N-R and P-R
  indistinguishable. Adaptive replanning (60 paths) is close to the fixed schedule and to the
  perfect-foresight bound (cumulative J 4.327 vs 4.330 vs 4.327 for P-R).

## Solver notes

HiGHS via `scipy.optimize.milp`; primary-stage gap ≤0.02% for recruitment-only plans. Six transfer
plans could not beat their recruitment-only counterpart within the time limit and adopted it (gap
to the dual bound ≤0.71%). Secondary stages are time-limited and report "incumbent retained".
P-R|pool1500 stopped at a 0.47% gap.

## Known limitations (see the report and `docs/chapter5_methods.md`)

Provisional stock scope; event-to-person assumption; no physician age (flat retirement rate); no
origin–destination or eligibility data (routes are proposals); Hamilton–Perry cannot separate
mortality from migration; M5 age effects extrapolate beyond training support after ~2030;
illustrative service weights are not WISN standards; population uncertainty calibrated on a single
backtest origin; budget feasibility not assessed (no cost data).
