# Re-check of the final-check fixes (independent agent, 15 Oct 2026)

## Scope

I re-checked every item marked as fixed in `docs/final_check.md` against the 15 Oct rebuild. The Chapter 5 run manifests carry code hash `74b92e180efd5592`, which equals the current `src/chapter5`. Numbers were recomputed from tables, not from `claims*.csv`. The sources were:
- `outputs/chapter5/tables` and `validation`, including `T5_PLAN_INDEX`, `T5_CROSS_EVALUATION_LONG`, `T5_PRACTICAL_DIFFERENCES`, `T5_FEEDBACK_LOG/CONVERGENCE`, `T5_UNCERTAINTY_SUMMARY`, `T5_SENSITIVITY_SUMMARY`, `T5_HEALTH_GAIN_SUMMARY` and `T5_HINDCAST_METRICS`;
- `plans/chapter5_provincial_annual_plans_all.parquet` and `chapter5_simulation_paths_adaptive.parquet`;
- `outputs/chapter4_*/tables`.

I read the whole Chapter 5 report for statements that the change from 90 to 100 min/AdjRW may have invalidated. I also reviewed:
- the diffs of `allocation.py`, `analysis.py`, `validation.py` and both templates;
- the two figures that carry labels (F43, F56), plus the F53 and F5A_UNCERTAINTY SVG text;
- notebook health (all 9 notebooks have monotonic execution, no errors and no glyph warnings);
- the plan workbook;
- the rendering: both reports equal their templates re-rendered from the current claims files.

I did not rerun the pipeline or the tests. The only file I modified is this one.

## Fix verification

