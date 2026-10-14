# Chapter 5 — methods

A 15-year provincial physician projection, stock–flow and constrained allocation model.
Code: `src/chapter5/`; configuration: `config/chapter5.toml`; tests: `tests/test_chapter5.py`.
Every number in the Thai report is drawn from the claim registry (`outputs/chapter5/claims_*.csv`).

## 1. Scope and calendar

| Item | Setting |
|---|---|
| Baseline | 2025 (B.E. 2568) end-of-year MOPH physician headcount, Health Resource Report |
| Allocation years | 2026–2040 (B.E. 2569–2583), exactly 15 annual decisions |
| Geography | 76 provinces; Bangkok is an external boundary (population projection and flows) |
| Cadre | physicians, aggregate headcount (no grade/specialty, no FTE) |
| Managed stock | **provisional**: the MOPH-wide stock stands in for the OPS stock (no OPS-matched provincial stock exists; Chapter 4.4.2). Every plan is therefore an `exploratory_policy_scenario`. |
| Flows | HROPS recorded events, fiscal years; applied to calendar planning years (3-month offset recorded as an approximation). The exposure-convention sensitivity (same-year vs prior-year stock) is exported in `T5_FLOW_RATES`. |

## 2. Population

No official provincial projection, vital statistics or migration flows are in the repository.
The projection is a Hamilton–Perry cohort-change model on the DOPA civil register by single
year of age and sex (77 provinces incl. Bangkok):

$$P_{p,a+1,s,t+1}=CCR_{p,a,s}\,P_{p,a,s,t},\qquad P_{p,0,s,t+1}=CWR_{p,s}\,W_{p,15\text{–}49,t+1}$$

with an open group 101+ (the register's ">100"). A cohort-change ratio combines survival and
net migration; they cannot be separated with these data (exported components: births and the
combined change of existing cohorts). Internal migration is the provincial deviation from the
national ratio; migration scenarios scale its logarithm by 0.5/1/1.5. Each year the 77
provinces are raked to the national cohort projection by age and sex, so internal migration
nets to zero over the full system while the 76 allocation provinces need not balance.
CCRs pool 2013→2024 pairs; CWRs pool 2022–2025. The 2025 base reproduces the register exactly
(asserted).

Backtest: projecting 2019→2025 with information to 2019 gives a provincial MAPE of 1.1% vs
2.2% for no change and 2.6% for a linear trend in totals (`T5_POP_BACKTEST`).

Entitlement population = projected civil population × the province's NHSO/civil ratio (held at
2025; 2019–2025 min/max as bounds). The ratio is an administrative relationship, not extra
residents. M5 always uses the civil population it was fitted on.

## 3. Supply

* **Pool** (`supply.input_mode`): `available_appointments` (direct, 2,000/yr illustrative),
  `national_graduates` (A = G × licensing × participation × managed_share, non-overlapping
  factors) or `student_intake` (existing pipeline for the first 6 years, then intake × completion
  lagged 6 years). All three are exported in `T5_POOL_PATHS`; the plans use the direct mode.
* **Departures**: recorded exit events per opening-stock person-year FY2021–2025 by cause,
  pooled by gamma–Poisson empirical Bayes toward the health-region (resignation) or national
  (other causes) rate. Competing risks: $d_p = 1-\exp(-\sum_k h_{pk})$, cause share $h_k/\sum h$.
  Stated assumption: a recorded exit is a unique person leaving.
* **Re-entries** (reinstatement, transfer-in from other agencies): $r_p H_{p,t-1}$, separate
  from the pool. The recruitment event rate is not used by any optimised plan.
* Historical stock–flow residuals are audited (`T5_NATIONAL_STOCK_FLOW`, `T5_STOCK_FLOW_BACKTEST`)
  and never extrapolated as an attrition rate. No CAGR multiplier is applied anywhere; simulated
  growth emerges from the flows.

Stock identity (identical in the optimiser, ledger and simulator; closes to <1e-6):

$$H_{pt}=(1-d_p+r_p)H_{p,t-1}+x_{pt}+z^{in}_{pt}-z^{out}_{pt}$$

Within-year sequence: opening stock → projected context, expected departures and re-entries
on the opening stock → pool and caps → decisions → realised events (new appointees first
exposed next year) → services with annual-average exposure $(H_{t-1}+H_t)/2$ → lagged feedback.

