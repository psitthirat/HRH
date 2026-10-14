# Chapter 4 — analytical decisions

Decisions that change a number, recorded with the reason. Numeric consequences are in
`docs/reconciliation_log.csv`; configuration values are in `config/analysis.toml`.

## Sources and scopes
| # | Decision | Reason |
|---|---|---|
| D1 | Raw files stay at their existing `data/` paths; `config/source_registry.toml` is the single path list. | Other projects in the repo (hrh.ipynb, scripts/, web tools) read the same files. |
| D2 | **All of Chapter 4 (author decision, 26 Sep 2026; config `cadres.nurse_includes_technical`):** nurses = professional + technical nurses, combined per province × year × sector in `panels.workforce_long()`; technical nurses are published separately only 2013–2021 and counted as zero afterwards. Source categories remain available with `raw=True` (used for the published-total reconciliation). HROPS events cover professional nurses only, which widens the nurse stock–flow residual in 4.4. | In 2022 professional nurses rose 5,331 but the combined series only 1,238, consistent with former technical nurses being counted as professional from 2022; the combined series is more continuous (T41_NURSE_COMBINATION). |
| D3 | Sectors are disjoint: MOPH / other public (other ministries, state enterprises, independent bodies, local government) / private / unclassified ("Other", 2016–2018 only). Published totals are used only to reconcile (max gap 0). | No double counting. |
| D4 | `moph_service` = regional + general + community hospitals (report tables 5–7). Health-promoting hospitals excluded. | Task definition; nesting inside table 4 verified nationally every year (13 province-year anomalies exported, not edited). |
| D5 | MOPH-wide workforce is *not* relabelled as OPS hospital staff. Service-per-staff ratios use MOPH workforce ÷ MOPH hospital services in the same 76 provinces and are labelled descriptive proxies. | Bangkok has MOPH staff but no RH/GH/CH service block; the workforce universe is broader than the hospitals. |
| D6 | Case-mix CMI = ΣSumAdjRW / Σcalculated cases (ratio of sums). Hospital-level identity verified (max gap 5×10⁻⁵ from 4-d.p. rounding). | Task requirement. |
| D7 | Facility-level staff file (GIS Health) rejected as an OPS-matched stock. | Coverage breaks (physicians +37% in 2016; nurses +39% in 2023, −17% in 2024) and a current-snapshot facility registry. |
| D8 | Entitlement register uses December rows; persons without a valid province are kept nationally, excluded provincially. | Register structure. |

## Geography and time
| # | Decision | Reason |
|---|---|---|
| D9 | National series (4.1, 4.2.1) include Bangkok; provincial models, inequality, and flows use 76 provinces with Bangkok removed before sampling. `outputs/shared/national_76_bridge.csv` explains the difference. | Task. |
| D10 | Case-mix fiscal year t is paired with report/calendar year t; GPP enters as calendar year t−1 by exact-year join. | Available data; the pairing is an approximation, stated. |
| D11 | Flow analysis uses FY2017–FY2025; FY2026 (extracted 5 Mar 2026; retirements projected) excluded. | Partial year. |

## Models (4.2.3)
| # | Decision | Reason |
|---|---|---|
| D12 | M0 year dummies; M1 + shares 0–14 and 60+ (15–59 omitted); M2 + six HDC prevalences (percent); M3 + log GPP(t−1); M4 + log beds per 1,000 (MOPH hospital beds; case-mix beds for AdjRW); M5 + log MOPH physicians and professional nurses per 100,000. | Agreed sequence. |
| D13 | Common sample: 302 province-years (76 provinces, 2022–2025) complete for all M5 covariates **and** all three outcomes. | Same rows across models and outcomes. |
| D14 | Province-grouped 5-fold CV × 10 repeats, seed 20260924, folds built over provinces sorted by code. R²_pred uses the training-fold mean. | Stable key; the previous name-sorted folds are reproduced as a check. |
| D15 | Paired SSE reductions with province-cluster bootstrap (4,000 draws), conditional on the CV fits. | Repeats of one province are not independent. |
| D16 | Temporal validation: test 2025 (and 2024); trend or last-year-effect rule applied to every model; conditional-retrospective and forward information sets; persistence baseline. | Year dummies cannot be estimated for an unseen year. |
| D17 | Supply associations: PPML on totals with log-population offset, province-clustered t(G−1) intervals, pooled vs province FE, long (2013–2025; AdjRW 2018–2025) vs short morbidity panel, joint vs reduced, lagged supply. | Task 7.5. |
| D18 | Standardization: full M5 OLS fit; reference = 76-province pooled 2023 values (pooled densities then log; population-weighted GPP level of 2022 then log); reference and 2023 normalization fixed for all years; province bootstrap with refitting (500). | Task 7.6; the reference passes marginal and joint support. |
| D19 | Age-weight gate fixed before estimation: share at zero bound ≤ 0.25; 60+ bootstrap ratio ≤ 3; 3- vs 6-group 60+ weight ratio ≤ 3; same weight ordering across service universes. All three outcomes fail → age denominators in 4.3 use declared scenarios (moderate 60+ = 2×, steep 3×). | Task 7.7. |