| ID | Verdict | Evidence |
|---|---|---|
| C-1 | fixed | `analysis.py:362` base set now includes B-R/B-RT. Recomputed from `T5_CROSS_EVALUATION_LONG.cumulative_j` (best: P→P-R, S→S-R, N→N-R, B→B-R). Regret under B: P-R 0.931%, S-R 2.067%, N-R 0.727%, B-R 0. Max regret across P/S/N/B: N-R 1.142 < P-R 1.325 < B-R 1.347 < S-R 2.067, so N-R is still minimax. Report lines 96 and 174 and Table 5.8 match. Residual for the Pent criterion: see N-9. |
| C-2 | partly fixed | Report line 152 is correct against `T5_FEEDBACK_LOG` (NFB1-R, 2026): eta 0.337, mean gain 0.880, 12 provinces ≥1, max 1.430; 15-year max 1.476. But `T5_FEEDBACK_ELASTICITY_2026` (shown in notebook 5.1 and titled "การตัดสินใจปี 2569") still gives different 2026 values for λ=1: mean 0.928, 22 provinces ≥1, max 1.483. See N-7. |
| M-1 | fixed | `T421_SCOPE_VS_DENOMINATOR` nhso_rights: 68.445 vs 71.114 = −3.753%. Table 4.1 shows 68.45 and −3.8%. Text lines 86 and 88 both give 3.75/3.8, the same for every cadre and scope. |
| M-2 | fixed | Ch4 lines 16 and 34 explain the private-dentist reporting break and give public-sector rates (dentists 3.07% vs nurses 2.78%). |
| M-3 | fixed | Shapley scope is stated (line 238). MOPH physicians −0.0070/+0.0007; all-sector physicians −0.0050/−0.0118, pharmacists −0.0054/−0.0066, dentists +0.0031 (`T43_DENOMINATOR_INEQUALITY_CHANGE`). The Gini-minimum claims match `T43_INEQUALITY_ANNUAL` (0.221 in 2562, 0.125 in 2561, 0.162 in 2561). The conclusion (line 348) mentions the reversal. A wording caveat for physicians is in N-10. |
| M-4 | fixed | `chapter5.toml`: `adjrw_minutes = 100`; the grid is 5/15 OP at 100 and 60/90/120 AdjRW. The plans parquet `weight_ip_min` is 100 for P-R/S-R/N-R/B-R and 90 only for `*|w10_90`. The T52 source reads "ค่าหลักของบทที่ 4 (4.2.2)". |
| M-5 | fixed for the stated item | N-RT = N-R: objective 4.340057 for both, same imbalance, 0 transfers, 0 switches (`T5_PRACTICAL_DIFFERENCES`). P-RT/S-RT/B-RT/Pent-RT also equal their R plans. The incumbent cannot make a plan infeasible: zero transfers satisfy every transfer-related row, `r_counterpart` keeps the same cap mode and targets, and `all_constraints_ok` is True for every RT plan. The same symptom persists in several RT variants, and the "never worse" guarantee in the code comment and the methods doc does not hold. See N-2. |
| M-6 | fixed, with caveats | Noise pairs (dJ ≤ 0.05%, switches > 0): P-R vs greedy 4.73%/42; vs tangent_fine 4.64%/40; P-RT vs P-RT\|tau0.05 9.86%/52; N-RT vs N-RT\|tau0.05 9.36%/70. That gives "9.9%" and "70" (line 166). P–S 425, P–B 256, P–N 85 are all above 70. Pair selection and wording issues are in N-4. |
| M-7 | fixed | `T5_HINDCAST_METRICS`, h=3, MAE model vs persistence: 2020 28.8 vs 40.9; 2021 30.4 vs 27.2 (lost); 2022 25.0 vs 31.8. With origin 2020 removed the model still wins (27.7 vs 29.5), so the main session's rebuttal of the agent is correct. Bias +4.1%, coverage 0.41 at h=3, Jaccard 0.59 vs 0.72, all as reported. |
| M-8 | fixed | Line 112 now frames the finding as conditional on the assumed cap and gives recorded intake (21.2/yr = 106 events / 5 yr; 29% of 72). Conclusion 4 is reworded. The cap figure "7" has a precision issue: see N-8. |
| M-9 | partly fixed | Report text, table headers (T53, T56) and `FAM_LABEL` are fixed, and no "ความจำเป็นอ้างอิง" remains in either report or in any Ch5 table. The old label survives in reader-facing outputs: see N-1. |
| M-10 | fixed | Ch4 lines 270 and 348–352 describe observed patterns and say the concentration-index intervals overlap. |
| M-11 | fixed | `T46_SPECIALIST_CONCENTRATION`: all-sector top-10% 61.55 (2021) → 63.50 (2024), Gini 0.742 → 0.754; MOPH community share 15.6 → 17.8, regional/general 73.3 → 72.2. The co-movement over 2021→2024, recomputed with Spearman from `T46_CENTRE_COMMUNITY_COMOVEMENT`: ρ = +0.128, p = 0.274, n = 75. |
| M-12 | fixed | `validation.py:57` uses `last_year_effect` (AdjRW 2025 0.670, the same as Ch4). C5-SVC is labelled "best alternative, not adopted". The Thai table has the column "แบบจำลองที่ทดสอบ". |
| A1/m-1, A2 | fixed | I viewed F43_CONVERGENCE_SCENARIOS.png: Thai text labels, no missing glyphs, translated legend, and the overlap is drawn (thick line under dashed) and labelled. |
| A3 | fixed | Line 124 says the 60 region transfers come from a near-indeterminate secondary stage and are not to be used as a conclusion. |
| A4 | no fix needed (agreed) | The principal RT plans now equal their R plans. |
| A5/m-2 | fixed | No CE fiscal years remain in notebook 4.4 or the Ch4 prose ("ปีงบ 2560–2568"). |
| A6 | fixed | No `.sum(1)` in notebook 4.5. |
| A7/m-19 | fixed | The Ch5 notebooks were executed 15 Oct 02:21; no errors; they contain B-R and current objectives (S-R 4.297020). Note: they still have no health-gain or hindcast cells. |
| A8 | fixed | Ch4 figures 4.1–4.31 and tables 4.1–4.17 are sequential; no stale bare numbers. |
| A9 | fixed | "ค.ศ. 2016 (พ.ศ. 2559)" (Ch4 line 76). |
| A10/m-18 | fixed | `methods_and_limitations.md` states 240 s and numbers the limitations 1–13. But it repeats two guarantees the data contradict (lines 98–99 and 118): see N-2 and N-5. |
| m-3 | fixed | "(รวมกรุงเทพฯ)" and the 76-province note in 4.2.3. |
| m-4 | fixed | Line 156: 20.2% vs NFB0-R 18.1% (vs N-R 17.9%), means over the period, no "ในทุกปี" (`T5_FEEDBACK_CONVERGENCE`). |
| m-5 | partly fixed | The text now calls foresight a bound on J only and states the trade-off (S 0.406 vs 0.412; N 0.384 vs 0.387). But foresight is not a bound on J either in this output: see N-5. |
| m-6 | fixed | "486 เส้น" matches `n_valid` for criterion N. |
| m-7 | fixed | "รับเข้าในตำแหน่งข้าราชการ (รวมการรับโอนและการบรรจุกลับ) 12,254". |
| m-8 | partly fixed | No "ร่างก่อนหน้า/ร่างเดิม" remains in either report, but "ผู้เขียน" remains in Ch5 and T52: see N-6. |
| m-9 | fixed | "M5 มีความคลาดเคลื่อนสูงกว่าร้อยละ 10.17". |
| m-10 | fixed | Appendix tables are ก1, ข1, ค1. |
| m-11 | fixed | "(AdjRW พ.ศ. 2561–2568)". |
| m-12 | fixed | Scope stated in line 136. |
| m-13 | fixed | "ประชากรถ่วงภาระส่วนเกิน" is named and its range explained (line 268). |
| m-14 | fixed (documented) | `hindcast.py` docstring and `decisions.md:109`. |
| m-15 | fixed | Line 156 adds the cross-sectional vs within-province sentence. |
| m-16 | fixed | Line 33 (+1.10% national total). |
| m-17 | fixed | `T5_PLAN_INDEX`: 7 plans with `incumbent_adopted` (P-RT, S-RT, S-RT\|B, B-RT, S-RT\|net, S-RT\|tau0.05, P-RT\|net\|surplus), all with 0 transfers. Largest gap 1.838% (S-RT\|tau0.05); non-incumbent maximum 0.471% (P-R\|pool1500). |
| m-20 | fixed | 1,469 positions (L1 2,938). |