## 4. Responsibility indices and targets

| Family | Raw burden | Dynamic through | Fixed |
|---|---|---|---|
| P | civil population | projection | – |
| P_ent | entitlement population | civil projection | NHSO/civil ratio |
| S | 10 min × OP visits + 90 min × AdjRW (illustrative weights) | population × benchmark rate | 2025 provincial rates (backtest-chosen) |
| N-STD | same weights × M5 standardized OP and AdjRW | population, age shares, recorded morbidity (fixed 2025 central) | economy, beds, physicians, nurses, year effect at the Chapter 4 reference (2023) |

Equivalent units use a fixed 2025 scale, $D_{pt}=P_{tot,2025}B_{pt}/\sum_p B_{p,2025}$.
Service benchmark: lowest backtest MAPE, but a non-persistence method needs ≥3 evaluated
cutoffs (AdjRW's trend "won" on only two cutoffs spanning the FY2023 grouper step, so
persistence is kept; `T5_SERVICE_BACKTEST`). IP days replace AdjRW in a sensitivity at equal
national baseline minutes.

Targets: reference 1 physician per 1,000 (illustrative; not WHO 4.45, which covers physicians,
nurses and midwives). **Experiment A** (`common_total`): $T_{pt}=k\,P_{tot,t}\,D_{pt}/\sum_q D_{qt}$.
**Experiment B** (`fixed_base_conversion`): $T_{pt}=k_m D_{pt}$ with $k_m$ fixed in 2025.

M5 safeguards: coefficients refitted with `chapter4.models` on the Chapter 4 sample and
checked against `T423_M5_COEFFICIENTS` (max difference 2e-16); year effect held at the
reference; positivity asserted; health covariates checked against training support each year
(`T5_M5_SUPPORT_BY_YEAR` — the elderly share leaves the training range for most provinces after
2030, so the N-STD age component is an extrapolation, reported with an age-held variant).

## 5. Resource-responsive services and N-FB

OLS M5 levels with actual resources turn non-positive for AdjRW under 2040 ageing (the N-FB
attempt with OLS levels is exported as `blocked_for_specific_reason`). The relative response
therefore uses the positive-mean (quasi-Poisson, log-link) M5 fitted on the same sample
(Chapter 4 out-of-fold R² 0.525 for AdjRW), **anchored** to validated levels:

$$V^{anch}_{k,pt}=V^{cf}_{k,pt}\,\exp\{\lambda\,\beta^{pos}_{k,phys}(\ln h^{plan}_{pt}-\ln h^{cf}_{pt})\}$$

with $V^{cf}$ the S benchmark and $h^{cf}$ the 2025 provincial density (the resource state behind
it), common to all plans; λ = 0, 0.5, 1 are associational-response sensitivities.

N-FB (lagged, within the need family):
$$D^{FB}_{pt}=scale_N\sum_k w_k V^{std}_{k,pt}\exp\{\lambda\sum_r\beta^{pos}_{k,r}(x_{r,pt}(H_{t-1})-x^*_r)\}$$
decision-year context with the previous year's physicians; the 2026 decision uses the observed
2025 stock. λ = 0 reproduces N-STD exactly (tested). Local elasticity
$\eta=\partial\ln D/\partial\ln H=\lambda\sum_k (w_kV_k/B)\beta_k$; target gain per extra
physician $\partial T/\partial H=\eta T/H$ (Experiment B) or $\eta(1-s)T/H$ (A). Physician
density relative to such a denominator moves like $H^{1-\eta}$: it improves when η<1, stalls at
η=1 and falls beyond; a gain ≥1 means one more physician raises the target by at least one.

## 6. Allocation (HiGHS MILP via `scipy.optimize.milp`)

