# Chapter 4 — methods and limitations

## Formulas
* **CAGR** $g=(W_{t_1}/W_{t_0})^{1/(t_1-t_0)}-1$, elapsed intervals; undefined (NaN) for non-positive endpoints.
* **Ratio growth** $1+g_{W/P}=(1+g_W)/(1+g_P)$ (exact; verified to 1e−12).
* **Contribution to net change** $\Delta W_s/\sum_s\Delta W_s$ (negative and >100% values kept).
* **OP decomposition** $\ln V=\ln N+\ln(V/N)$ on one scope.
* **CMI** $\sum\text{SumAdjRW}/\sum\text{calculated cases}$; $\text{SumAdjRW}=\text{cases}\times\text{CMI}$ on the same records.
* **Time illustration** $H=(U_{OP}m_{OP}+A\,m_A)/60$; direct-care budget $=\text{days}\times\text{h/day}\times a$ applied once.
* **Predictive R²** $1-\sum(y-\hat y)^2/\sum(y-\bar y_{train})^2$ pooled over repeats and folds. Increment $100(SSE_a-SSE_b)/SSE_a$.
* **PPML** $\log E[V]=\log P+\alpha(+\alpha_p)+\delta_t+\theta'\log(\text{supply}/P)+\dots$; 10% effect $100(1.1^\beta-1)$.
* **Standardization** $\hat r^*=f_{M5}(s,d,GPP^*,b^*,m^*,n^*,t^*)$, $V^*=P\hat r^*$, $E=V^*/\bar r_{2023}$ with $\bar r_{2023}$ fixed.
* **Age mixture** $r_{pt}=q_t\sum_a s_{pta}\rho_a$, $\rho\ge0$, $q_{t_0}=1$; $w_a=\rho_a/\bar\rho_{2013}$.
* **Weighted Gini**, **Theil T** $\sum q\log(q/d)$ with $T=T_B+T_W$, $T_W=\sum_g Q_gT_g$.
* **Beta convergence** $\frac1T\ln(r_{t_1}/r_{t_0})=a+\beta\ln r_{t_0}$, HC3 intervals.
* **Priority** $R_p=(W_p/D_p)/(\sum W/\sum D)$; gap $\sum W\,D_p/\sum D-W_p$ (relative to the proportional rule only).
* **Stock–flow** $W_t-W_{t-1}=I_t-O_t+A_t$.

## Uncertainty
* Descriptive indices on complete recorded totals carry no sampling interval.
* CV increments: province-cluster bootstrap conditional on fitted CV predictions (no refitting).
* M5 standardized indices and province E: province bootstrap with refitting (500/500 valid), reference held fixed — conditional model uncertainty only.
* Regression coefficients: province-clustered (CR1) intervals with t(G−1).

## Limitations that change interpretation
1. Headcount, not FTE; stock, not individual flows (4.1–4.3).
2. MOPH-wide workforce is broader than the MOPH hospitals whose services form the numerator; service/staff ratios are team output divided by headcount.
3. HDC prevalence is diagnosed prevalence in service records; it reflects diagnosis access and reporting. Against modeled BOD 2022 burden its provincial rank correlation is near zero for diabetes and hypertension (4.5).
11. BOD 2022 burden is a modeled, single-year estimate (possibly informed by service data); it measures the size of the health problem, not staff required. The age-specific file (S15) lets expected burden follow ageing, but only under province age-specific rates fixed at 2022; it is a demographic projection, not an observed disease trend.
4. Case-mix weights changed with a grouping/coding step in FY2023 (+12.4% CMI in one year); no DRG version metadata.
5. The data identify supply–service **associations**, not supplier-induced demand; no instrument, allocation discontinuity, payment change or referral data exist in the project.
6. Age-specific relative rates cannot be estimated stably from provincial aggregates; age denominators in 4.3 are declared scenarios.
7. Province-level data cannot identify within-province inequality.
8. No OPS-matched stock exists; the stock–flow residual mixes scope, timing, reporting and reclassification. Events are not unique persons; employment-status conversion appears as entry + exit.
9. Workload–flow associations are not robust to relaxing the unit-exposure (offset) assumption; they are not causal responses.
10. Scenarios (4.2.1, 4.3) are conditional arithmetic, not forecasts; redistribution scenarios ignore transfer, attrition, minimum-service and capacity constraints.

## Quality gates (status)
| Area | Status |
|---|---|
| Sources unchanged; provenance registered | pass (hashes in `outputs/shared/source_inventory.csv`) |
| Join cardinality | pass (all panel joins one-to-one; `outputs/shared/join_audit.csv`) |
| Sector/total reconciliation | pass (max gap 0) |
| Service nesting | pass nationally; 13 province-year anomalies exported |
| CAGR elapsed intervals; exact-year lags | pass |
| Professional vs technical nurses | pass |
| CMI ratio-of-sums | pass |
| M0–M5 common sample/folds; M4 beds, M5 + physicians + nurses | pass |
| R² definition stated; no province leakage | pass |
| Standardization positivity, support, bootstrap | pass (all three outcomes) |
| Age weights gate | fail for all outcomes → scenarios used (documented result) |
| Theil identity | pass (1e−12) |
| Scenario validation (growth-only keeps Gini) | pass |
| Workbook totals | defects found and documented; component sums used |
| Clean re-execution of four notebooks | pass (`python -m chapter4.build --section …`) |
| DOCX visual inspection | structural check only (headings, 21 figures, captions); rendering in Word not completed in this session |
