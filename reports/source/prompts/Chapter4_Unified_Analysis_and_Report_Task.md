# Unified Chapter 4 analytical task for the VS Code agent

## 0. Execute this assignment

Consolidate this repository into one reproducible analytical workflow and complete the analysis and Thai research report for Sections **4.1–4.4**. Work directly in this repository. Implement the changes, run the analyses, inspect the results, generate the tables and figures, and write the report. A proposed plan or a collection of partially completed notebooks is not the requested deliverable.

The repository is now the **authoritative source of analytical results**. Earlier calculations, exported tables, notebook outputs, and discussion drafts are material to reconcile, not independent sources of truth. Every reported number must be traceable to a current computation from identified inputs.

The author has already refined Sections 4.1–4.2.2. Preserve their reasoning, useful analyses, and writing style while checking their numerical consistency. Rebuild 4.2.3 around the agreed **M0–M5** sequence; complete 4.2.4; and create the analysis notebooks and report sections for 4.3 and 4.4. Keep physicians, professional nurses, pharmacists, and dentists in view throughout, using measurements appropriate to each profession.

You are authorized to reorganize analytical files, update imports and paths, move unused raw datasets into `data/cold_data/`, and remove verified obsolete, reproducible byproducts. Preserve original source data, unique author edits, and unrelated repository work. Follow the cleanup procedure below instead of deleting files merely because their names look old.

### Instructions and evidence precedence

Apply the following distinctions:

1. **Current instructions and analytical decisions:** this task defines the current scope and supersedes conflicting requirements in the two older task prompts, especially their prohibition on shared Python modules and their outdated model sequence.
2. **Editorial reference:** the latest author-written research report defines the intended argument, voice, and treatment of completed sections. It is not a numerical oracle.
3. **Numerical evidence:** verified source data, documented transformations, and freshly executed code determine the results. If these disagree with prose, resolve the source/definition issue and update the prose with a change record.
4. **Existing notebooks:** reuse correct, useful code and methods. Inspect them before replacing anything. Saved cell output alone does not establish reproducibility.
5. **Earlier analytical packages and results:** use them as comparison material and implementation references when available. Do not hard-code their answers or import unexplained final results into the new pipeline.

Read applicable `AGENTS.md` and repository instructions. Resolve routine implementation choices independently. Ask the author only when a missing definition or decision would materially change an analysis and cannot be resolved from the repository. Continue all unaffected work while recording a specific blocker. Do not invent data or silently choose a convenient definition to complete a table.

## 1. Read the supplied material before changing the analysis

Locate these files by content and filename; directory locations may differ:

| Material | Role in this assignment |
|---|---|
| `รายงานวิจัยฉบับสมบูรณ์_LASTEST.docx` | Latest editorial reference; retain its completed 4.1–4.2.2 argument and continue its Thai prose. |
| `chapter4_1_counts_and_services.ipynb` | Existing analysis of counts, growth, sectors, services, and case mix. |
| `chapter4_2_denominators_workload_and_need.ipynb` | Existing population/service analysis and an older need-model implementation requiring migration. |
| `Chapter4_1_Draft_and_Notebook_Analysis_Prompt(1).md` | Earlier requirements and checks worth retaining where consistent with this task. |
| `Chapter4_2_Draft_and_Notebook_Analysis_Prompt(1).md` | Earlier requirements, data definitions, and normative-need framework; its model and architecture instructions are superseded where specified below. |
| `enter_moph.xlsx`, `loss_moph.xlsx` | Actual recorded entries and exits. Use both in 4.4; do not infer all entries from changes in stock. |
| Any previous M0–M5, inequality, and entry/exit analytical packages supplied with the repository | Candidate reusable code and reconciliation evidence, subject to source and execution checks. |

The existing notebooks reference sources such as `data/hrh_moph.xlsx`, `data/cmi/CMI_<FY>.xlsx`, population age/grand-total/entitlement folders, `data/epi/`, `data/gpp.xlsx`, `data/hosp.csv`, and `data/hrh_aggregated.csv`. Discover the actual files rather than assuming all paths remain correct. Inspect any additional datasets already supplied, including those not yet used by the old notebooks.

Earlier extracts may include:

- `workforce_province_year_cadre_sector.csv`
- `services_province_year_wide.csv`
- `population_province_year_sex_singleage.csv`
- `nhso_province_year_scheme_agegroup_sex.csv` and its scheme-code crosswalk
- `casemix_province_fiscalyear.csv`
- `epidemiology_province_year_prevalence_wide.csv`
- `gpp_province_year.csv`

Determine whether each is an authoritative external input, a reproducible extract from a workbook, or an older derived dataset. Do not retain two competing canonical versions of the same series.

### Known migration issues to investigate

These are starting points for reconciliation, not instructions to reproduce predetermined numbers:

- The supplied 4.2 notebook uses an older **M0–M4** specification, including a trend/COVID baseline, five age bands, and some all-reporting/all-sector inputs. The latest report instead presents **M0–M5**, three broad age groups, year indicators, and a focus on MOPH hospital services outside Bangkok. This is a substantive migration, not a relabeling exercise.
- The latest report's M0–M5 table already separates beds in M4 from physicians plus nurses in M5, but a subsequent paragraph still refers to M4 as the final model. Update the surrounding reasoning, model comparisons, tables, captions, and standardization consistently.
- The national 2013 professional-nurse count was corrected to **131,349** in the latest report. An earlier **138,205** included technical nurses. Verify the raw categories and prevent their reintroduction.
- MOPH workforce counts may cover more institutions than the regional/general/community hospitals supplying the service totals. The latest report recognizes this mismatch. Do not erase it by renaming both variables “OPS” without source evidence.
- The current workload illustration uses approximately **484 AdjRW per physician**, whereas an earlier discussion used approximately 460. Compute from full-precision sources and make every derived hour/day figure agree with the selected scope and year.
- A previous narrative equated B.E. 2589 with “another 50 years.” Recalculate all calendar intervals from the stated reference year; do not carry this wording forward.
- Some older age-weight results failed stability tests. A later simpler model may behave differently, but a new fit must establish this; neither the old failure nor a new apparent success is automatic proof.
- Previous inequality results, province examples, and flow models may have used older M4 standardization, different workforce definitions, or mismatched periods. Recompute dependent analyses after the shared definitions and M5 outputs are finalized.

Create a short `reconciliation_log` with the old statement/result, source location, verified new result, reason for change, and downstream outputs affected.

## 2. Repository organization and safe cleanup

### 2.1 Inventory and preserve the current state

Before moving files:

1. Inspect Git status and preserve existing uncommitted work. Do not reset, clean, or overwrite unrelated changes.
2. Record the current analytical entry points, dependency/environment files, source paths, generated outputs, and report sources.
3. Inventory analytical files with path, size, checksum, source/provenance, years, geography, units, role, generating code if any, and downstream users. Hash-based duplicates are stronger evidence than similar filenames.
4. Create a recovery record appropriate to the repository: a dedicated branch when useful, a scoped snapshot of unique untracked analytical material, and a path migration manifest. Avoid copying the entire repository into multiple backup folders.
5. Identify the author-edited document and prose sources explicitly. Keep the supplied originals intact.

### 2.2 Adopt one small, navigable structure

Adapt names if the repository already has a good equivalent structure. Do not reorganize unrelated projects or introduce a large framework for its own sake.

```text
README.md
requirements.txt / pyproject.toml / existing environment lock
config/
  analysis.yml
  source_registry.yml
data/
  raw/                         # authoritative, unchanged source files
  processed/                   # canonical normalized tables and shared panels
  cold_data/                   # unused original datasets, preserved with metadata
src/chapter4/
  paths.py
  ingest.py
  panels.py
  metrics.py
  models.py
  reporting.py
  build.py
notebooks/
  chapter4_1_counts_and_services.ipynb
  chapter4_2_denominators_workload_and_need.ipynb
  chapter4_3_distribution_and_inequality.ipynb
  chapter4_4_entries_exits_and_growth.ipynb
outputs/
  shared/
  chapter4_1/
  chapter4_2/
  chapter4_3/
  chapter4_4/
reports/
  source/                      # protected author reference material
  templates/                   # editable Thai prose and numeric placeholders
  chapter4_complete_th.md
  chapter4_complete_th.docx
docs/
  data_catalog.md
  analytical_decisions.md
  methods_and_limitations.md
  reconciliation_log.csv
  file_migration_manifest.csv
  completion_report.md
archive/
  legacy_analysis/             # only unique old material worth retaining
```

This layout is a guide, not a requirement to create empty modules or folders. Combine small modules where appropriate. Keep one obvious location for each canonical input, dataset, notebook, report, and figure.

### 2.3 Shared code and editable notebooks

**This task supersedes the old requirement that every notebook contain its own complete ingestion and cleaning implementation.** Put genuinely shared ingestion, variable definitions, metrics, validation, and report rendering in a small common module. All notebooks must use it.

However, the notebooks must remain readable analytical documents:

- Use Thai Markdown to state each question, equation, sample, result, and interpretation.
- Keep section-specific modeling calls, specifications, and figure construction easy to locate and modify.
- Show the data behind each main figure immediately before the figure or link to a displayed named table.
- Display effective configuration near the beginning: sources, scope, years, geography, age groups, assumptions, validation seed, and relevant plotting settings.
- Keep one authoritative configuration. Clearly named exploratory overrides are allowed, but must produce separate scenario outputs rather than silently change canonical results.
- Do not turn the notebooks into opaque one-line wrappers; do not duplicate shared transformations across them either.
- Each notebook must run in a fresh kernel after the documented shared-data build. No hidden variables inherited from another notebook are permitted.