Variables per province-year: integer appointments x ≥ floor, integer transfers z_in/z_out,
expected stock H, shortfall $s\ge 1-H/T$, epigraph $y\ge 2as-a^2$ (tangents every 0.025 over the
reachable range; error ≤ 0.00016 per term; checked with a 0.01 grid), unplaced u.
Constraints: stock identity, pool conservation, universal floor, gross-arrival cap
$x+z^{in}+rH_{t-1}\le gH_{t-1}$ or net-growth cap $H_t-H_{t-1}\le cH_{t-1}$, transfer cap
$z^{out}\le\tau(1-d)H_{t-1}$, national budget, balance (per region for the regional network),
origin protection $H_t\ge 0.95(1-d)H_{t-1}$ (new appointments may replace transfers) or
`surplus_only`: existing staff after transfers $(1-d)H_{t-1}+z^{in}-z^{out}\ge\min(T,(1-d)H_{t-1})$
(new appointments cannot backfill outward transfers, so a below-target province has no net outflow;
one binary per province-year).

Lexicographic order: (0) full placement (if infeasible, the minimum unplaced balance is a
separate diagnostic); (1) $J=\sum_t\sum_p (T/\sum T)s^2$, no discounting; (2) within 0.05% of J*,
the distribution imbalance $\sum_t\sum_p|H-(T/\sum T)\sum H|/\sum T$; (3) within tolerance, the
number of transfers. Stages 2–3 have a 60 s limit and report "incumbent retained" when they
cannot improve. Simultaneous in/out transfers of one province-year are netted exactly.
Every transfer plan receives its finished recruitment-only counterpart (same targets and
constraints, therefore feasible) as an incumbent: it is adopted when the transfer MILP does not
beat it within the time limit, and when it meets the stage-1 and stage-2 tolerances it is the
exact optimum of the transfer-minimisation stage (zero transfers). A transfer plan therefore
never reports a worse objective than recruitment-only, and transfers appear only when they
improve the shortfall or distribution criteria beyond the stated tolerance. Routes:
integer transportation problem on great-circle distances between province centroids.
Benchmarks: myopic greedy heuristic; finer tangent grid; deterministic rolling horizon; max-min
fairness then J; no-floor variants (cost of the universal floor).

Status quo: FY2021–2025 recruitment shares apportioned by largest remainder (evaluated
unconstrained) and the closest feasible allocation (min L1 distance) under current constraints.

Inverse feasibility (LP relaxation): minimum ramp-limited pool (≤10%/yr growth from 2,000) so
that every province, or the national total, reaches the reference by 2040; otherwise the
maximum attainable common attainment with and without the ramp.

## 7. Evaluation and uncertainty

Every plan is evaluated against P, P_ent, S and N-STD targets (both experiments) and under the
common resource-response mechanism: national attainment, bottom-quartile (19) attainment,
worst attainment, provinces meeting, national vs spatial gap
($G^{nat}=\max(\sum T-\sum H,0)$, $G^{sp}=\sum\max(T-H,0)-G^{nat}$), cumulative shortfall and J,
weighted Gini/Theil (between/within region)/P90–P10 from `chapter4.metrics`, regret, and
destination switches $\tfrac12\sum_p|x^m-x^n|$ (+ unplaced category). Practical-difference
criteria are fixed in the configuration before results: <5% of annual assignments switched,
<2% difference in cumulative shortfall under every denominator, no bottom-quartile province
losing >5% of its 2040 stock.

Uncertainty: 500 paired paths with gamma posterior draws of hazards (one per path), provincial
population errors calibrated on the backtest (random walk, σ ≈ 0.57%/yr plus a national
component), one M5 bootstrap coefficient draw per path, and common random numbers for the
binomial/Poisson event draws (quantile coupling). Fixed schedules use one recourse rule
(cancel farthest planned transfers that would breach realised origin protection; honour
appointments; record cap breaches, never repair them with unbudgeted recruitment). Adaptive
replanning (60 paths × 3 families) updates hazards (conjugate), rescales population and
re-solves the remaining horizon each year using information to the decision date only. A
perfect-foresight run on the same paths is reported as an optimistic bound only.

## 8. References

[S1] WHO (2010) Models and tools for health workforce planning and projections.
[S2] WHO (2021) Health labour market analysis guidebook.
[S3] WHO (2023) WISN user's manual, 2nd ed. — not applied: the 10/90-minute weights are
illustrative allocation weights, not activity standards.
[S4] UN DESA (2024) WPP 2024 methodology — cohort-component reference only.
Hamilton C.H., Perry J. (1962) A short method for projecting population by age from one
decennial census to another. *Social Forces* 41:163–170.