## New or remaining problems

| ID | Severity | Location | What is wrong | Evidence | Suggested fix |
|---|---|---|---|---|---|
| N-1 | major | `src/chapter5/figures.py:24` → Fig. 5.3 (F53_ANNUAL_ALLOCATIONS legend) and Fig. 5.9 (F5A_UNCERTAINTY panel titles); `src/chapter5/workbook.py:52` → `chapter5_annual_allocation_plans.xlsx` sheet `metadata`; `notebooks/chapter5_3…ipynb` cell 0 | The M5 standardized quantity is still labelled "ความจำเป็นอ้างอิง M5 (N-STD)" in two report figures, the plan workbook and the notebook intro. This is residual M-9. | The string appears in `F53_ANNUAL_ALLOCATIONS.svg` and `F5A_UNCERTAINTY.svg` (generated 15 Oct 02:21 by the current code), and in workbook metadata: "P/S/N = ประชากร/บริการ/ความจำเป็นอ้างอิง M5". | Change `TH["N"]` and the workbook legend to "บริการคาดหมายมาตรฐาน M5 (N-STD)", fix the notebook markdown, and regenerate figures and workbook (no re-solve needed). |
| N-2 | major | Ch5 line 124; Table 5.5 (`T54_TRANSFER_AND_CAPACITY`); `allocation.py:548-561` (comment at :551); `methods_and_limitations.md:98-99` | Zero-transfer RT variants still differ from their R plans, the same symptom as M-5. (a) The text says widening transfers to 5% "ผลก็ไม่เปลี่ยน (0 ครั้ง)". Yet P-RT\|tau0.05 changes 9.9% of destinations per year, and Table 5.5 shows cap binding 71.8% vs 63.3% and floor-only 8.5% vs 1.1%. (b) S-RT\|net has 0 transfers but J +0.062% vs S-R\|net. That is above the declared 0.05% tolerance, and readers will attribute it to transfers. (c) The code comment ("a transfer plan is then never worse than its recruitment-only plan") and the docs ("แผน RT จึงไม่แย่กว่าแผน R"; "J … ไม่เกิน 0.05%") do not hold. | Exact objectives (`T5_PLAN_INDEX`):<br>- S-R\|net 4.258126 vs S-RT\|net 4.260748, 0 transfers; imbalance 0.451 vs 0.337; destinations differ 10.8%/yr (recomputed from the parquet).<br>- N-RT\|net +0.025% (298 transfers); B-RT\|net +0.021% with 1 transfer and 14.0%/yr switches.<br>- P-RT\|tau0.05 and N-RT\|tau0.05: 0 transfers, 9.9%/9.4%/yr switches.<br>Mechanism, from the stage outcomes: S-R\|net's distribution stage hit the time limit, so the zero-transfer solution found by S-RT\|net dominates it on imbalance. The shortfall tolerance is applied to the tangent J and relative to J1, and J1 is the R plan's post-distribution J after stage-1 adoption. In the tau0.05 plans the incumbent fails the J test because RT's stage-1 J1 is lower. | Re-solve the R variants with the better zero-transfer solution as an incumbent, or report the J comparison between plans with ≥1 transfer only. Reword line 124 to "the number of transfers stays 0, but the recruitment plan differs within the tolerance". Fix the comment and the doc guarantee (state that the tolerance is on the tangent objective). |
| N-3 | major | Ch5 line 220, point (1); claim `c54_swmax_PR_vs_SR` | "หลักคิด … ทำให้แพทย์ใหม่เปลี่ยนปลายทางได้ถึงร้อยละ 12.1 ต่อปี" understates the effect of the principle and contradicts 5.6. After AdjRW = 100, the P–S maximum fell (15.3 → 12.05), but S–N and S–B reach 18.1% in one year. Solver indeterminacy alone reaches 17.4% in a year and 9.9% on average, so annual switching is no longer a valid measure of the principle effect by the chapter's own argument. | `T5_PRACTICAL_DIFFERENCES` `max_annual_switched_pct`: P–S 12.05, S–N 18.10, S–B 18.10, P-RT vs P-RT\|tau0.05 17.40. Recomputed from the parquet. | Express (1) by the cumulative measure (e.g., "จำนวนรับสะสมของจังหวัดเดียวต่างกันได้ถึง 425 คน"), or give the maximum over all principle pairs with the indeterminacy caveat. |
| N-4 | minor | Ch5 line 166; `analysis.py:392-396, 440` | Noise-benchmark selection and wording:<br>(a) Rolling (dJ 0.069%) is excluded, though the same sentence presents it as a near-optimal re-solve "ต่างกันไม่ถึงร้อยละ 0.1"; with it, the cumulative benchmark would be 75, not 70. The P–N verdict still holds (85).<br>(b) "(4 คู่)" is called "คู่แผนอื่น", but 2 of the 4 are the greedy/tangent re-solves just cited.<br>(c) The two pairs that set the benchmark (P-RT\|tau0.05, N-RT\|tau0.05) are shortfall-stage solutions whose distribution stage timed out, so the benchmark is an upper bound on tie-breaking indeterminacy (conservative), which is not said.<br>(d) "ผลตัดสินรายปีที่ใกล้เกณฑ์" understates: P–S 9.0, P–B 8.5, N–B 6.6 and P–N 5.8 are all below 9.9 (`exceeds_indeterminacy_annual` False). Only S–N and S–B are above.<br>(e) Fig. 5.6 panel ก shows only the 5% line, not the indeterminacy level. | `T5_PRACTICAL_DIFFERENCES` rows 16–18, 37, 39; `T5_PLAN_INDEX.stage_outcomes`. | Include rolling or justify its exclusion; reword "คู่แผนอื่น" and "ใกล้เกณฑ์" ("ผลตัดสินรายปีของทุกคู่หลัก ยกเว้น S–N และ S–B, อยู่ในระดับความไม่เป็นเอกลักษณ์"); state that the benchmark is conservative; add the 9.9% line to Fig. 5.6. |
| N-5 | minor | Ch5 line 202; `methods_and_limitations.md:118`; Fig. 5.9 x-label "รู้อนาคต (ขอบเขต)" | Perfect foresight is not even a bound on J in these outputs. Adaptive replanning attains a lower J than foresight on the same path in 30/60 P-R paths (S: 20/60; N: 25/60), by up to 0.19%. For P-R the mean adaptive J (4.32687) is below the foresight mean (4.32692), so "ลด J ลงเกือบเท่าขอบเขตนี้" is literally wrong. | `chapter5_simulation_paths_adaptive.parquet`, own criterion, path-by-path difference adaptive − foresight. Cause to confirm (likely MIP gap or time limits in the foresight solves). | Call it a "reference (near-bound, subject to solver gap)" or re-solve foresight tighter; drop "(ขอบเขต)" from the figure label. |
| N-6 | minor | Ch5 lines 45, 51, 118, 156; `T52_BASELINE_AND_ASSUMPTIONS` (column "แหล่ง": "ตัวอย่างของผู้เขียน" ×3, "ผู้เขียน"; generated at `analysis.py` ~634) | m-8 residual: final_check says all "ผู้เขียน" phrasing was removed or rewritten; 4 sentences and 4 table cells remain. | grep of the rendered report and T52. | Use "ค่าตัวอย่างของการศึกษา" / "คณะผู้วิจัย" (the Ch4 usage) or remove. |
| N-7 | minor | `T5_FEEDBACK_ELASTICITY_2026` (shown in notebook 5.1 cell 17) vs Ch5 line 152 | C-2 residual: two published 2026 versions of "gain per added physician" disagree (12 vs 22 provinces ≥1). | λ=1, ELASTICITY table: mean 0.928, 22 ≥1, max 1.483. `T5_FEEDBACK_LOG` 2026: 0.880, 12, 1.430. | Align the definitions (Experiment A, the same weighting) or relabel the table. |
| N-8 | minor | Ch5 line 112; claim `c54_worst_province_cap_n` (`analysis.py:923`) | "เพดานในแบบจำลองราว 7 คนต่อปี" is 10% × the 2025 stock (7.2). The model's actual new-appointment limit for Bueng Kan is 6 in 2569 and falls to 3 by 2583: the cap is applied to each year's opening stock and expected re-entries count against it. The Thai phrase can also be read as "higher than the cap by ~7". The direction of the finding holds. | Plans parquet, P-R, บึงกาฬ: `cap_value` 6,6,6,6,5,5,5,5,4,…,3,3; allocations equal. | "เพดานในแบบจำลองให้รับใหม่ได้ 6 คนในปี 2569 และลดเหลือ 3 คนในปี 2583". |
| N-9 | minor | Table 5.8 column "ประชากรทะเบียนสิทธิ"; `analysis.py:362` | The C-1 pattern remains for the Pent criterion. Pent-R (a comparable Experiment-A gross-arrival plan) is outside the base set, so its own-criterion regret is negative and the Pent column's regrets are measured against P-R. | `T5_CROSS_EVALUATION_LONG`: Pent-R under Pent −0.086% (P-R 4.34780 vs Pent-R 4.34408). Effect ≈0.09 pp, minimax unchanged (Pent-R max 1.35). | Add Pent-R/Pent-RT to `base_set`. |
| N-10 | minor (to confirm) | Ch4 line 230 ("ต่ำสุดในปี 2562 … แล้วกลับสูงขึ้นจนถึงปี 2568") and conclusion line 348 | For all-sector physicians the "rise since 2019" is a single jump in 2020 (0.221 → 0.246), followed by a decline to 0.235. 2020 is the year Ch5 identifies as an HRR definition break ("จุดเปลี่ยนนิยาม…ปี 2563"). For pharmacists and dentists the rise is more sustained (dentists 0.179 → 0.197 in 2025). | `T43_INEQUALITY_ANNUAL` (population, gini_weighted), physicians all_sectors 2019–2025: 0.221, 0.246, 0.239, 0.232, 0.241, 0.237, 0.235. | Say "สูงขึ้นในปี 2563 (ปีที่นิยามรายงานเปลี่ยน) แล้วทรงตัว/ลดลงเล็กน้อย" for physicians, or confirm that the 2020 jump is real. |
| N-11 | minor | Ch5 line 208 | "ส่วนที่เปลี่ยนน้อย … ราวร้อยละ 1–6 ต่อปี" includes the inpatient-days proxy, which moves S-R destinations 6.8%/yr (N-R\|w10_90 0.6%). | `T5_SENSITIVITY_SUMMARY.mean_annual_switch_pct_vs_base`: S-R\|ipdays 6.76. | "ราวร้อยละ 1–7". |
| N-12 | minor (latent) | `allocation.py:525-561` | Incumbent adoption at both the shortfall and the distribution stage checks only the shortfall objective. `full_vector` leaves the maximin variable at 0, so an RT plan with a maximin first stage could adopt an R incumbent that violates the RT maximin floor. No current plan is affected (no RT maximin job in the catalogue). | Code reading: `full_vector` never sets `mm`; adoption tests `cS @ vi` only. | Check `extra` rows (maximin) before adopting, or skip adoption when `pb.stages[0] == "maximin"`. |
| N-13 | minor | `T5A_VALIDATION_SUMMARY` and `T46_VALIDATION_SUMMARY` (Thai appendix tables) | The new "แบบจำลองที่ทดสอบ" column (and the evidence, comparator and limitation columns) are in English inside Thai tables. | Table contents. | Translate, or note that technical labels are kept in English. |