### 2.4 Cleanup rules

| File class | Action |
|---|---|
| Original source data used by any current or required analysis | Preserve unchanged under the active raw-data structure. |
| Original source data not currently used | Move to `data/cold_data/` after checking the required analyses and recording what it contains and why it is unused. |
| Exact redundant copies | Retain the canonical copy and provenance; remove the duplicate only after confirming that references have been migrated. |
| Obsolete reproducible outputs, temporary renders, caches | Remove after the replacement pipeline has generated and verified the necessary outputs. |
| Unique legacy analysis or manually edited prose | Archive with a brief note; do not treat it as disposable output. |
| Ambiguous ownership or unknown provenance | Preserve and flag for review instead of deleting. |

Exclude `cold_data` and `archive` from automatic input discovery. A dataset cannot be declared unused merely because the old notebooks did not use it: first check whether it supplies a missing requirement for 4.2.3, 4.3, or 4.4. Record all moves/deletions and update notebook links, imports, README instructions, and report references.

## 3. Build the common analytical foundation

### 3.1 Common definitions and analytical universes

Create an explicit source-and-scope crosswalk covering:

- Professional categories: physicians, **professional** nurses, pharmacists, dentists; identify technical nurses separately.
- Disjoint sectors: MOPH, other public, private, and any unresolved category; derive public/all-sector totals without double counting.
- Institutional scope: MOPH-wide workforce, OPS workforce where available, regional/general/community hospital services, other hospital groups, and all reporting facilities.
- Population: age-disaggregated civil registration, published civil-registration totals, and health-entitlement registration; nationality, reference date, inclusion rules, and deduplication limits.
- Service units: outpatient visits, reported outpatient persons, admissions/discharges, inpatient days, SumAdjRW, and CMI. Preserve their distinct meanings.
- Activities specific to dentistry and pharmacy, including the actual reporting-facility universe and year coverage.
- Stocks versus employment events; headcount versus FTE; calendar/report year versus fiscal year.
- Resident-based population/health measurements versus provider-location service measurements.

In this project, `moph_service` means the sum of services from **regional hospitals + general hospitals + community hospitals**, subject to verified source categories. Keep the original components and an explicit membership mapping. Do not silently include every facility administered anywhere within MOPH.

Do not equate MOPH-wide staff with OPS hospital staff. If a genuinely matched OPS/hospital workforce series exists, make it available as a separate universe and compare it with the broader series. Never silently splice these scopes across years. A broader-workforce/narrower-service ratio may remain a clearly labeled descriptive proxy where the data require it.

### 3.2 Geography and periods

- Preserve the latest report's national coverage in 4.1 and the national population comparisons in 4.2.1. Do not silently change a national series by dropping Bangkok.
- Exclude Bangkok **from the outset** in the provincial need/service models, inequality analysis, and provincial entry/exit analysis. These are 76-province analyses unless documented data exclusions reduce a specific sample.
- Export a bridge between the national series and the 76-province series so that differences can be explained.
- Use stable province codes; normalize Thai names and document aliases. Map health regions explicitly and check their applicable period. Do not classify central administrative rows as provinces.
- Keep annual data where valid; use 2013–2025 for the established long series where available, 2018–2025 for case-mix comparisons where available, and the genuinely observed morbidity years for morbidity models.
- Use a common eligible sample for a specific comparison. Do not force every chapter to use the short morbidity period.
- Preserve `year_basis` and, where possible, actual period start/end dates. Pairing a fiscal-year outcome with a calendar/report-year covariate is an approximation to document, not a conversion accomplished by renaming a column.
- Compute lags by exact year joins within province and scope. A row shift across a missing year is not a one-year lag.

### 3.3 Canonical tables and panels

Build only the normalized tables needed, with clear keys. At minimum provide the equivalent of:

| Canonical data | Expected grain and essential content |
|---|---|
| Workforce | Province × year × cadre × sector/universe; count, definition, coverage flags. |
| Population | Province × year × register; age/sex detail in a related table where available. |
| Services | Province × year × provider universe × activity; total, unit, reporting coverage. |
| Case mix | Province × fiscal year × comparable reporting universe; SumAdjRW, calculated cases, days if available, DRG/reporting flags. |
| Epidemiology and economic context | Province × year × indicator; units, population base, reference year, provenance. |
| Employment events | Province × fiscal year × cadre × event type; entries and exits with source category preserved. |
| Provincial analytical panel | Unique province-year rows within a named universe, joined from the above, with eligibility flags for each analysis. |
| Denominators | Province × year × denominator ID × service outcome/scenario; raw value, unit, reference profile, uncertainty where relevant. |

Use long tables for extensible measurements and explicit wide model panels where convenient. The two forms must be generated from each other, not maintained independently.

Maintain `source_id`, `universe_id`, `year_basis`, `geography_basis`, `unit`, `status`, and source-row/file lineage directly or through linked metadata. Validate join cardinality. Do not allow many-to-many joins to inflate counts. Distinguish observed zero, blank-as-zero justified by a reporting form, missing, not applicable, and structurally unreported.

Generate `source_inventory`, `scope_crosswalk`, `coverage_by_year`, `missingness`, `duplicate_keys`, `join_audit`, and `analysis_sample_flow`. Explicitly report exclusions, not just final sample sizes.

## 4. Section 4.1 — ความจริงของจำนวนที่เพิ่มขึ้น

Preserve the existing section's progression: national growth → differences between professions and sectors → absolute contribution to growth → growth and composition of services → why parallel increases do not establish adequacy or equilibrium.

### Required analysis

1. Annual headcounts and endpoint changes for all four professions, nationally and by the disjoint sectors.
2. Absolute change, percentage change, and CAGR. For positive endpoints use:

   \[
   g=(W_{t_1}/W_{t_0})^{1/(t_1-t_0)}-1.
   \]

   Count elapsed intervals, not the number of annual observations. Handle zero/negative endpoints explicitly rather than fabricating CAGR.
3. Contributions of MOPH, other public, and private sectors to the total **net increase**, alongside sector growth rates. A rapidly growing small sector need not contribute the most people.
4. Preserve legitimate negative contribution shares and shares above 100% when one sector contracts. Do not use a positive-only stacked chart that hides them.
5. Investigate reporting discontinuities, including private dentistry and the redistribution of nurses around health-facility decentralization. A movement between reporting sectors is not necessarily an exit from the health system.
6. Outpatient visits, reported persons, and visits per reported person; explain what the person count can and cannot deduplicate. Decompose the change using the exact identity `visits = reported persons × visits per reported person`, on a common source/scope.
7. Inpatient admissions/calculated cases, days, length of stay where defined, SumAdjRW, and CMI. Aggregate CMI as `sum(SumAdjRW) / sum(eligible calculated cases)`, not the average of facility CMIs.
8. Use `SumAdjRW = eligible calculated cases × CMI` only when numerator and case denominator come from the same records. Do not substitute unrelated hospital admissions.
9. Compare the long window with the common case-mix window without changing scope unnoticed. Check DRG-version/coding/reporting changes before interpreting rising AdjRW as exclusively greater clinical severity.

### Required report treatment

Keep the author's distinction between “growth occurred” and “whose capacity grew.” Retain the question of whether the observed institutional distribution reflects a planned strategy or unequal resource attraction, while identifying what the data establish and what remains a mechanism to investigate.

Explain that headcount growth is net stock change; it does not itself identify new production, transfers, resignations, retirement, or reclassification. End with the transition to 4.2: increased staff counts acquire policy meaning only in relation to a stated responsibility or denominator.

## 5. Section 4.2.1 — เทียบกับจำนวนประชากร

Retain and verify the analyses already developed in the author's draft.

### Required analysis

- Density for each of the four professions, by workforce scope and population register. Use explicit units and the same denominator when comparing sector contributions.
- Combined physicians and professional nurses for the established international reference comparison. Verify the cited reference's occupational definition, including treatment of midwives, and distinguish the available proxy from the exact reference definition.
- Reconcile age-disaggregated civil-registration totals with published totals and separately recorded groups. Do not assume the entitlement register is a clean superset of the civil register or that all rights categories can be summed without checking.
- Separate the mathematical effect of changing the denominator from the effect of changing the workforce universe.
- Recalculate the author's national and MOPH conditional trend scenarios, including the whole period, recent period, and justified pre-reclassification period. Retain both fixed-population and trend-population scenarios where used. Label assumptions, horizon, and crossing-year rule.
- Verify the CAGR identity for a ratio: `1 + g(W/P) = (1 + gW)/(1 + gP)`. Do not substitute a difference of growth rates except as an explicitly stated approximation.
- Calculate the growth rate needed to reach a chosen reference by a specified date; distinguish it from a recommended recruitment target.

The **4.45 per 1,000** reference must not become an asserted staffing requirement for every province or for MOPH alone. Verify and cite its original purpose using an authoritative source. Report scenarios as conditional arithmetic, not forecasts of the year when every population's need will be met.

Keep national and MOPH comparisons useful: the question is how staff across sectors contribute to population responsibility, under what access conditions, and with what implications for planning.

