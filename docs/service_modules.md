# Data-ready service modules: older-person care, kidney failure and five cancers

Date: 14 October 2026. Status: **draft structures**, built ahead of data (next-phase plan §4, §8.3). Expert review is pending.

The model structures exist now. A user brings the data a module needs, the module validates the data and calibrates the parameters it can estimate, and the user reviews and runs it. A new dataset or assumption re-runs the same function, so results stay comparable and traceable. **No module produces an estimate until real data are supplied.** Synthetic demonstration datasets show the file layout, and every run that uses them is labelled as synthetic.

## Where it lives

| Part | Location | Owner |
|---|---|---|
| Contract, schemas, validation, parameter resolution | `src/services/contract.py` | research tree |
| Older-person care (wraps the activity/FTE ledger) | `src/services/older_care.py`, `ledger.py` | research tree |
| Kidney failure on treatment | `src/services/esrd.py` | research tree |
| Cancer: breast, lung, colorectal, cervix, liver | `src/services/cancer.py` | research tree |
| Residence- vs provider-based workload (referral flows) | `src/services/referral.py` | research tree |
| Comparability contract and staged comparisons | `src/services/compare.py` | research tree |
| Synthetic demonstration data | `src/services/synthetic.py` | research tree |
| JSON entry points (native and browser) | `src/services/lab_modules.py` (`dispatch_json`) | research tree |
| Population denominator for the Lab (8 age groups, plus women by age group `F_*`) | `make services-population` → `outputs/services/service_population.json` → authoring `data/workforce_lab/` | research tree, synced |
| Lab view (`?mode=lab&labview=modules`) | authoring `story/js/lab/modules.js`, `story/css/lab-modules.css` | authoring |
| Tests | `tests/test_service_modules.py` (19), `tests/test_lab_compare.py` (3), authoring `tests/test_lab_modules_browser.py` (Chromium, including native/browser agreement) | both |

`make sync-lab-source` copies `src/services/*.py` and the population artifact into the authoring workspace. The Lab release packages them as hash-verified engine files.

## Three kinds of parameter

| Kind | Meaning | When data arrive |
|---|---|---|
| estimated | Can be computed from a dataset (incidence, transitions, prevalence, stage, survival, task times) | Calibrated automatically; the source column shows which dataset was used |
| assumption | Expert or literature values (session frequency, minutes per activity, working time) | Unchanged unless the user edits them; placeholders are labelled |
| policy | Decision-maker choices (coverage target, modality mix, early-detection shift, HPV-type incidence multiplier) | **Never changed by calibration** (tested) |

Precedence is user override > calibrated value > default.

## Modules

### Older-person home and community care

- **Required dataset:** dependency assessments (`older_care_state`): assessed and in-state counts by age group 60–69, 70–79 and 80+, optionally by province.
- **Optional datasets:**
  - an activity–time study (`older_time_study`), which replaces task and travel minutes;
  - available FTE (`workforce_fte`), which enables deliverable-versus-unmet care.
  - a caregiver time-use sample (`older_caregiver_time`), which calibrates informal care hours per week.
- **Engine:** the activity/FTE ledger, with all its accounting rules (section "The activity → time → FTE ledger" below).
- **Informal (unpaid) care** is reported in its own table: dependent older persons, caregiver hours per year and full-time-caregiver equivalents (2,080 hours, a convention). It covers every dependent person, covered by the package or not. It is **never added to or netted against health-workforce FTE** (tested): unpaid care is not unlimited replacement capacity.

### Kidney failure on treatment (ESRD)

- **Structure:** an annual cohort over HD, PD, transplant, conservative care and death.
- **Required dataset:** incident patients by age group (`esrd_incidence`), complete across all 8 groups.
- **Optional datasets:**
  - transitions, giving the annual matrix and first modality;
  - prevalent patients by province and modality, giving the starting stock;
  - dialysis capacity, giving the chair gap;
  - referral flows (`esrd_referral`: from_prov, to_prov, share), giving the provider-based workload.