## Checked and found correct

- **Ch5 5.2–5.3 numbers**
  - Index changes: −6.6 / −7.25 / −6.7 / +16.4 (`T5_INDICES`, 2025→2040).
  - First-year statements: P-R Nakhon Ratchasima 82; floor provinces 3 / 1 / 2 / 2 (P/S/N/B). B-R top three 82/78/77; these are cap-bound and identical in all four plans.
  - 15-year differences: S−P +275/+198/+177 and −425/−230/−227; N−P +85/+75/+49 and −71/−63/−60; B−P +165/+138/+102 and −256/−201/−173. The hard-coded "ปทุมธานี นนทบุรี นราธิวาส" still matches the three largest S-R losses.
  - Switches: P–S 180.2 / 9.01% / 12.05 / 2,703; P–N 116.6 / 5.83; S–N 205.6 / 10.28; P–B 8.50 / 12.35; S–B 11.44; N–B 6.57; P–SQ-C 14.81; yld 5.81; asr 7.57; net cap 19.99.
- **Ch5 5.3–5.4 outcomes**
  - B under B: 0.409 / 0.392 / 0.377 / 0.397; Gini 0.071 / 0.112 / 0.131; B-R under P 0.124.
  - B-R\|B: 30,012 and 0.435 vs 0.541.
  - P-R: 30,011, 0.542, gap 25,396.
  - Gini under P: 0.083 / 0.094 / 0.139 / 0.182; bottom quartile 0.377 / 0.377 / 0.351 / 0.314; Bueng Kan 0.0986 in all principal plans, 72→37.1.
  - Net cap: 0.535 / 0.001 / 0.537; cap binding 63.3% / 10.0%.
  - Transfer counts and dJ: 545 / 0 / 298; −0.014 / +0.062 / +0.025; region −0.039 and 60; surplus 0.
