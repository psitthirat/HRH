# Next-phase development plan: integrated workforce modelling and the Workforce Lab

Date: 14 October 2026  
Status: proposed development roadmap; no model, website, or deployment changes made by this document  
Scope: Chapters 4 and 5, presentation, and the existing Workforce Lab

## 1. Recommended direction and answers to the four questions

Extend the existing research platform through shared, versioned service modules. The immediate priority is to reconcile the October analytical updates with the September Lab release, make validation results visible, and establish a common service-to-workforce accounting framework. Then pilot older-person/community care and one well-defined disease pathway before expanding the platform.

| Question | Assessment | Recommended next step |
|---|---|---|
| Can ageing, out-of-hospital care, ESRD, and cancer have specific models? | Yes. Population/needs-to-activity models, workload-to-FTE models, state-transition models, and discrete-event simulation answer different parts of these questions. The repository already contains useful demographic, burden, service, and allocation components, but does not yet contain validated end-to-end care pathways for these modules. | Build a shared task/time/FTE layer; pilot older-person community care, followed by ESRD subject to data readiness. Start cancer with one site or service pathway. |
| Have we done backtesting, and is more needed? | Yes, at component level. Population hindcasting, service-model temporal holdouts, service benchmark comparisons, and retrospective stock-flow checks exist. These do not validate the complete 2026–2040 policy simulation or identify policy effects. | Publish a validation inventory, strengthen time-cutoff evaluation, and add integrated hindcasts where historical inputs permit. |
| Should the Lab have two tiers? | Yes. The current browser Lab is a strong foundation for public exploration using study data. Research assumption changes, replacement datasets, recalibration, accounts, and shared private workspaces need additional contracts and services. | Separate **Study Lab** from **Research Workspace**, using the same scientific engine and explicit versioned inputs. |
| Can Myrdal's backwash/spread framework and rural anchoring inform analysis and policy controls? | Yes, as a conceptual framework and a set of explicit, testable mechanisms. A new rural centre can improve access while also drawing staff away from surrounding facilities. Current associations cannot identify those effects. | Add a Chapter 4 spatial mechanism audit and a Chapter 5 anchor-policy scenario module with donor-area outcomes, lags, capacity, and budget constraints. |

The main scientific distinction is between **observed services**, **expected or normative care requirements**, **deliverable service capacity**, and **health outcomes**. Keep these separate in both computation and presentation. More recorded services can reflect improved access, referrals, coding, or induced use; fewer recorded services do not establish lower need.

## 2. Evidence used and the current implementation

### 2.1 Meeting evidence and the status of this proposal

The source is the draft meeting summary, *“Policy options for the future: integrated modelling for workforce planning, workshop 2,”* dated **28 September 2026**, supplied as [สรุปการประชุม.docx](</Users/rama-hpsr/Downloads/สรุปการประชุม.docx>). Its recommendations are evidence for planning, not instructions to execute changes or approved parameter estimates.

Sections 6.1–6.7 and 7 support expected-service modelling; services beyond hospitals; task-based teams; realistic working time; technology; active workforce across sectors; and continuing data updates. Figures such as 80% service availability, 50% pharmacist time in OPD, and 20–25% teaching/research time are meeting examples requiring measurement or structured elicitation before adoption. They should not become universal defaults.

The explicit ESRD/cancer modules, two-tier product design, and Myrdal/anchoring extension are developed here in response to the user's additional brainstorming. They should not be attributed wholesale to meeting consensus. Quantitative statements in the meeting are a September presentation snapshot; subsequent October results need their own provenance.

### 2.2 What already exists

| Area | Verified current state | Consequence for development |
|---|---|---|
| Chapter 4 | Unified stock/service, workload/model, inequality, workforce-flow, and burden analyses. Current manifests include sections 4.1–4.5. Core service modelling covers 76 provinces, excluding Bangkok, and uses a shorter common sample than the full historical descriptive series. | Extend the canonical pipeline and reports. Do not infer that every model uses the full 2013–2025 history. |
| Age-specific burden | The October source has 107,184 rows: 77 provinces × 174 cause categories × 8 age groups. Expected DALY/YLD uses fixed province-age-specific 2022 rates with changing populations. | Ageing already affects expected burden. This is a demographic projection under fixed rates, not observed annual disease trends or a service/FTE requirement. Cause categories need a non-overlapping selection before aggregation. |
| Existing community data | `services_province.csv` contains a separate `pc` tier for health-promoting hospitals: OP persons/visits over 2013–2025. M5's hospital outcomes use `rh`, `gh`, and `ch`. | Audit the existing primary-care series before requesting everything anew. PC activity is not a complete home-care/LTC dataset, and coverage changes must be checked. |
| Disease candidates | Existing extracts include CKD stage data, selected cancer files, and community palliative-care coverage. These are not all validated model inputs. Current CKD prevalence is combined across stages 3–5; cancer extracts with `_age` in their names do not currently provide age strata. | Build a readiness inventory. CKD stage 5 does not identify dialysis modality, incident ESRD, or treatment eligibility. A palliative coverage percentage does not identify staff time or all care episodes. |
| Chapter 5 | Provincial physician allocation for 2026–2040, stock-flow dynamics, constraints/transfers, P/S/N comparisons, feedback sensitivity, and uncertainty. The current root code also includes age-specific BOD-based B plans and illustrative health-gain evaluation. | Reuse the allocator where its units and scope fit. Current plans use MOPH stock as a provisional OPS-managed stock and remain exploratory. Other cadres require their own supply and task parameters. |
| Health-gain extension | `health_gain.py` evaluates completed plans using assumed physician-to-amenable-burden elasticities. It does not feed health gains back into allocation targets. Its current amenable-cause age limits exclude the 80+ group. | Label results illustrative. Add appropriate older-person outcomes rather than presenting the existing YLL score as a complete measure of community-care benefit. |
| Existing Workforce Lab | The authoring workspace has a real browser solver: canonical Python through Pyodide/SciPy, scenario controls, saved local runs, comparisons, uncertainty, and exports. It already supports policy and selected scientific sensitivity controls. | Build on this implementation. A new slider-only prototype would duplicate existing work. |