## 6. Section 4.2.2 — หรือเทียบกับจำนวนบริการ

Preserve the author's argument while ensuring that all quantities and assumptions remain distinct.

### 6.1 Observed activities per staff member

- Recalculate services/staff and, where useful, staff/services for matched or explicitly qualified universes.
- Show physicians and nurses separately for outpatient visits, inpatient days, and SumAdjRW, with long-period and common case-mix-period comparisons.
- Use profession-specific dentistry and pharmacy activities when available: dental services and outpatient prescriptions. Label inpatient days as a proxy for pharmacy workload if used; it is not a pharmacy activity count.
- Re-run the existing HDC coverage checks. Export excluded province-years, the evidence of a coverage break, and sensitivity to the exclusion rule. Do not interpret abrupt reporting expansion as genuine workload growth automatically.
- Maintain the distinction between a team-produced service total divided by staff and measured work performed by individual staff.

### 6.2 Illustrative time conversion

Keep the author's arithmetic illustration where it helps readers see the question, but make its components reproducible:

\[
H_{\rm service}=\frac{U_{OP}\,m_{OP}+A\,m_A}{60},
\qquad D_{\rm service}=H_{\rm service}/h_{\rm day},
\]

where `A` is SumAdjRW per physician and `m_A` is assumed physician minutes per AdjRW **over the entire inpatient episode**. Do not multiply it again by inpatient days.

- Put assumptions such as 10 minutes per OP visit, 90 minutes per AdjRW, 8 hours/day, and 240 days/year in a named scenario table, with sources or an explicit “illustrative assumption” status.
- Use unrounded source values to calculate totals; round only for display. Resolve the approximately 484 versus 460 AdjRW distinction before carrying over an hour/day result.
- Do not present a diagnosis and length of stay as uniquely determining AdjRW. Verify any case illustration against its grouping context. In particular, `30 minutes / 0.3 AdjRW = 100 minutes/AdjRW`, not 90; amend or remove an inconsistent footnote.
- Distinguish a forward conversion of observed services into assumed clinical time from an available-working-time budget. If only 60% of working time is assigned to direct services, use that proportion once, and show what it applies to.
- The direct-care time budget cannot be allocated in full to OP, IP, and every other activity simultaneously. Display the allocation identity if comparing required with available time.
- Report a small sensitivity grid for the uncertain time assumptions. Do not claim that the equivalent days constitute measured total working days, establish spare capacity, or cover unmeasured duty, teaching, administration, and coordination.
- Keep the dentistry/pharmacy illustrations tied to their own activity and time assumptions. A lower activity count can coexist with a high assumed time requirement.

### 6.3 Interpretation and bridge

Retain the critical question about the gap between aggregate averages and difficult working conditions. The mathematical statement is that deviations above and below a common mean balance in total; it does not imply one equally extreme low-workload person for every high-workload person. Aggregate service data do not identify individual workload distribution or prove exploitation by particular groups.

Preserve the author's questions about task allocation, professional hierarchy, bargaining power, and uncounted responsibilities as mechanisms worth examining. End by explaining why observed service volumes omit people who need care but cannot obtain it. This leads to 4.2.3.

## 7. Section 4.2.3 — หรือเทียบกับความจำเป็น

### 7.1 Use this logical sequence

Write this section as a connected argument:

1. Population counts treat people equally; observed services also depend on access and existing capacity.
2. Test how well age, recorded morbidity, economic context, and resources predict observed services.
3. Investigate what the association with supply does and does not reveal about supplier-induced demand.
4. Use the complete validated model to estimate services under a common reference profile; explain exactly what is held fixed and what varies.
5. Compare this result with simpler age weighting, making their different purposes and data windows clear.
6. Explain what additional inputs are required to estimate services that people **should receive**, rather than services predicted under observed relationships.

Do not lead with a long history of failed spline fits and then unexpectedly use a different denominator. Put technical diagnostics in methods or an appendix. The main text must explain the analytical question, the evidence, the decision, and its implication.

### 7.2 Main outcomes and sample

Use three separate outcomes:

1. MOPH hospital outpatient visits per population.
2. MOPH hospital inpatient days per population.
3. SumAdjRW per population in the verified case-mix reporting universe.

Exclude Bangkok before constructing model samples. Use morbidity years actually available, expected to be 2022–2025. Check the original numerator and denominator of every prevalence variable and its unit; do not confuse percentages with proportions.

The primary comparison should use a common complete-case provincial panel across the covariates of M5 and, if feasible, all three outcomes, so differences between model stages are not changes in the sample. If outcome-specific coverage makes a common three-outcome panel impractical, use a common sample within each outcome and provide a common-three-outcome sensitivity. Document every exclusion.

An earlier analysis had approximately 302 province-years. Treat this as an audit clue, not a target sample size. Export the eligible rows and the reasons any of the expected 76 × 4 rows are absent.

### 7.3 Required cumulative model sequence

The primary specification is a regression of the observed **service rate per person**, matching the latest report's analysis. Use OLS as the transparent primary reconstruction, with a positive-mean alternative as a specified sensitivity when appropriate.

| Model | Variables added to the previous model | Cumulative interpretation |
|---|---|---|
| M0 | Intercept and year indicators | Differences associated with the observation year. |
| M1 | Age composition: ages 0–14 and 60+, with 15–59 as the omitted group | Year plus three-group age structure. |
| M2 | Recorded prevalence of diabetes, hypertension, CKD stages 3–5, COPD, stroke, and coronary heart disease | Add diagnosed morbidity. |
| M3 | Log GPP per capita from the preceding year | Add measured economic context. |
| M4 | Log beds per population in the appropriate service universe | Add physical service capacity. |
| M5 | Log physicians per population **and** log professional nurses per population | Add workforce jointly, retaining M4 beds and all earlier terms. |

Thus **M4 does not contain physician or nurse density; M5 contains both, in addition to beds**. Do not reuse the old combined beds/physicians M4 under the same label.

For outcome `k`, the primary M5 can be written as:

\[
y^k_{pt}=\alpha^k+\delta^k_t
 +\boldsymbol\beta^k_A\boldsymbol s_{pt}
 +\boldsymbol\beta^k_D\boldsymbol d_{pt}
 +\gamma^k\log(GPP_{p,t-1})
 +\theta^k_B\log(B_{pt}/P_{pt})
 +\theta^k_M\log(M_{pt}/P_{pt})
 +\theta^k_N\log(N_{pt}/P_{pt})+\varepsilon^k_{pt}.
\]

`p` is province, `t` is year, `s` contains the two included age shares, `d` contains the six recorded prevalence measures, and `B`, `M`, `N` are beds, physicians, and professional nurses. State any units used inside the density transformations. Use beds from the case-mix universe for the AdjRW outcome if that is the genuinely matched measure, and document the difference.

Use proportions or percentage-point units consistently. Omit one age share when including an intercept; all age shares sum to one. Province-year records are observations; the model does not replace the province's age distribution with mean age. No fabricated individual-level age or service records are needed.

### 7.4 Validation and comparison

**Primary question: can the model predict service rates in provinces not used for fitting?**

- Use province-grouped five-fold cross-validation, repeated ten times with recorded seeds. Keep all years of each province together.
- Reuse exactly the same eligible rows and fold assignments across M0–M5 for each comparison.
- Fit any scaling, imputation, feature selection, or regularization only inside the training data. Avoid imputation where the underlying coverage issue is not random missingness.
- The transparent primary fit treats province-years equally. If population weighting is used as a sensitivity, identify the change in estimand and do not replace the primary results silently.
- Export individual out-of-fold predictions, fold assignments, and training-baseline predictions, not just mean scores.
- Report MAE, RMSE, predictive R², and incremental squared-error reductions. If reporting MAPE, state the zero/small-outcome rule and do not make it the sole metric.
- Define predictive R² explicitly. To reconstruct the previous analysis, use a training-mean baseline:

  \[
  R^2_{\rm pred}=1-
  \frac{\sum_{r,f}\sum_{i\in test_{rf}}(y_i-\hat y_{i,rf})^2}
       {\sum_{r,f}\sum_{i\in test_{rf}}(y_i-\bar y_{train_{rf}})^2}.
  \]

  Also explain if any software-default R² with a test-set mean is supplied. Never mix these definitions in one comparison table.
- Calculate an increment as `100 × (SSE_previous − SSE_next) / SSE_previous`. It is not the same as an R² percentage-point change or a causal share of service production.
- Quantify uncertainty in paired model comparisons by resampling provinces, respecting repeated years and paired out-of-fold errors. Do not count the same province's predictions across ten repeats as ten independent samples. State whether an interval conditions on the existing fits or refits the entire procedure.
- Include limited, meaningful ablations of M5, such as removing morbidity, beds, physicians, or nurses, to assess redundancy and instability. Assess the two workforce variables jointly before over-interpreting their separate coefficients.
- If a simpler specification predicts better, report it. M5 remains the agreed full reference specification; it need not be described as the best possible predictor.

**Separate question: can the model predict a later year?**

Run temporal validation where the available years permit, including a last-observed province-rate baseline. Distinguish:

- Prediction of a held-out year's service using that year's already-observed covariates: conditional retrospective prediction.
- Genuine forward prediction using only information available before that year.