- **Ch5 5.5 feedback**: own-target 0.450 / 0.041; N-STD Gini 0.114 vs 0.074; bottom quartile 0.376 vs 0.395; λ=0.5 0.088; Exp. B 0.115; grow 0.113; elasticity of 0.34 against a gain of 0.88.
- **Ch5 5.6 comparisons**
  - Workload 85,443; P90/P10 1.49 / 1.41; 8 provinces in all three first-year bottom-19 sets.
  - Health gain: all YLL and DALY percentages, the 28/22/17/28% shares, ranking unchanged across ε (including B-R\|asr above P-R at every ε), and the "สามแบบหลังใกล้เคียงกัน" verdict.
  - Uncertainty: 0.362–0.396 and 0.368–0.411; −0.0001 / 0.0001 / 45%; −0.0289 / 0%; adaptive 0.378 / 0.380 / 0.381.
  - Sensitivity: 0.535 / 0.478 / 0.753 / 13.7; 1.3 / 1.0 / 3.5 / 6.1.
- **Ch5 qualitative statements still valid after AdjRW 100**: N-R is minimax regret; "S-R ต่างจากเกณฑ์อื่นมากที่สุด"; "N-R อยู่ใกล้ P-R มากกว่า"; P–S is the largest cumulative difference; the net cap changes destinations more than any principle (20.0 > 11.4); the conclusion paragraph (S-R and SQ-C raise Gini, P-R and N-R lower it; transfers add little).
- **Ch5 appendix**: 89 / 3 / 1 / 82 / 0 plans; 0.471 / 1.838%; MILP 33 s vs greedy 0.06 s and 0.031%; 27 validation rows; M5 does not beat persistence in 6 of 6.
- **Ch4 4.3.6**: 61.6→63.5, Gini 0.742→0.754 (2560: 63.6 / 0.757); MOPH 15.6→17.8 and 73.3→72.2 (2560: 13.2 / 76.5); ρ +0.13, p 0.27, n 75. The new claims `c46_*T` and `c46_comove_*` equal the table values.
- **Ch4 new claims `c43_*_gini_min*`**: all eight equal the minima in `T43_INEQUALITY_ANNUAL`.
- **Stale wording**: no "ความจำเป็นอ้างอิง", "ประชากรถ่วงภาระโรค" (for family B), "90 นาที" as the Ch5 main value, "ร่างก่อนหน้า" or "ร่างเดิม" in either report. No CE years in Thai prose (only reference years and Basu 2019 / Anand 2004 citations). Ch4 uses "90 นาที" only as the declared comparison.
- **Code**:
  - `allocation.py` distribution-stage adoption cannot create infeasibility. It is gated by the same shortfall bound the solver uses, the operational stage is skipped because there are no transfers, and the independent check passes for every RT plan.
  - `validation.py` uses the Chapter 4 rule.
  - Chapter 5 code hash = manifest hash.
  - Both reports equal their templates rendered from the current claims (0 differing lines).