## Distribution (4.3)
| # | Decision | Reason |
|---|---|---|
| D20 | Primary indices weighted by the denominator; equal-province Gini as sensitivity; Theil within-region term weighted by regional workforce shares (identity verified to 1e−12). | Task 9.1. |
| D21 | Service and M5 denominators are paired only with MOPH workforce; dentists and pharmacists use HDC dental visits / OP prescriptions (screened). | Matched scope; physician weights are not reused for other professions. |
| D22 | Priority = lowest 19 of 76 by R_p; ties by province code; ±2% near-cutoff flag; M5 membership probability from the 4.2 bootstrap draws. | Task 9.4. |
| D23 | Near-equality criterion (illustrative): weighted Gini ≤ 0.10 and P90/P10 ≤ 1.5; λ = 0.10; horizon 20 years; population shares fixed at 2025. | Declared policy choice. |

## Flows (4.4)
| # | Decision | Reason |
|---|---|---|
| D24 | Parser reads merged multi-row headers per sheet; component sums replace defective published totals; blanks treated as zero events only because every row reconciles with its published subtotals. | Workbook audit. |
| D25 | Stock–flow identity uses the broader MOPH stock (report year) → reconciliation diagnostic only. | No OPS-matched stock exists. |
| D26 | Primary workload model: PPML, offset log W(t−1), province + year FE, log GPP(t−1), clustered by province; all-zero provinces dropped per outcome. Sensitivities: free log-stock term, AdjRW on the same sample, excluding FY2020–2022, dropping the most influential province. | Pre-specified; free-stock variant reported beside the primary. |

## Scope of catching-up analyses (author decision, 27 Sep 2026)
| # | Decision | Reason |
|---|---|---|
| D27 | Baseline-quartile gains, beta/sigma convergence and the 20-year scenarios (4.3.2–4.3.3) use MOPH staff only (`CONV_SCOPES = ["moph"]` in notebook 4.3). Scenario aggregate growth = CAGR 2013–2025 of MOPH staff in the 76 provinces. Inequality indices (4.3.1) and priority lists (4.3.4) keep their existing scopes. | The question is whether MOPH allocation lets low-density provinces catch up; private and other-public growth is not governed by the same allocation rules. |

## Burden of disease (4.5, author request 14 Oct 2026)
| # | Decision | Reason |
|---|---|---|
| D28 | BOD 2022 enters as a time-invariant province attribute (one observed year); age-standardized rates are summed over Level-3 causes within a province only, never across provinces. | Source definitions: one standard population per province; provincial ASRs do not add to a national ASR. |
| D29 | Planning indices exclude COVID-19 (B5); the all-cause index is the sensitivity. | 2022 is a COVID break year in this project; a 15-year plan needs the structural burden. |
| D30 | HDC–BOD pairs: DM–O1, HT–I4 (hypertensive heart disease, nearest cause; hypertension is a risk factor), CKD 3–5–O2, COPD–J1, stroke–I3, CHD–I2; YLD is the primary comparator. | Closest cause-level matches; YLD is nearest to living with the condition. |
| D31 | Burden models reuse the 4.2.3 common sample and folds; the notebook asserts identical folds and exact reproduction of the published M1/M2/M5 R². | Paired, comparable increments. |
| D32 | Burden-weighted denominators: population × relative ASR (bod_pop, excess burden only), expected DALY and YLD at the 2022 province age-specific rates × each year's age groups (bod_count, bod_yld_count; replaced the earlier age-scenario × ASR proxy once S15 arrived), and an all-cause ASR variant. Concentration index of density ranked by ASR burden, population-weighted, bootstrap over provinces. | Excess-need (ASR) and total-burden (counts) answer different questions; both are reported. |
| D33 | Data fingerprint of a source that lists `files` in a shared folder hashes those files only (`config.source_fingerprint`). | Adding the BOD workbook to data/epi had invalidated the HDC source and every downstream cache. |
| D34 | Age-specific BOD rates (S15) held at 2022 and applied to each year's population by 8 age groups give expected DALY/YLD (panel 2013–2025; Chapter 5 projections). Crude-vs-national burden is decomposed exactly into age structure × excess (indirect standardization on the 76-province rates). | Only one subnational year exists; national totals for other years cannot change provincial shares under a common national target. |
| D35 | No feedback from allocated physicians to burden. | A single cross-section cannot identify the effect of physicians on DALYs (density is confounded with income); a need target that falls when health improves would penalise improving provinces. |