Categorical year coefficients for an unseen year cannot be estimated from the training years. Specify a coherent temporal variant, such as an explicitly fitted time trend or a fixed last-observed year effect, and label it separately from the primary grouped-validation specification. Apply the same rule to every competing model. Do not use held-out outcomes to estimate a future year effect.

Report if persistence performs better. Spatial predictive success does not establish long-term forecasting performance.

### 7.5 Supply and the supplier-induced-demand question

Give this question a real analytical subsection, not merely a disclaimer.

1. Describe unadjusted service–capacity relationships and the predictive contribution of beds and workforce in M4 and M5.
2. Estimate associations between services and supply across provinces, then within provinces over time with province and year fixed effects, on clearly matched samples.
3. For a multiplicative specification, use a log link for expected totals with a population offset and logged supply densities. PPML can accommodate nonnegative service totals, including noninteger positive totals such as SumAdjRW under a quasi-likelihood interpretation. Use province-clustered inference and inspect convergence/separation.
4. Show joint models of beds, physicians, and nurses and a small set of informative reduced specifications if collinearity makes attribution unstable. Do not choose coefficients based on preferred signs.
5. Compare a long panel using variables available throughout with the shorter morbidity-adjusted panel. Explain differences in sample and adjustment before comparing coefficients.
6. Inspect time variation, correlated age shares, stock changes, and reporting breaks. Low residual variation can weaken identification; it does not by itself prove that a variable has no effect or that the model is impossible.
7. Where feasible, examine lagged supply as a sensitivity. A lagged regressor is not automatically exogenous or a valid instrument.

Be precise about coefficient units. With logged supply density and a log link, the coefficient is an elasticity; with a level/proportion covariate and a log link, it is a semi-elasticity. For a 10% increase in a logged regressor, report `100 × (1.1^beta − 1)` and transform confidence limits accordingly.

A positive supply–service association is consistent with several mechanisms: previously unmet demand gaining access, capacity following need or referrals, facility specialization, and provider influence over utilization. A coefficient alone does not separate them. A wide within-province interval or a changed sign is not proof that the true effect is zero, nor proof that “all of the relationship is between provinces.”

Assess whether the repository actually contains a credible policy change, instrument, allocation discontinuity, payment change, or referral information supporting a causal design. If it does, describe identification assumptions and implement a proportionate design. If it does not, conclude directly that **the current data estimate supply–service associations but do not identify supplier-induced demand causally**. Specify the minimum additional evidence needed; do not invent an instrument.

### 7.6 M5 standardization: use the full model

This must answer the author's question about whether the “weighted population” uses only age coefficients or every term of M5.

For each service outcome, use the **complete fitted prediction function**, including the intercept and all model terms. Preserve each province-year's population, age composition, and recorded morbidity. Hold economic context, beds, physician density, nurse density, and the year effect at one declared reference profile:

\[
\hat r^{k,*}_{pt}
=f^k_{M5}(\boldsymbol s_{pt},\boldsymbol d_{pt},
 GPP^*,b^*,m^*,n^*,t^*),
\qquad V^{k,*}_{pt}=P_{pt}\hat r^{k,*}_{pt}.
\]

The full model contributes to the prediction even when some covariates are fixed. This is not “multiplying population by every regression coefficient,” and it is not using age alone.

Use the previously agreed 2023 reference as the starting specification if coverage supports it; verify rather than force it. For a national-density reference, calculate pooled beds/staff divided by pooled population, then apply the model's transformation. Specify whether the GPP reference is a population-weighted level followed by a log transformation. Do not silently switch between the mean of logs, the log of a mean, and a median.

The lag definition still applies to the reference profile: a 2023 model-year reference uses the GPP year implied by the fitted one-year lag, not an unnoticed substitution of contemporaneous GPP. If the profile is pooled across the 76 included provinces, describe it as that analytical population's reference rather than a total including Bangkok.

Hold the reference **constant across provinces and all comparison years**. Do not reset it annually: that would remove part of the change being measured. Export the complete numerical reference profile and its source sample.

For a common base year `b`, convert each service-specific standardized total into equivalent population units as:

\[
\bar r^k_b=\frac{\sum_p V^{k,*}_{pb}}{\sum_p P_{pb}},
\qquad E^k_{pt}=\frac{V^{k,*}_{pt}}{\bar r^k_b}.
\]

Then `sum(E_b) = sum(P_b)`, and the index is `100 × sum(V_t)/sum(V_b)` on the same province coverage. This normalization must remain fixed. Keep OP-, inpatient-day-, and AdjRW-based denominators separate; do not add their incompatible units or silently average them into a universal need score.

Required diagnostics:

- A balanced set of provinces for time comparisons, with the all-available sample shown separately. If 2023–2025 covers all 76 provinces and a longer window covers fewer, display that distinction explicitly.
- Positive, finite predictions and denominators. Inspect all negative/zero predictions from OLS. Do not replace them with a small constant to make ratios work.
- A positive-mean model sensitivity when needed. Any switch of prediction model changes the estimand/fit and must be reported and validated, not hidden.
- Marginal and joint support checks for the standardized covariate profile; being inside each variable's range alone does not guarantee a plausible joint profile.
- Province-cluster bootstrap uncertainty with model refitting, preferably at least 500 valid replicates, recording failed or invalid replicates. Hold the declared scenario reference fixed for conditional model uncertainty; label a separate procedure if its estimation uncertainty is also propagated.
- Service-specific acceptability decisions. Do not discard every outcome because one fails, and do not certify a problematic outcome because the other two succeed.

Name the result **model-standardized expected utilization** or an equivalent precise Thai term. It reflects the population and morbidity profile under a common modeled reference. It is not a direct measurement of all health need, an estimate of unmet need, or a causal result of equalizing resources. Diagnosed prevalence can still reflect diagnostic access and reporting.

Once supply densities are fixed, provincial variation in the standardized denominator must not directly reuse each province's observed physician or nurse count. Add a verification that changing observed supply alone, while the standardized profile remains fixed, does not change its standardized prediction. Do not use fitted values at actual provincial supply as a supposedly supply-neutral denominator in 4.3.

### 7.7 Age-only weights: a separate question and decision

Retain a compact comparison with age-only weighting because it offers a longer time series and a simpler demographic interpretation. It must not silently replace the M5 analysis or be presented as its output.

Answer these two questions separately, for OP, inpatient days, and AdjRW:

1. **Does age composition improve prediction?** Use the paired M0–M1 out-of-sample comparison, uncertainty, and temporal evidence where available.
2. **Can stable age-specific relative rates be estimated for use as a planning denominator?** Use identification and stability checks appropriate to that separate estimation task.

A predictive improvement does not establish that age-specific service rates have been identified. OLS coefficients on age shares are contrasts with an omitted group; they are not automatically nonnegative age-specific rates or ready-to-use weights.

For the second question:

- Check whether age-specific utilization or a defensible external reference schedule is actually available in any newly supplied dataset. Say “not available in the project data” when appropriate; do not claim that Thai health records never contain patient age.
- Start with an interpretable three-group specification; use six groups and the earlier spline approach only as informative sensitivities/appendix diagnostics, not an obligation to prefer greater complexity.
- State the rate-estimation equation, reference year/group, positivity constraints, treatment of year effects, and normalization. Separate a data-estimated schedule from assumed flat/moderate/steep scenarios.
- Inspect collinearity, boundary solutions, bootstrap intervals, dependence on age grouping, reference-group instability, and sensitivity to service universe and period. Document acceptance criteria before interpreting results; justify them and do not tune thresholds to obtain a desired verdict.
- A weight of zero is mathematically different from one. Do not replace zeros with ones, normalize by a zero/unstable reference, or describe a boundary estimate as proof that an age group needs no care.
- Failure means “not suitable as a stable denominator from these data and this specification,” not “age is unrelated to service use.”
- Explain within-province residual variation using the actual decomposition if needed: `x_pt = overall mean + province component + year component + remaining variation`. For an unbalanced panel, residualize with the actual fixed-effect design; do not substitute a balanced-panel shortcut.
- The reduction in age-share variance after province/year adjustment concerns the variation available to estimate within-province relationships. It does not show that differences occur below the province level, that provinces are demographically identical, or that a small percentage alone proves non-estimability.

Export a verdict table with `outcome`, `question`, `sample`, `evidence`, `decision`, `permitted_use`, and `reason`. Give direct conclusions: usable, usable only for a stated exploratory purpose, or not usable. Where weights are unstable, still complete the M5 standardized-utilization analysis if it passes its own checks.

### 7.8 Normative need and future model inputs

End by distinguishing the empirical standardization above from a care-based requirement calculation:

\[
\text{eligible people/events}
\times\text{appropriate activities per person/event}
\times\text{coverage target}
\times\text{cadre time per activity}
\longrightarrow\text{required hours/FTE}.
\]

Audit the available prevalence, risk, disability/ADL, oral-health, access, and care-package data. If the inputs support a genuine calculation for selected conditions, implement it with explicit scope, comorbidity/task-sharing rules, and uncertainty. Do not double-count shared visits across conditions or extrapolate a limited package into total national workforce need.

If clinical activity standards or population-based need inputs are absent, produce a populated data-readiness table and a computational schema, not fabricated required-FTE figures. Separate measured inputs, literature-based parameters, and policy choices. Cite the relevant original evidence where using an external standard.