Local evidence: [Chapter 4 decisions](analytical_decisions.md), [Chapter 4 panels](../src/chapter4/panels.py), [source registry](../config/source_registry.toml), [data catalogue](data_catalog.md), [Chapter 5 decisions](chapter5_decisions.md), [health-gain implementation](../src/chapter5/health_gain.py), and [Lab integration map](../workspaces/HRH-authoring/docs/workforce_lab_integration_map.md).

### 2.3 First dependency: reconcile the analytical and website source trees

There are two independently advanced implementations:

- The root research tree contains the **14 October** age-specific BOD and health-gain updates. The later [rebuild log](../outputs/chapter5/logs/rebuild_2026-10-14b.log) supersedes the open `rebuild_2026-10-14.log`; the [run manifest](../outputs/chapter5/validation/chapter5_run_manifest.json) records the workbook stage at 13:30 Bangkok time and uncommitted pipeline changes.
- `workspaces/HRH-authoring/` contains the newer Lab adapter, dependency injection, browser packaging, and policy interface. Those changes are not all present in the root tree. Conversely, its Chapter 5 implementation lacks the root's B family and health-gain module.
- The public site was checked on 14 October: its selected release is `20260927T223014Z-e20170082d16`. The release advertises P/S/N-STD/N-FB/SQ-C, no raw-data upload, and no required accounts. Its freshness status is `unknown`; it must not be presented as incorporating the October research updates. See the [live release index](https://psitthirat.github.io/HRH-model/data/releases.json) and [live Lab manifest](https://psitthirat.github.io/HRH-model/data/releases/20260927T223014Z-e20170082d16/lab/lab.json).

Do not copy either `src/` tree wholesale over the other. Reconcile the scientific definitions while preserving the Lab's lightweight model-design module and injectable inputs. The current Lab freezing script combines research exports with authoring inputs and frozen fits; simply refreshing CSVs would not establish a coherent new fitted model.

Create an explicit analysis-to-release handoff: source/config/data hashes, model/transform versions, coefficient provenance, validation results, and reviewed public artifacts. Use the established authoring workspace for presentation development and a defined canonical scientific source for both native and browser execution. Record the decision and eliminate ambiguous duplicate ownership.

The October Chapter 5 stage manifests share input/config fingerprints but record different code hashes across stages. Phase 0 should review those dependencies and freeze a coherent snapshot; a successful build alone does not establish one immutable version. The differing hashes do not, by themselves, demonstrate incorrect results.

Update stale methodological prose during that handoff. For example, older text saying the burden source cannot represent ageing is no longer accurate for the new age-specific source, although fixed 2022 rates remain a limitation.

## 3. Shared modelling framework

### 3.1 Add services outside hospitals as a distinct accounting dimension

Here, **out-of-hospital** includes home visits, community/primary care, intermediate care, LTC, rehabilitation, palliative care, and relevant preventive services. It is not a synonym for hospital outpatient visits.

Use the following dimensions across modules: residence/catchment, provider location, year, age or care state, service pathway, activity, setting, sector, and cadre. Keep hospital OPD, inpatient activity, home/community services, and remote contacts distinguishable. Maintain both residence-based need and provider-based workload so referral centres can serve populations beyond their administrative boundaries.

The proposed calculation chain is:

```text
Population and care states
  → eligible people/episodes
  → care package and coverage scenario
  → activities by setting and provider
  → time by task and cadre
  → required FTE and equipment
  → feasible delivery under workforce/capacity/budget constraints
  → unmet care, access, workload, and explicitly modelled outcomes
```

For a simple annual module:

```text
required activity = eligible people × target coverage × activities per recipient
required hours[r] = Σ(activity volume[k] × task hours[k,r]) + separately counted support hours[r]
required FTE[r]   = required hours[r] / available annual hours per FTE[r]
```

These are proposed accounting identities, not fitted treatment effects. For mutually exclusive alternative settings or providers, allocation shares must sum to one. A multidisciplinary contact can legitimately consume time from several cadres; represent its component tasks rather than forcing all cadre shares to sum to one.

Use WHO's workload/activity-time approach as a methodological basis, adapted to each local service. WISN supplies a workload-to-staffing framework; it does not by itself recover unmet need or forecast changes in care pathways. [WHO WISN user manual, 2nd edition](https://www.who.int/publications/i/item/9789240070066).

### 3.2 Rules that protect interpretability

1. Separate **current delivered activity**, **target care coverage**, and **feasible delivered activity**. Compare them to expose unmet care; do not calibrate need solely to historically constrained utilization.
2. Count leave, nonclinical time, teaching, supervision, travel, and coordination once. If a task is explicitly in the numerator, do not also deduct its time from the denominator. Convert headcount to available FTE transparently, including part-time and dual practice.
3. Reconcile pathway activity with the existing hospital totals. Replacing a hospital visit with a home visit changes both ledgers. Do not add a full disease workload on top of totals already containing that disease, or add a population floor to complete disease packages without an overlap rule.
4. Handle multimorbidity through shared contacts or joint care states. Summing independent disease pathways can overcount reviews, counselling, and care coordination.
5. DALYs, YLDs, prevalence, and recorded visits have different units. There is no automatic conversion from DALYs to visits or FTE. Retain BOD allocation as a comparator; add a separate care-package bridge when estimating staffing requirements.
6. Model public/private delivery shares by service, place, and access conditions. Private capacity does not automatically satisfy publicly financed need; contracts, eligibility, affordability, and actual activity matter.
7. Task shifting needs cadre competency, supervision, training, quality, and capacity constraints. Technology effects should have adoption lags, implementation/support workload, and uncertainty rather than an automatic productivity dividend.
8. Keep normative requirements separate from politically or financially feasible targets. Preserve the existing fixed-total comparison when isolating geography; show workforce expansion and cost effects separately.

## 4. Candidate service modules

The following are design recommendations, not claims that a ready-made foreign model is calibrated for Thailand. Published models support methodological choices; local data, pathway review, and implementation are still required.

### 4.1 Older-person and community-care module — first service pilot

Start with population × dependency/care state × service package × team time. Use age, functional dependency/ADL, frailty where measured, and living/support arrangements rather than age alone. Include assessment/prevention, rehabilitation/intermediate care, home care, LTC, and palliative care as distinguishable packages. WHO ICOPE offers an appropriate reference for person-centred primary/community pathways; it is guidance for defining care, not a workforce forecasting equation. [WHO ICOPE handbook, 2nd edition](https://www.who.int/publications/i/item/9789240103726).

**Minimum inputs:** age-specific population; measured or explicitly assumed care-state prevalence; package eligibility and frequency; time by cadre; setting/sector; travel and coordination time; available working hours; existing service coverage. Audit the existing PC and community palliative extracts first. Seek dependency/care-manager/LTC records and a small activity-time study to fill the missing dimensions.

**Controls:** coverage, home/community share, rehabilitation capacity, task allocation, care-manager availability, visit frequency, travel time, telehealth substitution, and formal/informal care balance. Show caregiver workload separately; unpaid care is not unlimited replacement capacity.

**Outputs:** required and available FTE by cadre/setting, unmet care episodes, continuity/coverage, travel burden, and caregiver hours. Add functional/QoL outcomes only with a defensible outcome model. The current amenable-YLL score excludes 80+ and cannot represent all relevant benefits.

**First implementation:** a transparent annual calculator for a small set of packages, with hand-worked examples reviewed by practitioners. Add transitions between dependency states only when longitudinal or externally justified transition data are available.

### 4.2 ESRD/kidney-failure module — first disease pilot if data are ready

Use a cohort state-transition model for annual demand and workforce planning. Distinguish incident kidney failure, haemodialysis, peritoneal dialysis/home support, functioning transplant/follow-up, conservative kidney management, and death, with a reviewed definition of the modelled cohort. Dialysis modalities are alternatives at a point in time; visits, training, monitoring, and complications generate additional activities.

A published renal-replacement model used discrete-event simulation with incidence/acceptance, survival, and modality transitions. This establishes a relevant model family, not transferable Thai parameters. Start with a simpler cohort model; add discrete-event simulation if chair scheduling, queues, or referral bottlenecks become the decision question. [Roderick et al., 2004](https://pubmed.ncbi.nlm.nih.gov/14767028/).

**Minimum inputs:** incident/prevalent treated patients by residence and age; modality and transitions; sessions/support contacts; mortality; public/private provider activity; nephrology/nursing/technical staff; machine/chair capacity and operating hours. Audit existing CKD-stage extracts, then assess renal-registry and payer aggregates. Do not infer these quantities from combined CKD 3–5 prevalence or DALYs.

**Controls:** scenario modality mix, home-support coverage, contracted private delivery, treatment-centre/satellite capacity, travel/referral patterns, and workforce retention. These are planning assumptions, not treatment recommendations for individuals.

**Outputs:** patients and activity by modality; staffing/equipment gaps; coverage and travel; costs when available; queues only if a queue model is implemented. Verify patient stock-flow conservation and resource capacity. Initiation policy and unmet treatment need need separate treatment so low recorded uptake is not read as low need.

### 4.3 Cancer module — one pathway before an all-cancer model

Start with a selected cancer site or a defined shared service such as radiotherapy. Use incidence × stage × treatment pathway, including follow-up/survivorship and palliative care. Prevalence alone cannot identify new treatment workload, cycles, procedures, or duration.

For annual staffing, use pathway activities and staff time. For treatment delays and bottlenecks, use discrete-event simulation linking staff and equipment. A published radiotherapy model explicitly represented the referral-to-treatment process and resource bottlenecks. Its results should not be imported as local staffing effects. [Babashov et al., 2017](https://pubmed.ncbi.nlm.nih.gov/28222957/).

**Minimum inputs:** registry incidence by site/age/residence; stage and treatment distributions; referral flows; surgery/systemic therapy/radiotherapy activity; time by profession; equipment availability; follow-up duration; service standards and observed waits. Existing breast/cervical/lung extracts are candidates for audit, not substitutes for these variables.

**Controls:** selected service expansion, centre/satellite location, diagnostic throughput, shared care, follow-up location, team composition, and equipment capacity. Model screening as a separate pathway with diagnostic and treatment consequences rather than a free reduction in burden.

**Outputs:** activity, specialist/support FTE, bottlenecks, access and waiting times where simulated. Avoid aggregating all cancers with one treatment time or mapping all work to general physicians.

### 4.4 Common integration contract

Each module should expose a versioned input schema, required/optional datasets, parameters with provenance, an activity/FTE ledger, capacity constraints, outcomes, uncertainty definitions, and validation evidence. A proposed internal interface is `validate → prepare → project_activity → estimate_resources → evaluate`; this is a design contract, not an existing API.

The first release should calculate needs/FTE alongside current allocations. A later multi-cadre allocator can consume those requirements once supply, minimum teams, training lags, and staffing interchangeability are specified. Changing physician coefficients into nurse or pharmacist coefficients by relabelling is not valid.

## 5. Validation: existing backtests and the next standard

### 5.1 What the existing checks establish

| Check | Existing evidence | Interpretation and limitation |
|---|---|---|
| Chapter 4 spatial validation | Repeated province-grouped cross-validation; all years for a province stay together. | Tests prediction across held-out provinces, not forecast performance through time. |
| Chapter 4 temporal validation | 2024 holdout trained on 2022–2023; 2025 holdout trained on 2022–2024. Conditional observed-covariate and forward carried-covariate versions are distinguished. | Persistence outperforms the service models in these short holdouts. Do not describe M5 as the best forecaster solely from explanatory fit. |
| Population hindcast | 2019 → 2025, with province total MAPE about 1.11% for national-control Hamilton–Perry versus 2.23% for no change. | Useful evidence from one six-year origin, not validation of every age group or a 15-year forecast. National-total error and provincial error are different metrics. |
| Service benchmarks | Rolling 1–3-year horizon comparisons; OP/IP have four cutoffs and AdjRW two. Persistence is selected; AdjRW's lower-error trend is not selected under the minimum-cutoff rule. | The implementation uses realized target-year population when evaluating projected rates, so this is a conditional service-rate check, not a complete joint population/service forecast. |
| Stock-flow reconstruction | FY2021–2025 replay using actual recruitment and hazards fitted across FY2021–2025. Provincial MAPE reaches about 11.27% in 2025. | A retrospective reconciliation diagnostic, not an out-of-sample forecast. Stock/event scope differences also matter. |
| Optimizer/software checks | Feasibility, balance, boundary, invariance, adapter/browser and export checks exist. | Establish implementation properties for tested cases; do not validate policy benefits or future clinical outcomes. |
| Burden and health gains | Fixed 2022 burden rates; assumed health-gain elasticity grid. | No longitudinal burden validation or identified physician-to-health effect. |

Evidence: [temporal service results](../outputs/chapter4_2/tables/T423_TEMPORAL_VALIDATION.csv), [population hindcast](../outputs/chapter5/validation/T5_POP_BACKTEST.csv), [service benchmarks](../outputs/chapter5/validation/T5_SERVICE_BACKTEST.csv), [stock-flow replay](../outputs/chapter5/validation/T5_STOCK_FLOW_BACKTEST.csv), [Chapter 4 model code](../src/chapter4/models.py), and [Chapter 5 methods](chapter5_methods.md).

### 5.2 Required additions

**A. Cutoff-safe component forecasts.** For every origin, rebuild transformations, imputations, coefficients, hazards, benchmark selection, and tuning using only information available by that cutoff. Distinguish a latest-revised-data hindcast from a real-time historical-vintage evaluation. In particular, a 2022 BOD cross-section must not be treated as information available for pre-2022 forecasts; earlier burden reconstructions are retrospective standardizations.

**B. Integrated hindcasts.** Where inputs permit, start from observed baseline stocks and independently projected population, services, and supply. Score 1-, 3-, and 5-year horizons where history supports them. If actual future recruitment or population is supplied, label the run conditional and present it separately. Do not promise a historical 15-year test from shorter or incompatible series.

**C. Honest baselines and metrics.** Compare persistence, simple trend, population-only, and the current canonical model on the same observations. Report MAE/RMSE, bias, population-weighted and unweighted errors, rank stability, and prediction-interval coverage where intervals are probabilistic. Use MAPE only where denominators are meaningful. Stratify by province/region, rural access, referral role, sector coverage, and shock/coding periods. Separate COVID-era disruptions and the FY2023 DRG step from general performance.

**D. Care-package validation.** Review eligibility, task content, time standards, and feasible team composition with practitioners. Reconcile predicted activity/FTE with independent service logs or time-use samples, including home/travel work. Observed underprovision is not a gold standard for normative need.

**E. Policy evaluation.** Historical replay can test prediction under observed policies. It cannot show what would have happened under an unimplemented allocation or rural centre. For these, report scenario sensitivity, constraint feasibility, distributional trade-offs, and regret across declared futures. Estimate causal effects only with a separate identification design.

**F. Structural and implementation checks.** Test no double counting, patient/workforce mass balance, zero-effect recovery of baseline, capacity bottlenecks, shared-task accounting, infeasible teams, and native/browser agreement. Use numeric tolerances and objective/constraint checks because MILP builds can select different equivalent integer schedules. Expose solver status and remaining optimality gap.

Predefine acceptance criteria before evaluating a candidate model. A forecast that fails to improve on a simple baseline should remain an explanatory/sensitivity option or use that baseline for forecasting. A module without sufficient holdouts should be labelled **scenario-only**. User-selected low/high ranges are scenario envelopes, not confidence intervals.

The current [M5 support table](../outputs/chapter5/validation/T5_M5_SUPPORT_BY_YEAR.csv) flags extrapolation for 71 of 76 provinces by 2040. Keep support diagnostics visible and evaluate alternatives before using M5 as the sole long-horizon response mechanism.

## 6. Chapter 4 and Chapter 5 analytical changes

### 6.1 Chapter 4: establish what can be learned from the available data

| Workstream | Deliverable | Interpretation to preserve |
|---|---|---|
| Coverage and active practice | Province × year × cadre × sector × setting coverage matrix; headcount/FTE definitions; PC series audit; missing-vs-zero flags. | MOPH, OPS, all-sector, and actual practice are different universes. Sector transfers are not automatically national workforce losses. |
| Need versus recorded services | Update burden/age decomposition; compare P/S/B/expected-service rankings; map disagreement and likely coverage/referral explanations. | Fixed-rate expected burden is neither observed utilization nor a causal model. |
| Working time and teams | Task inventory for the pilot packages; local time/FTE evidence; teaching, administration, travel, and supervision audit. | Meeting time percentages are hypotheses until validated. |
| Disease readiness | Explicit audit of existing CKD, cancer, palliative, specialist, and PC extracts; data dictionary and usable strata. | Filename labels do not establish age detail, unique patients, stable coverage, or clinical eligibility. |
| Spatial concentration | Centre/catchment maps, recruitment/retention and service-flow descriptions, access measures where network data exist. | Province averages conceal within-province rural shortages; adjacency does not establish patient or workforce flows. |
| Validation reporting | One consolidated table distinguishing explanatory fit, spatial CV, temporal forecasts, and retrospective diagnostics. | Null associations or short holdout performance do not establish absence of need or prove supply-induced demand. |

Add these as clearly identified extensions to the current chapter structure, including the existing burden section 4.5. Refresh claim registries and templates alongside tables; do not manually change prose without the corresponding analytical evidence.

One current result should shape the interpretation: the aggregate-burden model M2B performs worse than the age-only M1 in the paired held-out comparisons for OP visits, inpatient days, and AdjRW. This does not make burden unsuitable as an equity criterion; it shows why prediction of recorded hospital activity and normative resource allocation must be assessed separately. See the [paired burden-model comparisons](../outputs/chapter4_5/tables/T45_PAIRED_GAINS_BURDEN.csv).

### 6.2 Chapter 5: compare feasible ways of delivering care

Retain P, S, N-STD/N-FB, and the updated B family as distinct comparators. Add service-package/FTE requirements through the common ledger; preserve the fixed-total experiment for allocation comparisons and separate scenarios allowing total requirement/growth to vary.

Extend supply incrementally from physicians to relevant teams, with training pipelines, part-time/FTE availability, sector mobility, and actual absorption capacity. Compare packages combining recruitment, retention, task sharing, contracting, community delivery, and technology. A staffing solution must satisfy equipment, supervision, service floors, and budget constraints when those quantities are measured.

Report national, regional, provincial, and catchment consequences together. Include unmet need, access, continuity, workforce workload, donor-area losses, and cost feasibility alongside Gini and staffing targets. Keep health-gain assumptions in a separate, versioned evaluation layer. Broaden its outcome definitions for older-person care through a documented method change, not by silently removing the current age limits.

Uncertainty scope must match the actual implementation. Current root fixed-schedule analysis includes B, whereas adaptive replanning covers P/S/N only. New families need their own tested adaptive rules before being offered as equivalent options in the Lab.

## 7. Myrdal, backwash/spread effects, and rural anchoring

### 7.1 Use the framework to specify competing mechanisms

Myrdal's framework is a useful lens for cumulative spatial advantage and disadvantage. In this project, **backwash** means a centre's expansion draws scarce workforce, activity, or investment from surrounding areas; **spread** means benefits extend outward through training, shared services, outreach, referrals, and local capabilities. The workforce interpretation below is a proposed application, not an effect estimated by Myrdal or by the current HRH models. The original conceptual reference is Myrdal's *Economic Theory and Under-developed Regions* (1957); spatial empirical work illustrates why spillovers and the influence of multiple centres need to be measured. [Myrdal book record](https://books.google.co.uk/books?id=D_6OBPeIDDUC), [Ganning, Baylis and Lee, 2013](https://onlinelibrary.wiley.com/doi/10.1111/jors.12026).

| Mechanism | Observable evidence to seek | Proposed policy/scenario controls |
|---|---|---|
| Attraction and concentration | Staff origin/destination, vacancy changes, recruitment, turnover, specialist capacity. | Centre staffing, recruitment source, retention package, training places and return/rotation arrangements. |
| Backwash into a new rural hub | Loss of staff/activity in nearby community facilities; longer local access times despite hub growth. | Donor service floors, limits on internal transfers, funded replacement, protected primary-care staffing. |
| Spread through a network | Outreach/rotation activity, local skills, shared diagnostics, completed referral and return pathways. | Outreach time, supervision, teleconsult support, transport and referral agreements, community capacity. |
| Longer-term anchoring | Retained staff and trainees, supporting employment/services, sustained local capacity. | Investment timing, operating budget, housing/career support, training lag, local recruitment. |

A centre's opening should not automatically apply a positive rural workforce multiplier. WHO's rural workforce guidance supports context-specific bundles of development, recruitment, support, and retention measures; it does not establish a universal causal return to constructing a specialist centre. [WHO rural workforce guideline summary](https://www.who.int/publications/b/57953).

### 7.2 An implementable first anchor experiment

Define a centre at a specified facility/catchment, not just a province labelled rural. Compare four scenarios on the same evaluation population and declared resource envelope:

1. No new centre, with existing service expansion rules.
2. Centre investment and staffing without a dedicated outreach/retention package.
3. Centre plus community/satellite services, rotation, training, and retention support.
4. A distributed service package using an equivalent budget where costs are available; otherwise label this as an equal-workforce comparison with incomplete capital-cost comparability.

Separate capital commissioning, equipment, funded posts, actual recruits, retention, and service activation. Model delays, incomplete uptake, and recurrent costs. Distinguish new national entrants from internal transfers; internal movements must balance across origins and destinations, with boundary flows shown explicitly where Bangkok or other sectors lie outside the model universe.

Represent workforce movements and patient referrals as separate networks. Start with measured flows; where absent, use clearly labelled scenarios and sensitivity to catchments/travel impedance. Great-circle transfer distances in the existing allocator are not patient travel-time estimates. Constrain the whole team and equipment so an unstaffed facility does not count as operational capacity.

Report the centre, neighbouring areas, the poorest-access group, and the wider system: net FTE gain, donor losses, access/travel, unmet need, continuity, service throughput, and budget. A centre can attract staff and still worsen access in its hinterland.

### 7.3 From scenario analysis to empirical evaluation

For Chapter 4, assemble dated openings/expansions and policy exposure, pre-policy outcomes, comparable areas, workforce/patient flows, and concurrent investment. Consider event-study/difference-in-differences or synthetic-control designs only if timing, comparison groups, and pre-trends support them. Account for spillovers that contaminate nearby controls and for centres being deliberately located in changing or disadvantaged areas. If identification is weak, retain descriptive evidence and scenario ranges.

The existing M5 supply-service association and N-FB feedback coefficient do not identify attraction, retention, or spread effects. Keep those mechanisms as separately named parameters, with evidence status and zero-effect/adverse-effect scenarios. Monitoring after implementation should update the parameters without rewriting the original ex ante forecast.

## 8. Two-tier Lab: behaviour, interface, and computation

### 8.1 Product boundaries

| Feature | Tier 1 — Study Lab | Tier 2 — Research Workspace |
|---|---|---|
| Purpose | Explore the study and reviewed policy scenarios. | Investigate alternative evidence, assumptions, and model versions. |
| Access | Public, no account required. | Authenticated private workspace with membership/roles for saved data and collaboration. |
| Data | Immutable reviewed study release. | Versioned compatible replacement/extension datasets within the workspace. |
| Assumptions | Study defaults remain identifiable; curated policy controls and published sensitivity presets. | Explicit scientific assumption edits, typed data adapters, recalibration, and module configuration. |
| Computation | Existing browser engine for supported, bounded runs; published results stay distinguishable from fresh solves. | Same canonical engine via validated worker jobs for ingestion/refitting/heavy simulation; browser previews where equivalent. |
| Results | Reproducible baseline, policy comparisons, limitations, download. | Input/assumption diffs, data QA, calibration/validation reports, provenance, comparable-run evaluation. |
| Publication | Released study artifacts. | Private by default; deliberate review/promotion creates a new public release. |

Tier 1 should retain a clearly visible **Reproduce study baseline** action and **Explore policy** mode. Distinguish loading the exact published result from recalculating the baseline: native/browser solvers may choose different integer schedules within the declared tolerance, while preserving scientific definitions, feasibility, and provenance. Controls that change scientific assumptions must be labelled as study sensitivity analyses and visibly mark a departure from baseline. The existing advanced scientific controls can move to Tier 2 or to bounded published presets; they should not disappear without an explicit migration decision. Both tiers can run different service modules as those modules mature.

The current JSON import is scenario import, not dataset replacement. Current storage is browser-local; login, shared storage, upload validation, and refitting do not yet exist. Accounts alone would not add those capabilities. Evidence: [Lab capabilities](../workspaces/HRH-authoring/docs/workforce_lab_capability_matrix.md), [Lab adapter](../workspaces/HRH-authoring/src/chapter5/lab_adapter.py), and [browser persistence](../workspaces/HRH-authoring/story/js/lab/storage.js).

### 8.2 User flows and presentation changes

Keep one bilingual site with **Read findings → Open related Lab → Compare scenarios → Export**. Retain chapter context when entering and leaving the Lab.

**Study Lab:** choose a question/module → inspect baseline and evidence status → adjust relevant policy controls → run → compare against study baseline. Show results and trade-offs first; place advanced diagnostics in a methods drawer. Keep data year, release, population/sector coverage, and “baseline / sensitivity / user scenario” visible near the result.

**Research Workspace:** sign in → fork a study release → select data to replace → map/validate → inspect coverage and assumption changes → choose an applicable fixed-fit prediction or re-estimation workflow → review support/validation → run scenarios → compare/export → optionally submit a release for review. Missing mandatory inputs should identify exactly which module is unavailable; unrelated validated modules can still run.

Add module cards for **National/provincial allocation**, **Ageing and community care**, **Kidney failure**, **Cancer pathway**, and later **Rural anchor policy**. Each card should state its policy question, inputs, evidence status, and supported outcomes. Proposed modules should be labelled unavailable/experimental until implemented; avoid active controls with no corresponding calculation.

Revise the narrative to show population, observed service, burden, and care-package requirements side by side. Add a compact validation view explaining what was held out, against which baseline, and where performance is weak. For anchoring, show centre and surrounding-area outcomes together. Maps should switch explicitly between provider workload and resident access/need.

### 8.3 Replacement data must trigger an explicit analysis workflow

Treat a “plug-in” initially as a declarative dataset adapter, not uploaded executable code. Begin with a limited set of aggregate CSV/Parquet schemas, then add reviewed adapters for further sources.

Each dataset manifest should include dataset/schema version, source and permitted use, checksum, geography/codes, period and fiscal/calendar basis, units, age/cause/cadre/setting definitions, population and institutional coverage, missingness/suppression, and any parent dataset replaced. Validate keys, duplicate rows, non-negative quantities, ranges, share sums, and count/rate denominators. Reject incompatible mappings; never silently convert missing provinces to zero or combine incompatible scopes.

The dependency examples below describe affected components, not mandatory refitting for every new value. Compatible future exogenous inputs can use a fixed fit if that choice is explicit and support checks pass. Changes to training observations or model definitions require refitting and renewed backtests; outcome-only assumptions may require evaluation alone.

| Replacement | Dependent work that must be invalidated or rerun |
|---|---|
| Population/age structure | Demographic fit/projection, denominators, expected burden/activity, targets, and downstream plans/evaluations. |
| Workforce stocks or events | Scope reconciliation, hazards/supply calibration, relevant resource covariates and model fits, plans, and validation. |
| Service or morbidity data | Coverage checks, transforms, service benchmarks/M5 where relevant, responsibility indices, pathway calibration, and validation. |
| Care pathways/time standards | Activity/FTE conversion, capacity, relevant cost/evaluation outputs, and affected allocation plans. |
| Outcome-only assumptions | Outcome evaluation and its manifest; preserve plans if targets/constraints/objective truly do not depend on them. |

Do not silently change policy preferences when data change. Separate observed inputs, estimated quantities, literature assumptions, illustrative values, policy choices, and conventions. Show old/new values, source, affected outputs, and whether refitting is required. A changed coefficient should be traceable to a changed dataset or method, not merely a new file label.

Use immutable input snapshots and run IDs. Capture source-code content hashes as well as commit IDs, because the current working tree contains uncommitted scientific changes. Record configuration, seed, transforms, fitted parameters, input hashes, solver/runtime, diagnostics, and output schema. An unsuccessful update leaves prior runs available and visibly tied to their original release.

### 8.4 Comparison and infrastructure contracts

The existing `compare_runs` correctly rejects incompatible input/engine versions. Do not remove that guard to enable Tier 2. Add an explicit harmonization/reference contract: common geography, population, time horizon, outcome units, target definitions, and evaluation weights, with exclusions disclosed. Preserve both each run's own-context results and any common-reference re-evaluation.

Separate the effect of **new data**, **refitting/method changes**, and **policy changes** through staged comparisons. Run comparisons against a fixed reference where meaningful; otherwise label results non-comparable. Renaming a metric does not make different denominators comparable.

Add a small server-side research service for authentication, workspace authorization, dataset/object storage, metadata, validation, and queued model jobs. Enforce access at the service/storage layer; a static-site login screen is not protection for private data. The scientific library should remain independent of account/UI code. Cache keys must include data, configuration, and engine hashes; jobs need progress, cancellation, resource limits, and explicit failure states.

Start with aggregate data only. Do not route uploaded research datasets into the public static bundle. Add isolation checks, upload size/type validation, safe parsing, and access-controlled exports as part of this concrete upload feature. Reuse the existing public-artifact allowlist and review/promotion process for publication.

## 9. Delivery sequence and acceptance gates

Effort bands below indicate relative complexity, not delivery commitments. Named roles are proposed responsibilities, not assigned personnel. Work can proceed in parallel where dependencies permit.

| Phase / priority | Deliverable and likely owner | Dependency | Acceptance gate |
|---|---|---|---|
| **0 / immediate: reconcile the baseline** — small/medium | Analysis + Lab engineers reconcile root/authoring differences; inventory releases; refresh October methods/claims; generate one coherent scientific/public handoff. | Existing sources and outputs. | New BOD/B/health features preserve Lab functionality; native/browser fixtures agree within declared tolerance; release provenance is complete; September remains reproducible. |
| **1 / high: validation and contracts** — medium | Methods lead creates validation inventory, cutoff-safe test specifications, dataset schemas, parameter provenance, and dependency invalidation rules. UI adds visible version/evidence labels. | Phase 0 for final parity; design can start immediately. | Existing backtests are correctly labelled; simple baselines reported; an incompatible dataset is rejected; one compatible local replacement produces a traceable recalibrated sandbox run. |
| **2 / high: common task/FTE layer + ageing pilot** — medium/large | Service researchers and analysts audit PC/LTC/palliative data, define a small package set, implement activity/FTE ledger, validate practitioner examples. | Minimum care-state and activity-time evidence; Phase 1 schemas. | Baseline hospital/PC accounting reconciles; no duplicated tasks/time allowances; required versus deliverable care is distinct; unavailable evidence is clearly labelled. |
| **3 / high after contracts: Tier 2 MVP** — large | Application/data engineers add accounts, workspace isolation, versioned uploads, job orchestration, recalibration review, and exports. Start with one replacement schema. | Phase 1 workflow and canonical engine; can develop alongside Phase 2. | A user forks, replaces data, reviews QA/refit, runs, and reproduces a result; another workspace cannot access its data; public baseline remains intact. |
| **4 / conditional: first disease module** — medium/large | Disease expert + modeller implement ESRD cohort/activity model; choose a cancer pathway next if its data are more ready. | Usable modality/stage/activity/team data; shared FTE layer. | Patient balance, activity/resource constraints, validation against independent aggregates, and scope limitations pass review before public release. |
| **5 / research: anchoring/spatial module** — large | Spatial/policy researchers + modeller develop catchments, flows, centre timelines, scenario mechanisms, and evaluation design. | Facility/network evidence and service/team constraints; descriptive mapping can begin earlier. | Centre-only and network alternatives report donor losses and system gains; internal transfers balance; zero/adverse spillover cases run; unsupported causal claims are excluded. |
| **6 / recurring: monitored releases** | Research/platform team maintains input registry, validation dashboard, decision log, and reviewed releases. | Earlier gates for each module. | Each update identifies changed data/assumptions, out-of-sample performance where possible, scenario changes, and unresolved limitations. |

### First actionable backlog

1. Produce a root-versus-authoring change map and agree canonical ownership of scientific modules, including `models.py`/`model_design.py`, injectable panels, BOD transformations, and Lab packaging.
2. Create a single validation table from the existing Chapter 4/5 artifacts, including forecast origin, information set, comparator, horizon, metric, and limitation. Link it from the methods view.
3. Inventory existing PC, CKD, cancer, palliative, BOD, and specialist data with actual columns, year coverage, units, and known breaks. Distinguish available/usable, available/unvalidated, and missing.
4. Specify the activity/FTE ledger and one older-person care package with a worked example and an explicit hospital/community overlap rule.
5. Classify every current Lab control as policy, scientific sensitivity, data-driven estimate, or unsupported feature. Define its Tier 1/Tier 2 destination and migration behaviour.
6. Prototype one dataset replacement through the engine locally, including invalidation/refit and provenance, before building a general upload interface.
7. Draft the spatial mechanism diagram and data request for workforce/patient flows and centre opening dates. Keep initial parameters scenario-based unless identified evidence is available.

Extend the existing [Chapter 4 data requests](data_requests.md) and [Chapter 5 data requests](chapter5_data_requests.md) with the pilot-specific gaps. Candidate data holders include HDC/MOPH, NHSO, professional and disease registries, local care programmes, and participating facilities; access and suitability must be confirmed rather than assumed. Request only variables tied to a model decision or validation question.

## 10. Implementation map and definition of completion

Existing integration points to reuse:

| Layer | Current location |
|---|---|
| Source definitions, coverage and analytical defaults | `config/source_registry.toml`, `config/analysis.toml`, `src/chapter4/ingest.py`, `panels.py`, `models.py` |
| Projection, responsibilities, supply and allocation | `src/chapter5/demography.py`, `responsibilities.py`, `supply.py`, `allocation.py`, `pipeline.py` |
| Scenario evaluation and evidence | `src/chapter5/analysis.py`, `evaluation.py`, `health_gain.py`, `outputs/chapter5/validation/` |
| Report definitions and claims | `reports/templates/`, Chapter 4/5 claim registries, `docs/*methods*`, `docs/*decisions*` |
| Lab scientific adapter and lightweight design | `workspaces/HRH-authoring/src/chapter5/lab_adapter.py`, `src/chapter4/model_design.py` inside that workspace |
| Lab controls, outcomes and schemas | `workspaces/HRH-authoring/config/workforce_lab/` |
| Browser interface and computation transport | `workspaces/HRH-authoring/story/js/lab/`, including `runtime-worker.js` and `storage.js` |
| Release assembly and public handoff | `workspaces/HRH-authoring/scripts/webstory/`, including `lab.py`, `lab_inputs.py`, `lab_release.py` |

New service modules, schemas, validation orchestration, and authenticated services are proposed additions; their precise package paths should be chosen after Phase 0. Avoid introducing another independent scientific implementation in the frontend or backend.

The first meaningful milestone is reached when an October-consistent study release reproduces its reference analyses, clearly reports existing validation limits, and runs one reviewed community-care package with an auditable FTE ledger. The Tier 2 milestone additionally requires a complete, isolated dataset-replacement-to-recalibration workflow. A new disease or anchoring control is complete only when it changes a real, tested mechanism and produces interpretable outputs with documented evidence status.

This roadmap was prepared from the supplied meeting document, current local source/output inspection, local Lab architecture, the public release metadata, and the cited methodological sources. It does not constitute a fresh full analytical rebuild or a new test-suite pass; the requested work here is the development plan itself.
