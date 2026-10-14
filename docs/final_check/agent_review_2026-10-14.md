# Independent final check: Chapters 4 and 5 (agent review, 14 Oct 2026)

## Scope and method

I read both rendered reports in full (`reports/chapter4_complete_th.md`, `reports/chapter5_complete_th.md`). I then recomputed about 120 Chapter 4 claims and about 90 Chapter 5 claims from `outputs/*/tables`, `figure_data`, `validation`, `plans/chapter5_provincial_annual_plans_all.parquet` and, where possible, directly from `data/processed/*.csv`. I did not read the values from `claims.csv`. Every section was covered: 4.1–4.6, 5.1–5.7 and both appendices, with extra attention to the headline sentences, 4.5 burden, 4.6 coverage/spatial, the 5.x plan comparisons and the hindcast. Independent recomputations included:
- the weighted Gini from raw workforce and population (brute-force pairwise formula),
- the expected-DALY construction for Chapter 4.5 and family B,
- plan-to-plan destination switches and cumulative differences,
- the regrets,
- the hindcast MAE and coverage from the prediction file.

I also reviewed the code in `src/chapter4/metrics.py`, `panels.py` (burden functions and joins), `src/chapter5/hindcast.py`, `demography.project`, `inputs.flow_rates`, and the cross-evaluation and validation parts of `analysis.py`, `validation.py` and `pipeline.py`. I scanned all nine notebooks' executed outputs and re-rendered both templates from the current claims; the rendered reports match the current claims exactly. I did not rerun any part of the pipeline and did not modify any project file except this one.

Severity: **critical** = a wrong number or conclusion in the report; **major** = misleading wording or an inconsistency a reader would notice; **minor** = presentation. Some items rated critical have low practical impact; this is noted where it applies.

## Findings