State how later integrated planning would connect population/health states, eligible care, available hours, entry/exit dynamics, allocation, referral, and access. Do not calibrate causal behavioral responses from associations that this analysis did not identify.

## 8. Section 4.2.4 — ตัวหารที่ต่างกันให้ภาพความก้าวหน้าต่างกันอย่างไร

Write a substantive synthesis of 4.2, not a repetition of methods or a list of limitations. The final Thai subtitle may be refined to fit the author's style.

### Required comparison

Build a denominator matrix and a common-period comparison showing, where coverage allows:

| Denominator | Responsibility represented | Main issue for interpretation/planning |
|---|---|---|
| Civil population | People living/registered within the stated population definition | Equal counting does not represent different care requirements. |
| Entitlement population | People registered under the included rights arrangements | Registration and service responsibility may differ from residence. |
| Observed services | Work that entered the reporting system | Access, referrals, capacity, and reporting affect the denominator. |
| Fixed age-weighted population | Demographic change under a stated age schedule | The schedule may be assumed or estimated from access-constrained utilization. |
| M5 standardized expected utilization | Expected services under a common measured reference profile | Still conditioned on observed relationships and recorded morbidity. |
| Normative care requirements, if estimable | Services a defined population should receive under a specified care package | Requires clinical, coverage, time, and allocation choices. |

For the same workforce numerator, quantify how the level, trend, and interpretation change with the denominator. Show the national all-sector view and the MOPH view separately. Do not construct an apparent long-run comparison by splicing a 2022–2025 modeled denominator onto a 2013–2025 observed series. Present long and common short windows side by side.

Discuss consequences for future modeling: a utilization-based projection can perpetuate an access-constrained service pattern; a population model embodies a different responsibility; a need-based model requires explicit judgments about appropriate care and access. The choice is substantive, not just a matter of predictive accuracy.

Conclude with the bridge to 4.3: Sections 4.1 and 4.2 describe national aggregates. The next step tests where growth occurred and whether the apparent progress survives a change in geographical scale and denominator. Prepare the reader for different province priorities without claiming one list is automatically the correct one.

## 9. Section 4.3 — การเพิ่มขึ้นเกิดขึ้นที่ไหน

Create `chapter4_3_distribution_and_inequality.ipynb`. Its purpose is to determine where national growth occurred, how uneven the resulting distribution is, whether initially disadvantaged provinces are catching up, and how the choice of denominator changes policy priorities.

Use four linked questions as the report's structure. Suggested subsections are below; refine the Thai wording for flow.

### 9.1 How did inequality change, and at which observable geographical level?

Analyze all four professions. Compare all-sector and MOPH distributions where the underlying data support both. Use 76 provinces, excluding Bangkok, and show coverage throughout.

For each valid denominator `D`, define provincial density `r_p = W_p/D_p`. Use **denominator-weighted** inequality as the primary population/service-responsibility comparison, with equal-province statistics as a clearly labeled sensitivity.

At minimum calculate:

- Weighted Gini of provincial density.
- Theil T, selected because it has an exact geographical decomposition.
- A readable dispersion measure such as P90/P10 or the proportion of people living in provinces within a specified band around the pooled density. State whether quantiles are province-weighted or denominator-weighted.
- Annual trajectories and endpoint changes, on a stable coverage sample where necessary.

For Theil T, with workforce share `q_p = W_p / sum(W)` and denominator share `d_p = D_p / sum(D)`, use:

\[
T=\sum_p q_p\log(q_p/d_p).
\]

Decompose by health region `g`:

\[
T_{between}=\sum_g Q_g\log(Q_g/D_g),\qquad
T_{within}=\sum_g Q_g T_g,\qquad
T=T_{between}+T_{within},
\]

where `Q_g` and `D_g` are regional workforce and denominator shares. For Theil T, the within-region component is weighted by **regional workforce shares**, not arbitrarily by population shares. Verify this identity computationally.

Use the continuous limit for a zero-workforce contribution where defined. Positive workforce with a zero denominator makes the ratio/decomposition problematic; report the affected observations and an explicit analytical decision instead of adding an undocumented epsilon. Model-derived denominators must have passed their positivity and stability checks.

These statistics describe the distribution of recorded provincial totals. When the underlying records cover the full reporting population, there is no automatic sampling confidence interval to attach to an observed Gini. Distinguish coverage/measurement sensitivities, uncertainty propagated from a modeled denominator, and any explicitly justified superpopulation inference.

Describe the geographical levels accurately:

- Between health regions.
- Between provinces **within** a health region.
- Within a province only if independently adequate district/facility-level data exist with usable denominators and coverage.

Province-level data cannot identify within-province inequality. A facility-level staffing file does not automatically supply catchment populations or comparable service responsibilities. If sufficient finer data exist, add a separate extension with its own coverage audit; otherwise state the unresolved level without inventing it.

Do not label an index “low” or “not as high as expected” without a stated comparison or benchmark. A small provincial aggregate index can coexist with large individual workload differences and unobserved within-province concentration. Report the observed change and where it is concentrated.

### 9.2 Which gaps did the observed growth tend to narrow?

Compare inequality in staff relative to:

- Civil population and entitlement population.
- An accepted fixed age-weighted population, or explicitly assumed age scenarios if empirical weights fail.
- Observed services appropriate to the profession.
- M5-standardized service-specific equivalent populations over their valid short window.

For physicians and nurses, examine OP, inpatient-day, and AdjRW responsibility separately. For pharmacists and dentists, prioritize pharmacy/dental activities. Broad OP or inpatient totals may be contextual sensitivity measures, but cannot become validated direct workload measures for those professions. Do not simply apply physician M5 weights to dentistry or pharmacy and call them profession-specific need.

Use matched scope, years, and province coverage for each denominator contrast. Quantify:

1. Changes in inequality under each denominator.
2. Changes in provincial workforce shares relative to population/service shares.
3. Whether initially low-density provinces received larger proportional or absolute increases.
4. Contributions of changes in staff distribution and denominator distribution, using a transparent counterfactual/Shapley decomposition if making an attribution claim. Report interaction/order dependence if using a simpler sequential decomposition.

If inequality falls more against services than against population, describe the observed allocation pattern as more closely aligned with service volume. Do not infer policymakers' intentions or a proven causal allocation rule from this pattern alone.

### 9.3 Are provinces catching up, and what would convergence require?

Separate **distributional convergence** from **growth in the overall workforce level**.

- Sigma convergence: does dispersion in density decline over time?
- Beta convergence: do provinces with lower initial density subsequently grow faster? Fit a transparent relationship between annualized log density change and initial log density, report uncertainty, and explain that beta convergence need not imply falling dispersion.
- Examine regression-to-the-mean and baseline measurement error with a justified alternative baseline, such as a multi-year starting average, and a recent/pre-break period comparison.
- Where useful, compare convergence within health regions and by profession/sector without multiplying weak subgroup models unnecessarily.

Do not promise a finite year of exact equality. Define an interpretable **near-equality criterion** before making conditional projections, such as a configurable density band, Gini threshold, or P90/P10 threshold. Label it as an illustrative policy choice, not a scientifically established optimum. Show the starting value and whether the criterion is reached within the stated horizon; “not reached under these assumptions” is a valid result.

Use a small set of transparent scenarios, preferably over a 20-year horizon from the last complete observed year:

1. **Aggregate growth only:** retain initial workforce shares, subject to the stated population path.
2. **Redistribution only:** hold the aggregate stock fixed while gradually changing shares toward the selected denominator shares.
3. **Growth plus redistribution:** combine an explicitly stated aggregate growth assumption with a share-adjustment rule.

One reproducible illustrative rule is:

\[
q_{p,t+1}=(1-\lambda)q_{pt}+\lambda d_{p,t+1},
\qquad W_{p,t+1}=W_{total,t+1}q_{p,t+1}.
\]

Explain the choice of `lambda`: a policy scenario is different from an estimate of historical convergence. If estimating it, propagate uncertainty and retain evidence of no convergence/divergence rather than forcing a positive speed. Use aggregate growth assumptions appropriate to the profession, sector, and period from 4.1/4.4.

This share rule may imply removing posts from some provinces. Label it as an unconstrained distribution scenario; add an additions-only comparison if drawing practical allocation conclusions. Do not present a mathematical redistribution as an implementable staffing plan without transfer, attrition, minimum-service, and capacity constraints.

For each scenario, export provincial counts/densities, total stock, inequality, and proximity to the chosen threshold. Under fixed denominator shares, uniform proportional growth should leave relative inequality unchanged; use this as a meaningful validation check. Where demographic projections are unavailable, distinguish fixed population and documented trend assumptions instead of presenting them as official forecasts.

A more equal distribution can still be uniformly inadequate, and a higher aggregate density can coexist with persistent relative gaps. Preserve this distinction in figures and prose.

### 9.4 Do policy-priority provinces change when the denominator changes?

Make this a central result, not a footnote.

For a common latest-year sample:

- Calculate the density relative to the pooled density for each denominator:

  \[
  R_p=\frac{W_p/D_p}{\sum W/\sum D}.
  \]