- **Without prevalence data:** the starting stock is the stationary stock implied by incidence and transitions. This is flagged.
- **Outputs:** patients by modality, HD sessions, nephrologist and dialysis-nurse FTE, and HD chairs required.
- **Check:** patient balance, Δstock = incident − deaths, is tested to below 1e-8.

### Cancer pathways (five sites)

- **Required dataset:** registry incidence by site and age group (`cancer_incidence`). Diagnosed prevalence is not accepted as a substitute.
- **Optional datasets:** stage at diagnosis (unknown stage is redistributed and reported), first-course treatment by stage, 1–5-year survival, and linac capacity.
- **Optional datasets (continued):** screening results (`cancer_screening`: screened, positive, followed up by site), which calibrate test positivity and diagnostic follow-up completion; referral flows (`cancer_referral`), optionally by service (surgery, chemotherapy, radiotherapy, palliative, follow-up).
- **Policy levers:** an early-detection shift of stages III–IV to stages I–II (the case total is preserved, which is tested), an incidence multiplier, and the screening programme (target age groups, round coverage, interval).
- **Outputs:** cases by stage, patients by modality, follow-up survivors, operations, chemotherapy cycles, radiotherapy fractions, FTE for seven cadres, linacs and chemotherapy chair-hours.

#### Screening, a separate pathway

Breast, cervix and colorectal screening has its own workload: screened = target population × round coverage ÷ interval; positives = screened × positivity; diagnostic follow-ups (colposcopy, colonoscopy, diagnostic imaging) = positives × completion; hours by six screening cadres; FTE reported separately from treatment.

- Breast and cervix targets use **women** by age group from the population export. With an older population file the module falls back to a stated female-share assumption and warns.
- The programme defaults are illustrative. Breast screening is off (coverage 0) unless a user sets it.
- **Screening never changes cases or stage by itself** (tested: treatment tables are identical with and without screening). A burden effect needs the separate early-detection-shift policy, and the run warns when screening is on without it.
- Target groups are the 8 BOD age groups, so programme ages are approximate (for example 30–60 is read as 30–44 and 45–59).

## Residence-based need and provider-based workload

Modules count patients **where they live**. ESRD and cancer runs also produce a province table **by the province that delivers the care**:

- **Reallocation rule:** an uploaded referral file moves additive workload (sessions, procedures, staff hours, FTE, linac and chair requirements) from the residence province to the providing province, with provider = Σ residence × share.
- **Shares:**
  - shares of one origin province and service must not exceed one; the excess is rejected as an error;
  - any remainder, and any province absent from the file, stays in the residence province, so the default provider is the residence;
  - service-specific rows replace `all` rows for that origin.
- **Totals and gaps:** national totals are preserved (checked in every run; tested). Capacity gaps (chairs, linacs) are recomputed where the work is delivered.
- **In the Lab:** a toggle switches the province table between "by residence (need)" and "by providing province (workload)". It states whether referral data were used.

## Comparing runs: the comparability contract and staged comparisons (plan §8.4)

`compare.comparability(run_a, run_b)` checks the model structure, module version, time horizon and population denominator; any difference blocks the comparison. It then discloses columns or provinces present in only one run, flags different evidence labels, and attributes every difference to **data** (a dataset hash changed), **calibration** (an estimated parameter), **assumption** or **policy**.

`compare.staged` runs four stages:

1. base data;
2. new data with the calibration **frozen** at the base values;
3. new data recalibrated, plus assumption edits;
4. policy edits.

It reports, for each national indicator, the effect of new data, of refitting or method changes, and of policy. The three effects sum to the total change (tested). The order of the stages is a convention.

In the Lab: "use current datasets as the comparison base", then upload new files and press "compare with base".

The allocation Lab has the matching contract in `src/chapter5/lab_compare.py`, attached to every pair from `compare_runs`:

- **not comparable:** different versions, domain or geography;
- **common reference required:** the population denominator, target definition or evaluation weights differ;
- **directly comparable:** only policy, assumption or method parameters differ.