| ID | Severity | Location | What is wrong | Evidence (recomputed value; table/row used) | Suggested fix |
|---|---|---|---|---|---|
| C-1 | critical | `reports/chapter5_complete_th.md:96`, `:176` (Table 5.8, column "ประชากรถ่วงภาระโรค"); claims `c54_regret_PR_B`, `c54_regret_SR_B`, `c54_regret_BR_B`; code `src/chapter5/analysis.py:34,357-361` | **Regret under criterion B is measured against the wrong reference.** The "best plan under that criterion" is taken only from `PRINCIPAL = [P-R, P-RT, S-R, S-RT, N-R, N-RT]`, so the B-optimised plans (B-R, B-RT) are excluded. As a result, Table 5.8 shows a **negative** regret for B-R (−0.7%), which is impossible under the caption's own definition. All other regrets under B are understated. The text's comparison "B-R loses 1.0% under P, while P-R loses only 0.2% under B" is asymmetric and reverses the impression: the true loss of P-R under B (0.93%) is about the same as B-R's loss under P (0.97%). | `T5_CROSS_EVALUATION_LONG`, criterion B, `cumulative_j`: B-R 4.3502, P-R 4.3907, S-R 4.4401, N-R 4.3813, SQ-C 4.4690, NFB1-R 4.4021. Regret vs B-R: P-R **+0.93%** (reported 0.2), S-R **+2.07%** (reported 1.3), N-R **+0.71%** (reported 0.0), SQ-C **+2.73%** (reported 2.0), NFB1-R **+1.19%** (reported 0.5). The regret_bottom_quartile_pp column under B has the same problem (B-R shows −1.1 pp). The N-R "minimax regret" conclusion at line 174 still holds after correction (max 1.17% under S). | Compute `best` per criterion over all comparable Experiment-A gross-arrival plans, including B-R/B-RT (or use the plan optimised for that criterion). Re-render Table 5.8 and line 96. |
| C-2 | critical (low impact) | `reports/chapter5_complete_th.md:152`; claim `c55_gainBmax_1`; code `src/chapter5/analysis.py:811` | The sentence is about the 2026 (พ.ศ. 2569) decision ("เฉลี่ย 0.33 ในปี 2569 … 7 จังหวัด … (สูงสุด 1.45 คน)"), but 1.45 is the maximum over all 15 years (it occurs in 2040). The 2026 maximum is 1.38. The published table `T5_FEEDBACK_ELASTICITY_2026` gives different 2026 figures again: unweighted mean gain 0.90, 12 provinces ≥1, max 1.435. That table uses Experiment-B scaling and unweighted means; the claims use Experiment A, H-weighted. | `T5_FEEDBACK_LOG`, plan NFB1-R: 2026 `gain_B_max` = 1.384, `provinces_gain_B_ge_1` = 7; the 2040 max is 1.447. `T5_FEEDBACK_ELASTICITY_2026` (lam=1): mean `gain_B` 0.896, 12 provinces ≥1, max 1.435. | Use the 2026 max (1.38), or say "สูงสุดตลอดช่วง". Align `T5_FEEDBACK_ELASTICITY_2026` with the claim definition, or label the difference. |
| M-1 | major | `reports/chapter4_complete_th.md:86` vs `:88` and Table 1 (`:106`) | **The same quantity is given two values in consecutive paragraphs.** Line 86: the NHSO register lowers density by **3.75%**. Line 88 and Table 1: by **3.6%**. Line 86 uses the national NHSO total (67,115,196, which includes 111,392 rights-holders with no province). Table 1 uses the sum of provinces (67,003,804). D8 in `docs/analytical_decisions.md` says unassigned persons are "kept nationally". Table 1 is a national density, so by that rule it should use the national total. | 1 − 64,596,347/67,115,196 = 3.753% (claim `c421_nhso_vs_age_density_pct`). 68.5588/71.1139 − 1 = −3.593% (`T421_SCOPE_VS_DENOMINATOR`, physicians all_sectors nhso_rights). `T421_NHSO_RECONCILIATION`: 111,392 without province. | Choose one denominator for national densities (national total per D8), regenerate Table 1, and make lines 86 and 88 agree. |
| M-2 | major | `reports/chapter4_complete_th.md:16`, `:34` (Finding 1), `:66` | **The headline "ทันตแพทย์ช้าที่สุด (1.29% ต่อปี)" is driven by a reporting break the chapter itself identifies.** Private dentists fall from 1,771 (2013) to 462 (2014), which line 24 calls coverage, not real change. Excluding that artefact, dentists are not the slowest-growing cadre. | `T41_WORKFORCE_ENDPOINTS`: public-sector CAGR dentists 3.07% vs nurses 2.78%; MOPH dentists 2.47% vs nurses 2.04%. All sectors from a 2014 base (2014→2025): dentists (8,940/6,544)^(1/11) = 2.88%/yr; nurses (203,224/158,659)^(1/11) = 2.27%/yr. | Qualify the ranking in line 16 and Finding 1 (e.g., report public-sector rates or the 2014 base), or drop "ช้าที่สุด" for dentists. |
| M-3 | major | `reports/chapter4_complete_th.md:238` (template `reports/templates/chapter4_th.md:227`, hard-coded text, no claim); conclusion `:348` | **Shapley sentence has no scope and is false for all-sector staff.** It says the decline in inequality per population "comes almost entirely from the workforce distribution; population redistribution has very little effect". That holds for MOPH staff only. For all-sector physicians and pharmacists, population redistribution is the larger part; for all-sector dentists the workforce distribution actually **increased** inequality. Separately, the endpoint statement "ลดลงในทุกวิชาชีพ" (4.3.1 and the conclusion) hides that all-sector Gini has risen since 2018–2019 for physicians, pharmacists and dentists. | `T43_DENOMINATOR_INEQUALITY_CHANGE` (population, own window), Theil change from workforce / from denominator: physicians all −0.0050 / **−0.0118**; pharmacists all −0.0054 / **−0.0066**; dentists all **+0.0031** / −0.0067; (MOPH physicians −0.0070 / +0.0007). `T43_INEQUALITY_ANNUAL` Gini (population): physicians all 0.221 (2019) → 0.235 (2025); pharmacists 0.125 (2018) → 0.138; dentists 0.162 (2018) → 0.197. | Scope the sentence to MOPH staff, report the all-sector split, and mention the post-2018 reversal in 4.3.1 and the chapter conclusion. |
| M-4 | major | `reports/chapter5_complete_th.md:60`; `T52_BASELINE_AND_ASSUMPTIONS` row "น้ำหนักบริการ" (source given as "ตัวอย่างในบทที่ 4"); `config/chapter5.toml:76`; `docs/chapter5_decisions.md` D8 | **Cross-chapter inconsistency in the inpatient time weight.** Chapter 5's service family S (and N-STD) uses 90 min/AdjRW. Chapter 4 (`:122`, `:126`) states that 100 min is its main value and that 90 min is the superseded draft. The Chapter 5 sensitivity grid (60/90/120) does not include 100. | Ch4: "บทนี้ใช้ 100 นาทีเป็นค่าหลัก และแสดง 90 นาทีไว้เทียบ". Ch5: `adjrw_minutes = 90.0`; `weight_sensitivity` = [[5,90],[15,90],[10,60],[10,120]]. | Either adopt 100 in Chapter 5 or state explicitly why Chapter 5 keeps 90 against Chapter 4's choice, and fix the T52 source text. |
| M-5 | major | `reports/chapter5_complete_th.md:124`; Table 5.4 (`T53_MAIN_PLANS`); Fig. 5.4 caption (`:114`); Table 5.8 row N-RT | The text says the RT plans have 0 transfers and that "the recruitment-only plan … is therefore the answer". **This is false for N-RT.** N-RT has 0 transfers but different recruitment destinations and different outcomes from N-R, because its distribution stage hit the time limit ("shortfall-stage solution retained"). Fig. 5.4 says dashed = "recruitment + transfers", so readers will attribute the N-R vs N-RT gap to transfers. | N-R vs N-RT: 9.0% of annual appointments switched (2,708 over 15 yr); J 4.339954 vs 4.339227 (−0.017%, within the 0.05% tolerance). 2040 bottom quartile 0.395 vs 0.387; Gini 0.073 vs 0.079; cap binding 0.63 vs 0.69. `T5_PLAN_INDEX` (N-RT: `incumbent_adopted` False; stage 2 not completed). | Seed N-RT with the finished N-R solution through all stages (or report N-RT = N-R), and add a note to Table 5.4 and Fig. 5.4. |
| M-6 | major | `reports/chapter5_complete_th.md:94`, `:164-166`, `:96` (verdicts "ต่างกันเชิงปฏิบัติ") | **Solution non-uniqueness is understated.** The report puts it at 4.6–5.7% of annual destinations and says the 5% threshold is "at the same level". Solutions in this build with practically equal J differ by 9–10% per year. So the annual-switch verdicts for P vs N (6.0%), N vs B (6.5%), B vs B\|yld (5.8%), B vs B\|asr (7.6%) and P vs B (8.5%) cannot be told apart from solver indeterminacy. Cumulative 15-year differences tell a clearer story: P vs S and P vs B exceed what near-optimal alternatives produce; P vs N does not. | Near-equal-J pairs: P-RT vs P-RT\|tau0.05 9.86% (ΔJ −0.011%); N-RT vs N-RT\|tau0.05 9.91%; N-R vs N-RT 9.03%. Max cumulative province difference: near-optimal pairs 37–75 (rolling 75, greedy 42, tangent 40, N-R/N-RT 40); P vs N 75; P vs S 425; P vs B 256. | Recalibrate the non-uniqueness benchmark to include these pairs, base verdicts on cumulative or allocation-invariant metrics, and soften the P vs N (and B-variant) verdicts. |
| M-7 | major | `reports/chapter5_complete_th.md:248` | **Over-claim from the hindcast.** After C1 passes, the report says the engine "อธิบายได้ว่าเป็นเครื่องมือพยากรณ์จำนวนรวมรายจังหวัด". This follows the pre-registered consequence, but the pooled C1 pass rests on 3 origins at h=3 and is driven by origin 2020 (the post-break trough, where persistence is mechanically penalised). The model loses to persistence at origin 2021, has a +4.1% national bias, and fails C2 and C3. | `T5_HINDCAST_METRICS`, h=3, per origin, MAE model vs persistence: 2020: 28.8 vs 40.9; 2021: **30.4 vs 27.2**; 2022: 25.0 vs 31.8. Pooled 28.09 vs 33.29 vs 32.82 (recomputed from `T5_HINDCAST_PREDICTIONS.parquet`). Coverage 0.441 overall, 0.412 at h=3; Jaccard 0.585. | Keep the pre-registered verdict, but add: three origins, one adverse; the gain is concentrated at the 2020 origin; biased upward; intervals not usable. Call it "provisional point-forecast skill at h≤3". |
| M-8 | major | `reports/chapter5_complete_th.md:112` (bold policy finding), `:222` (conclusion 4) | "ปัญหาของจังหวัดที่ต่ำที่สุดอยู่ที่ขีดความสามารถในการรับคนและการคงอยู่" presents an **assumed constraint as an empirical finding**. Bueng Kan's binding limit is the illustrative 10% gross-arrival cap. The recorded data show the province historically took in about three times that. | `T5_FLOW_RATES`, Bueng Kan (prov 38), FY2021–2025: 106 recruitment events on 379 person-years (raw 28%/yr, pooled 21.7%/yr), about 21/yr vs a model cap of 6/yr (plans parquet `cap_value`). Under the net-growth cap, Bueng Kan reaches 0.537 (`P-R|net`). | Rephrase: "under the assumed 10% gross-arrival cap …", and note that recorded intake exceeded the cap. |
| M-9 | major | Ch4 Fig. 27 caption (`chapter4_complete_th.md:292`, "ความจำเป็น M5"); T46 group label `need_not_service`; Ch5 throughout ("ความจำเป็นอ้างอิง" at `:110`, `:164`, `:166`, `:174`, `:196`, `:222`; Table 5.8 header "ความจำเป็นอ้างอิง M5"; T53) | **"Need" is used for the M5 model-standardised expected service use.** Chapter 4.2.3 (`:172`) explicitly says this quantity is "ไม่ใช่ความจำเป็นทั้งหมด", and Chapter 5 (`:61`) gives the exact name, but the label "ความจำเป็นอ้างอิง" then carries the conclusions ("การจัดสรรตามประชากรหรือความจำเป็นอ้างอิงลดความเหลื่อมล้ำ"). | Text comparison as cited. | Use one consistent label, e.g. "บริการคาดหมายมาตรฐาน M5 (N-STD)", in captions, table headers and conclusions. |
| M-10 | major | `reports/chapter4_complete_th.md:350`, `:352` (chapter conclusion) | **The conclusion attributes distributions to MOPH allocation rules**: "การจัดสรรของกระทรวงฯ ลดความเอนนี้ลง…", "กติกาการจัดสรรที่มีอยู่ ซึ่งเอนตามปริมาณบริการที่เกิดขึ้นแล้ว". This contradicts the chapter's own caveat at `:238` ("ไม่ใช่หลักฐานของเจตนาหรือกฎการจัดสรรที่พิสูจน์แล้ว"). The concentration-index change was not tested, and its intervals overlap heavily. | `T45_CONCENTRATION_BOOTSTRAP`: MOPH physicians 2013 −0.048 (−0.084, −0.008), 2025 −0.018 (−0.052, +0.019). | Describe as observed patterns of MOPH-staff distribution, not as effects of allocation rules; drop "ลดความเอน" or add that the change is within uncertainty. |
| M-11 | major | `reports/chapter4_complete_th.md:284` vs `:286` | The text says trend conclusions rely mainly on 2564–2567 because coverage was poor earlier (median ratio 0.87 in 2560, 0.77 in 2562). It then reports every trend over 2560→2567: community-hospital share 13.2→17.8, regional/general 76.5→72.2, and rho +0.31 on 2017→2024 changes. | `T46_SPECIALIST_CONCENTRATION` (MOPH), within 2564–2567: community share 15.6→17.8, regional/general 73.3→72.2 (direction holds, about half the size). `T46_SPC_RECONCILIATION`: 2017 ratio 0.874. Notebook 4.6 uses `y0 = SPC_YEARS[0] = 2017` for the co-movement. | Report the 2564–2567 changes as the main numbers (or state explicitly that the 2560 base is used and why). Recompute the co-movement on 2021→2024. |
| M-12 | major | Table 5ก.4 (`T5A_VALIDATION_SUMMARY`; `chapter5_complete_th.md:244-246`); code `src/chapter5/validation.py:56-60`, `:98-110` | **The validation summary reports values that are not the methods used in the chapters.** (a) C4-TEMP rows take the best of two year rules, so AdjRW 2025 M5 R² = **0.695** (and 0.630 for 2024), while Chapter 4 `:160` reports **0.670** for the same check. (b) C5-SVC rows show the best *non-adopted* method (AdjRW damped trend 6.67, marked "ดีกว่าตัวเทียบ"), while the adopted method is persistence (8.69). The Thai table drops the model-description column, so readers cannot see either choice. | `T423_TEMPORAL_VALIDATION`, forward, M5, adjrw 2025: `last_year_effect` 0.670, `trend` 0.695; 2024: 0.617 / 0.630. `T5_SERVICE_BACKTEST`: adjrw `constant_last` 8.69 (chosen), `trend_last5_damped` 6.67. | Use the same rule as Chapter 4 (`last_year_effect`), restore the model column in the Thai table, and label C5-SVC as "best alternative (not adopted)". |
| m-1 | minor | Fig. 21 `outputs/chapter4_3/figures/F43_CONVERGENCE_SCENARIOS.png`; notebook 4_3 cell 8 | The Prompt font lacks β, ● and ○, so the panel-ก legend and x-axis label render as empty boxes (UserWarning in the notebook). The panel-ข legend uses raw codes (growth_only …), and `redistribution_only` is invisible because it overlaps `growth_plus_redistribution`. | Viewed the PNG; notebook warnings "Glyph 946 / 9675 / 9633 missing from font(s) Prompt". | Use text labels, or a font with these glyphs; translate the legend; note the overlap. |
| m-2 | minor | `reports/chapter4_complete_th.md:334` | CE years in Thai prose: "ปีงบ 2017-2025". | — | "ปีงบ 2560–2568". |
| m-3 | minor | `chapter4_complete_th.md:180`; `chapter5_complete_th.md:35`; `chapter4_complete_th.md:190` | **Scope mismatch for the elderly share and the age-weighted population.** Chapter 4.2.3 (whose sample excludes Bangkok) quotes the national (77-province) elderly share 13.72→21.80 and age-weighted growth 9.73 / 15.44 vs 1.49, "for use in 4.3", but 4.3 uses 76 provinces. Chapter 5 quotes 21.5 for 2025 (76 provinces). Chapter 4.5 says the 60+ share is 18.7% (BOD mid-year population, 2022). | 76-province values: share 13.62→21.54; age-weighted +10.19 / +15.83 vs population +2.04 (`T423_AGE_WEIGHTED_POPULATION`, `province_panel_76`). Civil register 2022, 76 provinces: 19.05%. | State the scope or switch to 76-province values in 4.2.3. |
| m-4 | minor | `reports/chapter5_complete_th.md:156` | "ในทุกปี … ร้อยละ 20.1 ภายใต้ N-FB เทียบร้อยละ 18.0 ภายใต้ N-R": not true in every year. In addition, N-R is solved by a different method (full-horizon MILP) than N-FB (annual sequential); NFB0-R (λ=0, same solution path) is the clean baseline. | `T5_FEEDBACK_CONVERGENCE` `share_receipts_top19_2025`: 2037 0.200 vs 0.200; 2040 NFB1-R 0.190 < N-R 0.217. NFB0-R mean 0.182; NFB0-R Gini vs N-STD 2040 0.077 (N-R 0.073; NFB1-R 0.114). The conclusion holds. | Drop "ในทุกปี"; compare with NFB0-R. |
| m-5 | minor | `reports/chapter5_complete_th.md:202`; Table 5.10 | The perfect-foresight run is called a "ขอบเขต" (bound) on bottom-quartile adequacy, but it bounds J only. For N-R and S-R the foresight value is below the fixed schedule. Adaptive replanning lowers bottom-quartile adequacy in all three families while improving J, which is not said even though 5.7 recommends annual replanning. | `T5_UNCERTAINTY_SUMMARY` (60 paths), bottom quartile: N-R adaptive 0.3832 / fixed 0.3869 / foresight 0.3851; S-R 0.4057 / 0.4109 / 0.4096; P-R 0.3778 / 0.3801 / 0.3806. J (P-R): 4.3269 / 4.3303 / 4.3269. | Call it a bound on J; add one sentence on the bottom-quartile vs J trade-off. |
| m-6 | minor | `reports/chapter5_complete_th.md:200` | The N-criterion uncertainty results use 486 of 500 paths (14 invalid M5 bootstrap draws); this is not disclosed. | `T5_UNCERTAINTY_SUMMARY`, `n_valid` = 486 for criterion N. | Add "(486 เส้นทางที่ใช้ได้)". |
| m-7 | minor | `reports/chapter4_complete_th.md:308` | "เป็นการบรรจุข้าราชการ 12,254 ครั้ง": 12,254 counts all civil-servant entries, including 124 transfers-in and 11 reinstatements. Civil-servant recruitment is 12,119. | `T44_NURSE_FY2020`, FY2020, civil_servant. | Use "รับเข้าในตำแหน่งข้าราชการ" or 12,119. |
| m-8 | minor | `reports/chapter4_complete_th.md:84`, `:114`, `:116`, `:122`, `:152`, `:254`; Ch4/Ch5 "ผู้เขียน" phrasing | Draft-revision commentary left in the final text ("ร่างก่อนหน้า…", "ร่างเดิม…"). "ตารางที่ 1 ในร่างก่อนหน้า" (`:152`) can be confused with this report's Table 1 (density). | — | Move these to a reconciliation note or appendix. |
| m-9 | minor | `reports/chapter4_complete_th.md:158` | Double negative: "M5 แย่กว่าร้อยละ -10.17". | `T423_PAIRED_GAINS` op_moph M1_plus_supply→M5 −10.17 (−21.55, −0.11). | "M5 มีความคลาดเคลื่อนสูงกว่าร้อยละ 10.17". |
| m-10 | minor | `reports/chapter4_complete_th.md:356-368` | Appendix table numbering: "ตารางผนวกที่ ก2" sits in appendix ข and "ก3" in appendix ค. | — | Renumber as ข1 and ค1. |
| m-11 | minor | `reports/chapter4_complete_th.md:164` | "ในแผงยาว พ.ศ. 2556–2568" is also applied to AdjRW, whose long panel is FY2561–2568. | `T423_SUPPLY_ASSOCIATIONS` adjrw long: 608 rows, 2018–2025. | Add "(AdjRW 2561–2568)". |
| m-12 | minor | `reports/chapter4_complete_th.md:136`; `T422_CADRE_ACTIVITY` | Bangkok is handled inconsistently between the two HDC activity ratios: dental uses 76 provinces, prescriptions use 77 (includes Bangkok's 275–309 MOPH pharmacists). The numerical effect is negligible. | Excluding Bangkok: 2022 11,024 vs 10,978; 2024 9,102 vs 9,121 prescriptions per pharmacist. | Use 76 for both, or state the scope. |
| m-13 | minor | `reports/chapter4_complete_th.md:190` vs `:268` | Two different "ภาระส่วนเกิน" measures with different ranges: indirect-standardisation factor 0.73–1.15, and ASR relative index 0.73–1.17. | `T45_BURDEN_AGE_DECOMPOSITION` `excess_factor`; `T45_BURDEN_INDEX` `RB_daly`. | Name them differently or explain. |
| m-14 | minor | `src/chapter5/hindcast.py:119-128` | (To confirm intent.) The C3 / Spearman scoring forms *predicted* densities with the **observed target-year population**, which is post-origin information inside the metric. Model inputs are cutoff-safe (checked). The persistence comparator gets the same benefit, and C3 failed anyway. | `pop = g.population_observed` used in `dp = pred / pop`. | Use the Hamilton–Perry population projected from the origin for predicted densities, or document the convention. |
| m-15 | minor | `reports/chapter5_complete_th.md:146`, `:156` | λ=1 ("full response") is calibrated on the cross-sectional positive-mean M5 (AdjRW elasticity 0.60). Chapter 4's within-province PPML estimate is 0.200 (0.081–0.319). The headline feedback result (Gini 0.114) relies on λ=1. | `T5_M5_COEFFICIENTS` `coef_positive_mean_model` adjrw 0.605; `T423_SUPPLY_ASSOCIATIONS` adjrw `province_year_fe` 0.200. | Add one sentence noting that λ≈0.33 corresponds to the within-province association. |
| m-16 | minor | `reports/chapter5_complete_th.md:33`; Table 5ก.4 C5-POP rows | Hamilton–Perry beats no-change on provincial MAPE, but is worse on the 76-province national total, which drives the 1:1,000 target. This is not mentioned. | `T5_POP_BACKTEST` `national_76_error_pct`: HP +1.10, no-change +0.25. | Mention it. |
| m-17 | minor | `reports/chapter5_complete_th.md:228` | "7 แผนที่มีการโยกย้าย … จึงใช้แผนรับใหม่อย่างเดียว": one of the seven (N-RT\|net\|tau0.05) ends with 644 transfers; the distribution stage moved away from the incumbent. | `T5_PLAN_INDEX`: N-RT\|net\|tau0.05 `incumbent_adopted` True, `transfer_events` 644. | Say "6 of 7". |
| m-18 | minor | `docs/chapter5_methods.md` §6; `docs/methods_and_limitations.md` (quality gates, limitations list) | Stale documentation. Stage 2–3 limit is stated as 60 s, but the config and D22 use 240 s. "Clean re-execution of four notebooks" and "21 figures" are out of date (now six Chapter 4 notebooks; the report has 31 figures). The limitation list is numbered 1, 2, 3, 11, 4, …. | `config/chapter5.toml:137` `secondary_time_limit_s = 240`. | Update the docs. |
| m-20 | minor | `reports/chapter5_complete_th.md:228` | "แผนที่ใกล้ที่สุดที่ผ่านข้อจำกัดต่างจากกฎเดิม 2,938 ตำแหน่ง" is the full L1 distance Σ\|x−y\|. Elsewhere the chapter counts switched appointments as ½Σ\|x−y\| (`:164`). By that convention, 1,469 appointments move. | Plans parquet: SQ-HIST vs SQ-C, Σ\|Δ\| = 2,938; ½Σ = 1,469. | Report 1,469 "ตำแหน่งที่ต้องย้าย", or say it is an L1 distance. |
| m-19 | minor | `notebooks/chapter5_1..5_3*.ipynb` (notebook health) | The Chapter 5 notebooks were last executed on 27 Sep and contain no family-B, health-gain or hindcast outputs, so they are stale relative to the 14 Oct build. The values they do show match the current tables. All Chapter 4 notebooks are clean: no errors, monotonic execution order, only glyph warnings (m-1) and a Pandas4Warning in 4_5. | `grep` of the notebook outputs; file timestamps. | Re-execute the Chapter 5 notebooks or mark them as historical. |

## Checked and found correct

**Chapter 4.1**
- All-sector headcount endpoints and CAGRs for all four cadres (4.60 / 3.27 / 3.61 / 1.29) and the ratio 0.28.
- Sector CAGRs: public, private, MOPH, other-public.
- Technical-nurse figures (4,093; 5,331 vs 1,238; 131,349; 3.70).
- 2023 transfer shift (−3,806 / +5,473 / +4,562).
- Private dentists 1,771→462→463.
- Contributions to net change (42.83/31.68/25.49; 41.18/32.73/26.09; 63.56/24.10/12.34; 124.29/78.54/−102.83).
- Service endpoints and CAGRs for both tiers.
- OP decomposition (4.36→4.24, −0.23%; 3.72→4.23, 67.84%).
- 2023 person jumps, including the non-MOPH +100.19% (recomputed from the annual series).
- MOPH shares (40.70 / 86.43 / 88.04; 61.17→56.27, etc.).
- Case mix: 866–895 hospitals, +38.84%, CMI 1.1131→1.3514, +14.35% cases, 59.1% log share, +12.42% in FY2566, other years ≤7.67.

**Chapter 4.2**
- Population 63,650,593→64,596,347 (+1.49%).
- Densities for all scopes and cadres (Table 1 cells spot-checked).
- MOPH share 58.55→51.99.
- Combined density 2.59→3.86, 86.68%, 68.10%.
- Reference scenarios (4.58 / 4.56 / 4.33 / 4.30, BE 2575, 2.90–3.03%, 3.50%), MOPH scenarios (148,388; 2.30; 2.67 / 2.57 / 2.33; BE 2590–2636; 14.28% vs 2.27%).
- Register reconciliation (65,809,011; components sum exactly; 1.84%; NHSO 3.90%; 1,307,527).
- Service per staff, matched 76 provinces (7,436→5,939; 1,716→1,428; 1,178→1,121; 272→269; 2018–2025 rates; AdjRW per staff 386.8→484.0 at 3.25%/yr; nurses 71.1→91.3 at 3.65%/yr; 459.7).
- Time arithmetic (990 / 807 / 1,796 h; 225 days; 1,152 h; 156% / 149%; 374 days; 51–128%; 85–213%).
- HDC activity (3,368→4,230; 10,978→9,121; 17.6 / 8.8 / 38.0 / 9.5).
- 4.2.3 models:
  - M0–M5 R² (all 18 values);
  - paired SSE gains with CIs (beds; M4→M5; drop-physicians 25.28; drop-nurses −0.99; age 14.53; disease 17.95);
  - nurse–bed correlation 0.78;
  - temporal R² (0.673 / 0.804 / 0.946 vs 0.381 / 0.360 / 0.670);
  - PPML elasticities (0.708, 0.162, 0.668, 0.461, 0.200);
  - within-province variance shares (3.8 / 2.1 / 2.5);
  - M5 standardised changes with CIs (all-76 and balanced-74);
  - age-weight verdicts and scenario growth (national).
- 4.2.4 denominator matrix (48.39 / 25.20 / 20.21 / −20.07; nurses 24.58 / 5.11 / 0.92 / −22.21; short window 6.95 / 4.80 / 8.40 / −2.76 / −6.66).

**Chapter 4.3**
- Gini 2013/2025 for all eight cadre-scopes, recomputed independently from `data/processed` with a brute-force weighted Gini (all match to 3 d.p.).
- P90/P10 2.97; Theil between-region shares (30.4; 23.9→15.0; 20.5→38.5).
- Gini vs services (0.117 / 0.128 / 0.139; 0.101→0.101; 0.136→0.079).
- Baseline-quartile gains (64.7%, 34.5%, 12.0 / 12.0, 26.5 vs 28.3, 50.7 vs 2.7).
- Beta/sigma convergence (all coefficients and CIs quoted).
- Scenarios (3.52%, Gini 0.122, BE 2571 / 2571 / 2569, 38 provinces losing staff).
- Priority sets: 4 provinces in all six (and all nine) denominators; 41 in any; overlaps 7–18 and 8; 25 uncertain (union of three M5 outcomes); Bueng Kan rank 1 under all ten denominators; switchers' ranks.
- Pathum Thani / Narathiwat figures (1,229,364; 279; 4,406.32; 4,441.72; 3,563.97; 4,249.16; 1.01 / 1.19 vs median 2.41).

**Chapter 4.5 / 4.3.5**
- ASR median 25,140, min Nonthaburi 17,870, max Chaiyaphum 28,745, ratio 1.61, P90/P10 1.31; top-5 and bottom-5 lists.
- YLL 77.8%, NCD 70.4%, variance shares 67.5 / 24.1 / 8.4, the top three variance drivers.
- COVID share 3.1% (median) / 5.8% (max).
- Spearman correlations (−0.54 / −0.51 / +0.11 / −0.15).
- 80+ vs 30–44 = 6.8×; 60+ share 18.7% of population and 45.5% of DALY.
- Total 18,479,241; crude rate range 22,404–40,370; 1.27; age factor 0.82–1.16; excess 0.73–1.15; 37%.
- Expected DALY 15,968,772→19,341,080 (+21.1%) vs population +2.0%; provincial range 9.4–44.3% (Pathum Thani).
- HDC vs BOD correlations and the pooled recording model (0.20 [0.11, 0.30]; 0.36 [−0.05, 0.76]; 3.5%).
- Burden-in-model gains (−5.76 / −5.18 / −6.67 with CIs) and M5HB effects (+0.8, −1.7).
- Burden Gini (0.133 / 0.138 / 0.122; 0.264 / 0.267 / 0.235), concentration indices and bootstrap CIs, YLL / YLD indices, quintiles (21.1→34.0; 25.6→36.0; 16.6 vs 16.9), dentists +0.047.
- Burden priority sets (16; Buriram / Kanchanaburi, J = 0.90; 3 in / 3 out, J = 0.73; 4 of 4; 8), reallocation 1,985 / 2,177 / 2,272, and the five largest gap changes each way.
- Code: `burden_age_rates` sums counts over causes within age groups (mid-population is constant across causes, verified); `expected_burden` uses 2022 province rates × each year's 8-group counts; recomputed totals for 2013, 2022 and 2025 match.

**Chapter 4.4**
- Entries and exits per cadre; exit-cause shares; FY2020 nurse figures (19,198; 15,005; 6,946).
- Parsing defects (8; +9,895; +1).
- Facility-stock breaks (+37.1%, +39.4%, −16.9%).
- Stock–flow reconciliation (2,462 / 2,496; 13,540 / 15,659 / −2,119 / −15.6%; 5,886 / 8,608 / −2,722 / −46.2%; 30,277; 162; 153 / 684).
- Intensities (3.39 / 1.34 / 2.97 / 2.66; 10.99 / 6.20; 9.57 / 8.06; 0.84 / 0.56) and the quartile and priority-group contrasts.
- PPML workload effects, primary and free-stock (3.7 [1.5, 5.9]; 4.7 [2.2, 7.3]; 4.1 [1.4, 6.8]; 1.7 [−0.2, 3.5]).

**Chapter 4.6**
- Specialist concentration (63.5 / 63.6 / 0.754; 13.2→17.8; 76.5→72.2; rho 0.308, n = 75).
- Coverage ratios (0.87 / 0.77 / 0.94–0.99).
- Rank-disagreement groups (8 / 11 / 11; medians 1.82 / 3.04; 62% vs 36%; the group definition matches the text).
- Coverage appendix (15,246 cells; 24 breaks: 10 private, 5 MOPH).

**Chapter 5.2**
- 22,685; population 59,316,175→55,406,782 (−6.6%; −6.7 / −6.5); 60+ share 21.5→32.0; births 395,893→329,845.
- Backtest (1.11 / 2.23 / 2.62; 0.28 / 4.72; +1.10).
- Hazards 5.52 / 0.75 / 0.21 / 0.04 / 0.02 and 0.45; EB P10–P90 3.6–9.7→3.8–8.0; 6.25%; 1,418; about 108.
- FY2021–25 stock +4,358 vs net 4,290 (68); 2020 residual −4,364; replay −223 / 11.3%; 2,092 / 1,330; target 59,316, 0.38; steady state about 34.6k.

**Chapter 5.3**
- B family: 19,341,080→22,505,246 (+16.4%), 0.326→0.406, share range 0.72–1.29 (Phuket / Chainat), the three largest gains and losses each way. Recomputed from `T5_POP_PROJECTION` × BOD rates; equals Chapter 4 exactly for 2025.
- M5 support (28 / 83 / 93%; 30.6%), coefficients 3.715 / −0.631, minimum AdjRW 0.079.
- Index changes (−6.6 / −7.2 / −5.5); service backtest (11.5 / 8.7 / 6.7).
- First-year and 15-year allocation differences for S-R, N-R and B-R vs P-R (all provinces and values quoted).
- B-R switches 8.5 / 12.3 / 10.8 / 6.5; B-R bottom quartile and Gini under B; B-R\|B 0.435 vs 0.541.

**Chapter 5.4**
- Stock 30,011; adequacy 0.542; shortfall 25,396 (spatial gap 0).
- Gini (0.121→0.083 / 0.094 / 0.140 / 0.182) and bottom quartile (0.377 / 0.377 / 0.350 / 0.314).
- Bueng Kan 0.099, 72→37, 13.4%.
- Cap binding 63% / 10%; net cap 0.535, Gini 0.001, Bueng Kan 0.537; 20.0% switch.
- Pool 2,500: 1,078 unplaced; pool 1,500: 24,624.
- Transfers 545 / 652 / 976 and region 534; inverse feasibility 0.73 / 0.11 / 58,063 / 6,939 / 0.80.

**Chapter 5.5–5.7**
- Elasticities 0.14 / 0.19 / 0.60; N-FB own vs N-STD metrics (0.449, 0.041, 0.114, 0.073, 0.376 / 0.395, 0.088, 0.114, 0.112).
- Switch metrics (192 / 9.6 / 15.3 / 2,887; 119 / 6.0; 200 / 10.0; 296 / 14.8; 4.6 / 4.7 / 5.7; nofloor 122).
- Cross-evaluation P, Pent, S and N columns; workload 81,258 and P90/P10 1.49 / 1.40; the eight provinces in all three criteria.
- Health gain: 4,398,027 YLL and 22.4%; 1,331,630; 18,335; 671,696–3,243,101; −4.4 / −7.8 / −0.4 / −0.5 / +0.4; 28 / 22 / 17%; +6.3 / +5.6.
- Uncertainty: 0.362–0.396, 0.369–0.410; paired differences 0.0000 / 0.0002 / 47%, −0.0299 / 0%; 21.0% cap breaches; 0.378 / 0.380 / 0.381.
- Sensitivity values (0.535 / 0.478 / 0.753; 13.7; 1.1 / 1.6 / 3.5 / 5.8; 303).
- Rolling 0.069%; greedy 0.031%; tangent 0.005%; MIP gaps 0.472% / 0.713%; 87 / 80 / 3 / 1 plans, with the one constraint failure being SQ-HIST by design.

**Hindcast code (`src/chapter5/hindcast.py`)**
- Hazards are re-estimated on FY ≤ origin, with exposure equal to the prior-year stock.
- Recruitment uses the mean of FY ≤ origin; the trend uses stock ≤ origin.
- Population: `demography.project` slices the register array at the base year; CCR and CWR windows end at the origin.
- No look-ahead in the model inputs (see m-14 for the scoring metric only).
- `validation.toml` SHA-256 = `16d303bdfe78…`, as reported. C1 / C2 / C3 values (28.09 vs 33.29 / 32.82; 0.441; 0.585) were reproduced from the prediction file.

**Other code**
- `metrics.weighted_gini` (sorted form equals the pairwise definition, verified numerically), `theil_t` / `theil_decomposition`, `concentration_index` (2·cov(x, R)/μ with midpoint ranks and averaged ties) and the CAGR elapsed-interval convention are correct.
- The panel join audit is one-to-one with no dropped province-years (`outputs/shared/join_audit.csv`).
- BE/CE handling: `be()` = +543 and the sheet-year parsing were checked; Chapter 5 figure axes are in BE.

**Rendering**
- Both rendered reports equal the templates re-rendered from the current claims files; there are no unresolved placeholders.

## Not checked

- Visual inspection of figures: only F43_CONVERGENCE_SCENARIOS, F45_DENSITY_VS_BURDEN and F54_ADEQUACY_AND_INEQUALITY were viewed. The other 28 Chapter 4 figures and 8 Chapter 5 figures were checked only through their captions and the tables behind them.
- The DOCX versions of both reports.
- Re-estimation of any model: the M5 fit, the PPML, age-weight NNLS, bootstrap draws, MILP solutions and the uncertainty simulation were taken as exported. I recomputed derived statistics only.
- Workbook parsing of the raw HROPS / HRR Excel files, the NHSO and DOPA register extraction, and the BOD web extract against source.
- Chapter 5 lab modules (`lab_*.py`), the web outputs, and the `outputs/chapter5_scenarios` folder.
- Most of the 3,160 Chapter 5 claims and 4,377 Chapter 4 claims not quoted in the reports. Report-quoted claims were sampled as listed above; a handful were not recomputed, for example "373 unplaced in 2569", "9.1e-13" and the 4.2.3 fold-reordering 0.058.
- Whether CMI file years (`CMI_2018.xlsx` …) are CE fiscal years. The parser assumes CE, and the report's BE labels follow from that assumption.