- Rank provinces and identify the lowest-density quartile. With all 76 provinces this contains 19; document a deterministic tie rule and show sensitivity to near-boundary ties.
- Compare lists using intersection counts, Jaccard overlap, rank correlation, and a rank-change/priority-membership figure.
- Compute an illustrative proportional-allocation difference `sum(W) × D_p/sum(D) − W_p`. Call it a gap relative to the chosen proportional rule, not a proven absolute shortage or surplus.
- Retain the earlier six-way comparison when valid: population, entitlement population, fixed age-equivalent population, OP visits, inpatient days, and AdjRW. Identify the exact six definitions. If an age denominator fails the new gate, report that limitation and provide the clearly labeled scenario alternative; do not retain a headline of “all six” without valid underlying definitions.
- Extend the comparison with the separate M5 OP/IP/AdjRW standardized denominators. Replace legacy `m4_*` artifacts; do not silently relabel their old values as M5.
- For model-derived priorities, propagate model uncertainty and show the probability/frequency of belonging to the priority group when feasible. A province just outside a hard cutoff may not differ meaningfully from one just inside it.

Use province examples grounded in the rerun. Investigate **Bueng Kan**, including whether it remains a priority under all specified denominators, and select additional provinces whose classification changes substantially. Earlier examples involving Amnat Charoen, Kamphaeng Phet, Loei, and Chaiyaphum are hypotheses to verify, not a required five-province list.

Also explicitly verify the author's **Pathum Thani and Narathiwat** question:

- Plot population per physician on the x-axis and OP visits per physician on the y-axis, using the same physician denominator and institutional scope.
- Label these provinces and report their original staff, population, visits, both ratios, and visits per population.
- Use the identity `y/x = OP visits/population`. Overlay meaningful constant service-per-population lines if helpful.
- Inspect the corresponding nurse/service pattern where useful.
- Explain that a low service/population ratio in these sources may reflect access, referral, provision outside the measured universe, population-register differences, or reporting. A shared staff denominator can induce correlation in the scatter; the plot does not establish a causal staffing effect.

### 9.5 Policy interpretation and transition

Retain the author's critical question: if additional staff are allocated only after a place demonstrates service volume, can an initially low-capacity area ever generate the work required to qualify?

Also recognize genuine referral and complex-care responsibilities. Ask whether the current location of major hospitals is being treated as an unchangeable assumption, and distinguish allocating basic/primary-care responsibility from allocating referral-intensive specialist services.

Do not imply that every high-volume province should reduce services or that equal per-capita staffing is the unique equitable solution. Show the implications of different responsibilities and choices. End by asking how growth and redistribution are sustained through recruitment, transfers, and retention, introducing 4.4.

## 10. Section 4.4 — การเพิ่มขึ้นเกิดขึ้นได้อย่างไร

Create `chapter4_4_entries_exits_and_growth.ipynb`. Explain stock growth as a balance of recorded entries, recorded exits, and the differences that remain when sources do not fully reconcile. Link this directly to 4.1 growth and 4.3 geographical distribution.

### 10.1 Parse actual entries and exits

Read `enter_moph.xlsx` and `loss_moph.xlsx` from their original sheets. Inspect headers, units, fiscal years, employment categories, profession groups, central rows, province rows, subtotals, and totals before reshaping them.

Required safeguards:

- Accommodate changing multi-row headers and column locations across sheets. Do not assume a fixed column number has the same meaning in every year.
- Preserve original event categories. Entries may include recruitment/hiring, reinstatement, and transfers in; exits may include resignation, retirement, transfers out, death, and other categories according to the actual form.
- Distinguish an employment event from a unique individual or newly qualified graduate. Inspect whether employment-status conversion or multiple records per person can affect counts.
- Analyze the four main professions, but use other profession/overall totals where helpful to audit the form.
- Exclude Bangkok and central administrative units from the provincial analysis, showing any excluded totals separately.
- Exclude a partially observed fiscal year from full-year trend/rate comparisons. The previously supplied entry workbook was extracted on 5 March 2026; verify metadata before treating its FY2026 sheet as complete.
- Preserve a flag for original blanks. Treat blanks as zero only where the form and reconciliation justify “no recorded event”; otherwise keep them missing.
- Check component-to-profession totals and province-to-published totals independently. Do not assume a published grand-total formula is correct.

Previous parsing identified two issues to recheck in the actual files: a one-event difference in the FY2020 dentist/grand totals, and an FY2022 overall-total formula that omitted nursing components. Preserve the raw workbook and record any analytical correction in an audit table. Prefer validated component sums to an incorrect footer, explaining why.

Export the event-level long table, province-year-cadre summaries, parsing decisions, and workbook reconciliation checks.

### 10.2 Reconcile the stock-flow identity before interpreting mechanisms

For a genuinely matched scope and timing:

\[
W_{pt}-W_{p,t-1}=I_{pt}-O_{pt}+A_{pt}.
\]

Here `A` is the residual/adjustment needed to reconcile observed stock with recorded flows; it may include scope/timing differences, reporting changes, reclassification, and unmeasured movements. It is not automatically a substantive category such as “hidden hiring.”

First search for stock data matching the OPS employment-event universe. Compare it with the broad MOPH series used in 4.1. If only a broader or differently timed stock is available, retain the calculation as a **reconciliation diagnostic**, with the mismatch explicit. Do not equate the residual with an identified cause.

Show the identity annually and over the matched full period, for each profession and province. Calculate:

- Initial/final stock and change.
- Recorded entries by category.
- Recorded exits by category.
- Recorded net flow `I − O`.
- Residual `ΔW − (I − O)`.
- Number and size of unreconciled province-years, and cases in which net-flow and stock-change signs disagree.

Near-zero national residuals can conceal large offsetting provincial residuals. Show their distribution and identify material outliers before telling a recruitment/retention story.

Do not back-calculate entries as `ΔW + O` now that actual entry records are available. That quantity may be shown as an implied-flow diagnostic only, beside observed entries and the residual.

### 10.3 Match flows to CAGR and geographical growth

For flow years 2017–2025, for example, use stock at 2016 and 2025 and nine elapsed intervals:

\[
CAGR_{2016\rightarrow2025}=(W_{2025}/W_{2016})^{1/9}-1.
\]

Verify the actual complete period rather than forcing these dates. Show the original 2013–2025 CAGR from 4.1 alongside the period-matched CAGR; explain that they answer different time-window questions.

Use transparent event intensities, such as events per 100 prior-year staff and period events divided by the sum of eligible prior-year stocks. Label the exposure as an approximation where the stock does not match the event universe.

`Exits / entries` is a replacement-pressure description, not a cohort attrition rate. Without linked individuals, do not estimate survival, tenure-specific retention, or the probability that a newly hired person will leave from these aggregates.

Compare:

- High recruitment with high exits versus high recruitment with low exits.
- Slow growth from low intake versus slow growth despite substantial replacement activity.
- Provinces with rising stock but high recorded turnover.
- Professions and provinces with falling stock despite positive recorded net flows, emphasizing reconciliation limits.
- Entry/exit intensity across **baseline** density groups and the priority lists in 4.3. Do not group only by final growth and then present the association as independent evidence of its cause.

Use matched provincial scatterplots/correlations and small explanatory tables. Shared denominators and algebraic links among growth and flow measures constrain interpretation; a strong correlation is not a causal decomposition of growth.

### 10.4 Workload, economic context, and entries/exits

Answer directly: **how strongly is prior reported workload associated with subsequent recorded hiring, entry, and exit?** Keep causal language separate.

Analyze actual event counts. Use a suitable count-mean model such as PPML with province and year fixed effects and province-clustered inference. Predefine the primary specification before comparing results. A useful form is:

\[
\log E[F_{pct}|X]
=\log W_{pc,t-1}+\alpha_{pc}+\delta_t
 +\boldsymbol\beta\,\boldsymbol L_{pc,t-1}
 +\boldsymbol\gamma\,\boldsymbol Z_{p,t-1},
\]

where `F` is one event type, `L` contains the justified workload measures, and `Z` contains prespecified context variables. Estimate professions separately unless a pooled model has explicit profession interactions and a clear purpose.

Primary outcomes should include total recorded entries, recruitment/hiring, resignations, and total exits where comparable. Keep resignation distinct from retirement and transfer. Analyze major exit components descriptively; fit additional component models only if counts and coverage support them.

Workload measures must match the profession:

- Physicians: OP visits and inpatient days/AdjRW per physician, with a limited set of joint or alternative specifications.
- Nurses: inpatient days/AdjRW per professional nurse, with other services only where the task relationship is defensible.
- Pharmacists and dentists: use their own activity data if time coverage supports lagged analysis. If not, report the missing coverage and still complete their descriptive entry/exit/growth analysis; do not manufacture workload measures by dividing arbitrary OP totals by their headcounts.

Use lagged economic context and other defensible confounders available in the data, with a rationale. Do not add every variable merely because it exists. Beds, workforce, workload ratios, and population can be highly related; inspect collinearity and avoid disguising weak identification with many controls.

An earlier implementation included both `log(lagged stock)` as an offset and an additional freely estimated `log(lagged stock)` term. If reproducing it, state that the effective stock elasticity is `1 + beta_stock`; the extra term relaxes the unit-exposure assumption. Compare with the offset-only version as a targeted sensitivity and record which is primary. Do not describe the two specifications as identical.

Required reporting:

- Sample years, provinces, observations, lag construction, and omitted rows.
- Convergence/separation diagnostics, clustered confidence intervals, and relevant residual/overdispersion checks. PPML does not require the conditional variance to equal the mean when robust inference is used, but it still requires a credible conditional-mean specification.
- The expected percentage difference in event counts for a 10% difference in workload when using a logged workload term: `100 × (1.1^beta − 1)`, with transformed confidence bounds.
- A clear statement of whether the primary interval supports a positive association, a negative association, or remains inconclusive about direction. Do not translate an interval spanning zero into proof of no relationship.
- Predicted event-count differences for a clearly stated reference exposure if they materially improve interpretation.
- A distinction between retrospective association and forecasting performance if any predictive claim is made.

Run only sensitivities that address concrete concerns: aligned shorter AdjRW years, an alternative workload unit on the **same** sample, documented COVID/reclassification/reporting periods, a lag specification, and influence of a materially problematic province. Do not select years or models to obtain significance. Fiscal/report-year misalignment must remain visible when discussing temporal order.

Earlier primary workload models had intervals crossing zero; a few shorter-window hiring results were more positive. Treat this as a reproducibility check, not an expected outcome. Report changed conclusions honestly if the revised data or specification support them. Avoid turning an isolated significant sensitivity into the main finding.

### 10.5 Interpretation and model-readiness handoff

Connect back to the earlier sections: producing or recruiting more people can raise stock, yet repeated replacement, unequal access to recruits, transfers, and institutional reclassification may shape where the increase appears. The same CAGR can arise from very different entry/exit patterns.

Distinguish clearly:

- What the recorded flows establish.
- What stock-flow reconciliation does not yet resolve.
- What workload/economic associations support.
- What causal responses cannot be inferred from these data.

Produce a future-model parameter table: quantity, definition, scope, period, estimate, uncertainty, evidence type, permitted use, and missing inputs. Empirical event intensities can inform baseline scenarios with stated limitations. An observational workload coefficient must not become an established causal attrition response to workload reduction.

Where transfers in/out are separately identified, preserve them as geographical redistribution flows. Internal transfers may cancel nationally only within the same organizational boundary and period; do not count every provincial transfer-out as a loss from the national workforce. Do not infer province-to-province transfer routes without origin–destination records.

End the section with policy choices about recruitment, retention, allocation, and responsibilities across institutions, rather than reducing the explanation to “produce more.”

## 11. Report writing: preserve the author's critical voice

Write the report in **Thai**. Write technical documentation in English or Thai according to existing repository conventions, but keep terminology consistent. The four primary notebooks should explain their questions and conclusions in Thai so the author can work directly with them.

The author wants connected, critical prose that gives readers a reason to reconsider familiar policy narratives. Follow this approach:

1. Begin each subsection with the substantive question, then the result, then the evidence needed to understand it, then the policy implication.
2. Preserve the distinction between empirical findings, conditional calculations, and questions about institutional mechanisms. State each confidently within its actual evidential scope.
3. Integrate material qualifications where they change interpretation. Do not append repetitive defensive paragraphs that weaken every point.
4. Explain technical methods only to the extent needed to understand the conclusion; move full specifications and diagnostics to methods/appendices.
5. Do not infer adequacy from rising density, overstaffing from an average below an illustrative hours threshold, deliberate policy intent from a distributional correlation, or exploitation by named groups from aggregate ratios.
6. Do not let physicians become the sole subject. Identify when findings differ for professional nurses, pharmacists, and dentists, and when a particular measure is only appropriate for one profession.
7. Keep “who receives resources, for which responsibilities, under whose allocation rules” visible throughout. A model's accuracy does not decide society's desired distribution.
8. Avoid saying that the study “proved” a causal effect when it estimated an association. Use direct conclusions rather than vague caveats: for example, the present data do not identify supplier-induced demand, or the estimated age schedule is not stable enough to serve as a denominator.
9. Make transitions cumulative: counts in 4.1 → meanings of denominators in 4.2 → geography in 4.3 → flows and sustainability in 4.4.

Write 4.2.3 and 4.2.4 as part of the same 4.2 report, not detached appendices. Write 4.3 and 4.4 as complete sections with introductions, connected findings, selected province examples, and closing transitions.

Preserve useful author-written paragraphs rather than rewriting the entire chapter into generic prose. Correct factual or logical inconsistencies, recording material edits. Do not carry forward an old conclusion if the rerun changes its basis.

### Closing argument

The chapter's conclusion should show why numerical analysis produces concrete planning options while leaving substantive choices open. It can ask whether existing allocation rules close inequality or reproduce it, and what rules society is prepared to change. Tie that question to the actual chapter findings: differences between institutions, denominators, provinces, and recruitment/retention patterns. Avoid a philosophical conclusion disconnected from the results.

## 12. Figures, tables, insertion placeholders, and numeric traceability

### 12.1 Stable analytical IDs and report numbering

Give every table and figure a stable ID independent of its final printed number, for example `T423_MODEL_VALIDATION` or `F434_PRIORITY_SWITCHES`. Generate a final numbering map after the report structure is settled. This avoids stale references when the new sections change figure order.

Use explicit insertion markers in the working Thai report, for example:

> [ตำแหน่งตาราง T423_MODEL_VALIDATION: ความสามารถในการทำนายบริการของ M0–M5 แยกผู้ป่วยนอก วันนอนรวม และ AdjRW; แสดง R² ตามนิยามที่ระบุ จำนวนจังหวัด–ปี และผลเปรียบเทียบความคลาดเคลื่อน]

> [ตำแหน่งรูป F434_PRIORITY_SWITCHES: การเปลี่ยนกลุ่มจังหวัดที่ควรให้ความสำคัญเมื่อเปลี่ยนตัวหาร; ใช้จังหวัดและขอบเขตบุคลากรชุดเดียวกัน พร้อมระบุบึงกาฬ ปทุมธานี และนราธิวาสตามผลที่ตรวจสอบแล้ว]

Each placeholder must map to a generated asset, source table, caption, notebook section, and status. Do not leave numerical `xxx` placeholders where data are available. A genuinely unavailable analysis requires a specific explanation and data request, not fabricated rows.

### 12.2 Main-text asset plan

Choose a readable subset for the report and place detailed diagnostics in the appendix. At minimum cover these analytical functions:

| Section | Main table/figure functions | Place in narrative |
|---|---|---|
| 4.1 | Cadre/sector trajectories; growth versus absolute contribution; OP persons/frequency; inpatient volume/case mix | Immediately after each corresponding finding. |
| 4.2.1 | Alternative population-register densities; national/MOPH conditional reference scenarios | After explaining scope and denominator changes. |
| 4.2.2 | Services per staff by profession/measure; time-assumption sensitivity; dental/pharmacy activity trends | After measured ratios, before the interpretation of workload averages. |
| 4.2.3 | M0–M5 specification and validation; paired predictive increments; supply-association comparison; fixed-reference M5 trends; age-weight verdict | In that order, as the argument moves from prediction to interpretation and standardization. |
| 4.2.4 | Same workforce, alternative denominators and time windows; policy-meaning matrix | Before the transition to provincial analysis. |
| 4.3 | Inequality trends; Theil region decomposition; convergence/scenario comparison; priority-list changes; province verification scatter | Along the four substantive questions. |
| 4.4 | Stock/entry/exit/residual reconciliation; flow composition; matched CAGR/flow patterns; workload association estimates | From accounting identities to possible mechanisms. |

Possible figures may combine related panels, but avoid overfilled charts with many professions, sectors, denominators, and years competing in one panel. A table is preferable when exact values are the main point.

### 12.3 Export and visual requirements

- Research figures should use a white background, legible Thai fonts available to the project, consistent colors and labels, and explicit units, years, scopes, and sample counts where relevant.
- Export main figures in PNG at publication-appropriate resolution and SVG or PDF for editing/printing.
- Export every plotted dataset to CSV, including values before and after indexing, base year, denominator, scope, scenario, and uncertainty bounds.
- Save tables as CSV UTF-8 with BOM and as a section workbook with Excel-compatible sheet names.
- Visually inspect rendered figures and the final DOCX. Fix clipped Thai labels, missing glyphs, crowded legends, ambiguous scales, and detached captions.
- Do not use dual axes to imply a relationship between unrelated scales. Identify logarithmic axes and meaningful reference lines.
- If using a provincial map, verify province geometry/codes and do not fill missing provinces with zero. Maps are optional; a sorted plot may communicate the question better.

### 12.4 One source for report numbers

Create a small claim/value registry linking each important numeric claim to:

`claim_id`, report location, table and row keys, variable, full-precision value, display format, unit, scope, years, sample, and status.

Keep editable Thai prose in templates or another simple authoritative text source. Insert numeric values from the registry. Rebuild the report when outputs change, and flag substantive conclusions requiring editorial review. Do not automatically preserve phrases such as “increased,” “significant,” or “all six provinces” when the corresponding results change.

Reconcile tables, figures, notebook commentary, captions, and final prose. A stale paragraph beside an updated table is a failed deliverable.

## 13. Concrete outputs to create

### 13.1 Shared outputs

- Data/source catalog and variable dictionary.
- Source and scope crosswalk, province/region crosswalk, and analytical eligibility flags.
- Canonical normalized tables and versioned/shared panel metadata.
- Source coverage, missingness, joins, exclusions, and reconciliation audits.
- Denominator registry, including definitions, permitted uses, reference profiles, and uncertainty status.
- Run manifest: timestamp, code revision if available, input hashes, dependency versions, effective configuration, random seeds, and generated outputs.