The existing version guard of `compare_runs` is unchanged.

## The activity → time → FTE ledger

Engine `src/services/ledger.py`; illustrative package `config/services/older_person_home_care.toml`; tests `tests/test_services_ledger.py` (the worked example below is a test). Every package value is an illustrative placeholder and is reported as a warning.

```text
population by age group ──► eligible = Σ_a N_a × prevalence_a        (care state, e.g. dependency)
                          ──► recipients = eligible × target coverage
                          ──► activity[k,s] = recipients × per_recipient[k] × setting share[k,s]
                          ──► hours[r] = Σ_k activity[k] × (task min[k,r] + travel min[k,r]) / 60
                                         + recipients × support hours[r]          (counted once)
                          ──► required FTE[r] = hours[r] / (contract hours × (1 − leave − other non-clinical))
                          ──► deliverable activity under available FTE  →  unmet activity
                          ──► hospital ledger: activity avoided by substitution and hospital time freed
```

| Rule | How it is enforced |
|---|---|
| Alternative settings or providers sum to one | `validate` raises otherwise |
| A multidisciplinary contact consumes time from several cadres | `task_minutes` may name several cadres; cadre shares are never forced to sum to one |
| Travel and coordination are counted once | an allowance counted in the numerator must appear in that cadre's `nonclinical_excludes`, or `validate` raises "double counting" |
| No workload is added on top of hospital totals that already contain it | substituting activities declare `replaces_hospital`; the hospital ledger records the avoided visits and the time freed |
| Required, deliverable and unmet care stay separate | deliverable ≤ required is tested; the scarcest cadre rations activities proportionally (declared convention) |

**Worked example**

| Step | Calculation | Result |
|---|---|---|
| Population | 60–69 = 10,000; 70–79 = 5,000; 80+ = 2,000 | — |
| Eligible | 10,000 × 0.02 + 5,000 × 0.06 + 2,000 × 0.20 | 900 |
| Recipients | 900 × 0.80 | 720 |
| Available hours per FTE | 1,920 × (1 − 0.10 − 0.10) | 1,536 h |
| Required FTE | nurse; physiotherapist; physician; care assistant | 6.91; 2.34; 0.23; 30.47 |
| Hospital ledger | 2,880 home sessions × 0.5 | −1,440 hospital rehabilitation visits |

**Before real use:**
1. practitioner review of the package;
2. replace the placeholders (dependency prevalence by age; task, travel and working times; current coverage from the รพ.สต. series up to 2022 and care-manager records);
3. reconcile the community and hospital ledgers with observed activity;
4. add outcomes only with a defensible model.

## Validation rules

- **Complete files only:** a dataset with a missing age group or province, an unknown code, a negative value or a duplicate key is rejected, with the reason shown. Missing values are never filled with zeros or defaults.
- **Required data:** a run is refused until its required dataset is present.
- **No incidence defaults:** absolute counts always come from data. This prevents placeholder rates from looking like Thai estimates.

## Privacy and the public Lab

The owner approved local processing on 14 Oct 2026. A chosen file is read in the page and passed as text to the Python worker, where pandas parses it. It is never executed, posted or stored. The browser test serves the site with a handler that records any POST request, and asserts that none occurs. Closing the page discards the data.

## How "automatic re-running" works

A run is a pure function of four inputs:

- the module version;
- the SHA-256 of each dataset;
- the overrides;
- the population denominator.

All four are recorded in the result's `provenance`. Changing any dataset or assumption invalidates the earlier validation: the Run button stays disabled until the data are validated again. Re-running then reproduces the full chain. The research-workspace prototype (`src/workspace/replace.py`) applies the same idea to the study's own inputs.

## Before public release

1. Clinical review of the ESRD and cancer structures, including states, pathways and activity content, plus practitioner review of the older-person package.
2. Replace placeholder assumptions with literature or local values where they exist, and keep their provenance.
3. Promote a release only after owner review. The current local draft is `20261014T111958Z-1dd387d08ca4` on branch `phase0-october-research-sync`.