Use build metadata or hashes to identify versions rather than producing many ambiguously named copies such as `final_v2_new_latest`.

### 13.2 Section outputs

| Section | Essential analytical exports |
|---|---|
| 4.1 | Annual workforce/service tables; endpoint/CAGR summaries; sector growth contributions; service-composition identities; coverage/break diagnostics. |
| 4.2 | Population-register reconciliation; density/scenario tables; activity and time assumptions; service/staff ratios; model input/specification/fold/prediction/metric tables; association results; standardization reference and predictions; age-weight verdict; denominator comparison; need-readiness table. |
| 4.3 | Annual inequality by scope/cadre/denominator; region decomposition; staff/denominator change decomposition where used; convergence estimates; conditional scenarios; province ranks, allocation differences, list overlaps, priority uncertainty, and selected-province source checks. |
| 4.4 | Parsed entry/exit events; workbook-total checks; matched stock-flow panel; national/provincial residuals; period-matched CAGR and flow intensities; model specifications, coefficients, effect-size tables, diagnostics, and future-model parameter status. |

For each section, deliver:

1. The canonical, executed notebook.
2. Tables and a consolidated `.xlsx` workbook.
3. Main and supplementary figures with plot data.
4. Thai report text, captions, methods notes, and a placeholder/asset map.
5. A short section-specific findings and unresolved-data summary, generated from the current results.

### 13.3 Integrated report and handoff

Deliver:

- `reports/chapter4_complete_th.md`, with the full connected 4.1–4.4 text and insertion markers.
- `reports/chapter4_complete_th.docx`, using the author's report style and current captions/numbering. Insert the main assets where practical, or retain clear matching insertion markers for author placement. Preserve the supplied original DOCX.
- `docs/methods_and_limitations.md`, with equations, assumptions, coverage, validation details, uncertainty methods, and interpretation limits.
- `docs/analytical_decisions.md` and the reconciliation log, including reasons for substantive changes from previous results.
- `docs/completion_report.md`, summarizing what changed, principal findings, unresolved issues, files removed/moved, and how to rerun.
- A concise data-request list only for genuinely missing inputs, stating exactly which claim/analysis each missing field would enable. Avoid a generic wish list.
- A reference list tied to the actual citations in the report. Verify external standards and clinical/time assumptions against original sources; do not retain unresolved citation tokens such as `[R5–R6]` or invent citations to support assumptions.
- An updated root README that lets the author find the data, four notebooks, report, and final assets quickly.

The report should be analytically complete for the available data. An unsupported causal identification or unavailable normative input is a documented result/boundary, not a reason to leave all later sections unfinished.

## 14. Execution order and reproducibility

Work through the following sequence, implementing rather than stopping after a plan:

1. **Inspect and map:** read source materials, inventory the repository, preserve unique work, identify conflicts, and record the current state.
2. **Resolve definitions:** establish sources, scopes, calendars, geography, professions, and common schemas. Identify critical missing inputs early.
3. **Build shared data:** implement canonical ingestion and panel construction; run source and join checks.
4. **Reconcile 4.1–4.2.2:** rerun existing analyses through the shared definitions, preserve the author's editorial logic, and record changes.
5. **Rebuild 4.2.3:** fit/validate M0–M5, estimate supply associations, standardize with the full M5, decide which age weights are usable, and export denominators with metadata.
6. **Complete 4.2.4:** compare meanings and results using the same verified workforce data.
7. **Build 4.3:** inequality, decomposition, convergence, priority changes, and source-checked province examples.
8. **Build 4.4:** actual entries/exits, stock reconciliation, matched growth, and workload/context associations. Update any 4.3 scenario using a now-verified flow assumption through an explicit dependency, not copied values.
9. **Write and integrate:** render section reports and the connected Chapter 4, with current numeric claims and asset locations.
10. **Validate and clean:** rerun from a clean execution state, inspect figures/document, remove verified obsolete outputs, and finalize the migration manifest and handoff.

Provide a documented build command using the repository's existing environment, or a simple command such as `python -m chapter4.build --all` if appropriate. Support rebuilding shared data and individual sections without manually copying cells or editing paths. Store assumptions and seeds centrally.

Do not require notebook execution in an undocumented order. If a section needs a shared model-denominator artifact, either generate it through the build dependency or raise an actionable message naming the required target. Do not silently load an older output if the current build fails.

Preserve final outputs in the notebooks for review, while ensuring that **Restart Kernel → Run All** works against the documented current inputs. A cached result can be reused only when its input/configuration/code identity is verified.

## 15. Required quality gates

Use meaningful checks tied to the actual risks below; avoid a large test suite that merely repeats implementation details.

| Area | Acceptance condition |
|---|---|
| Sources | Original data are unchanged; every active dataset has provenance and a role; cold/archive data do not enter builds accidentally. |
| Shared definitions | All four sections use the same verified workforce, population, service, and geography definitions or explicitly named alternatives. |
| Joins | Keys are unique at the declared grain; join expansion and dropped rows are audited. |
| Aggregation | National/sector/component totals reconcile within justified tolerances; duplicate counting is absent. |
| Time | CAGR uses elapsed intervals; lags skip no missing year; fiscal/calendar mismatches and incomplete years are flagged. |
| Workforce scope | Professional/technical nurses and MOPH/OPS/hospital scopes remain distinguishable. |
| Case mix | CMI is ratio-of-sums; calculated-case identities use matched records; no RW/AdjRW substitution without documentation. |
| Workload arithmetic | Full-precision sources, declared time assumptions, and no duplicated clinical-time allocation produce every displayed hour/day value. |
| M0–M5 | The required cumulative models use common comparison samples/folds; M4 adds beds and M5 adds physicians plus nurses. |
| Validation | No province leakage; every R² and incremental-error figure has a stated formula; temporal results disclose information timing. |
| Standardization | Full M5 predictions use a fixed reference profile; normalization remains fixed; positivity/support/uncertainty checks are reported. |
| Age weighting | Stable-rate estimation is distinguished from predictive age effects; zero/boundary weights are not silently repaired. |
| Inequality | Weighting is explicit; Theil components sum to the total; within-region differences are not mislabeled within-province inequality. |
| Priorities | All compared rankings use compatible samples; uncertain model-denominator ranks and tie rules are disclosed. |
| Scenarios | Totals, shares, and constraints reconcile; aggregate growth is distinct from distributional convergence. |
| Flows | Actual entries and exits are used; source totals are checked; the residual in `ΔW = I − O + residual` is visible. |
| Flow interpretation | Events are not mislabeled unique recruits/attrition probabilities; CAGR and event windows match. |
| Inference | Model fit/convergence and interval construction are checked; associations are not presented as identified causal effects. |
| Report | All numbers, signs, model names, scope descriptions, captions, and cross-references agree with the current executed results. |
| Reproducibility | A clean documented build generates all available-data deliverables without hidden notebook state or stale-output fallback. |
| Cleanup | Every deletion/move is justified and logged; no unique raw data, author prose, or unrelated work is lost. |

A failed gate must produce an explicit status, a reason, and the scope of affected conclusions. Do not force a result to pass by suppressing an inconvenient dataset, changing its unit, clipping a prediction, or adjusting a criterion after seeing the outcome.

## 16. Decisions the completed work must make explicit

Do not leave these questions scattered across code cells. Answer them in the report and in the completion summary:

1. How did each profession grow, and which sectors contributed the additional people?
2. How does the appearance of progress change when the workforce is compared with population, observed services, or standardized/need-related denominators?
3. Does age composition improve out-of-sample prediction for each service outcome?
4. Are estimated age-specific weights stable enough to be used as denominators? If only a scenario or exploratory use is justified, say so directly.
5. What additional predictive information comes from beds, and what comes from physicians plus nurses after accounting for beds?
6. What does the full M5-standardized denominator contain, what is fixed, what varies, and what can it legitimately be called?
7. Do the data identify supplier-induced demand, or only supply–service associations?
8. Did provincial inequality improve for every profession, and how much lies between regions versus between provinces within regions?
9. Which provinces remain priorities under several definitions, and which change classification when the denominator changes?
10. Are low-density provinces catching up, and how do distributional progress and aggregate workforce growth differ?
11. How much of recorded stock change reconciles with observed entries and exits, and where does the accounting fail?
12. How large and how uncertain are the workload–entry/exit associations, on comparable samples and periods?
13. Which quantities are ready to inform a later planning model, which remain assumptions, and which additional evidence would change the policy conclusions?

## 17. Final response to the author

When implementation is complete, respond concisely in Thai with:

- What was consolidated and what materially changed from the earlier analysis.
- The location of the four canonical notebooks and the integrated report.
- The most important revised findings, including any conclusions that no longer hold.
- Any genuinely blocked calculation and the precise missing input.
- The rerun command and the location of the file-migration/cleanup record.

Do not ask the author to approve routine work already authorized by this assignment. Do not report success until the outputs have been executed and checked. If an input is unavailable, be specific about what could and could not be completed, and deliver the useful completed work.

---

**Start instruction:** Read this entire task, the latest report, the two notebooks, and the older prompts. Inspect the actual repository and sources. Then carry out the consolidation, analyses, report writing, verification, and cleanup through completion, using the repository as the single authoritative analytical pipeline.
