# Activity → time → FTE ledger, with an older-person care example

Date: 14 October 2026. Implements backlog item 4 of the [next-phase plan](next_phase_development_plan_2026-10-14.md) (§3.1–3.2, §4.1, §4.4).

| Part | Location |
|---|---|
| Engine | `src/services/ledger.py` |
| Package | `config/services/older_person_home_care.toml` |
| Tests | `tests/test_services_ledger.py` (the example below is a test) |

**Every parameter in the package is an illustrative placeholder.** The numbers were chosen so a reviewer can check them by hand, and the ledger reports each placeholder as a warning. The ledger is not yet applied to provinces. It should be applied only after practitioners have reviewed the package and measured or elicited inputs have replaced the placeholders.

## 1. The calculation chain

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

The interface is `validate → project_activity → estimate_resources → deliverable → evaluate`. `evaluate` returns these ledgers:

| Ledger | Grain |
|---|---|
| `activity` | unit × activity × setting |
| `hours` | unit × activity × cadre × component (task / travel / support) |
| `fte` | unit × cadre |
| `deliverable` | required vs deliverable vs unmet activity |
| `hospital_required`, `hospital_deliverable` | hospital activity avoided and hospital time freed |

## 2. Rules the engine enforces

| Rule (plan §3.2) | How it is enforced |
|---|---|
| Alternative settings or providers must sum to one | `validate` raises if an activity's setting shares do not sum to 1 |
| A multidisciplinary contact consumes time from several cadres | `task_minutes` may name several cadres; cadre shares are never forced to sum to one |
| Travel and coordination are counted once | An allowance counted in the numerator (travel, support) must appear in that cadre's `nonclinical_excludes`, or `validate` raises "double counting" |
| No workload is added on top of hospital totals that already contain it | Substituting activities state `replaces_hospital`; the hospital ledger records the avoided visits and the hospital time freed |
| Required, deliverable and unmet care stay separate | `deliverable` never overwrites the required ledger; deliverable ≤ required is tested |
| Unvalidated evidence is visible | Every parameter has a provenance class; placeholders become warnings |

**Deliverable care convention.** An activity is delivered in the proportion available ÷ required FTE of its scarcest cadre. Activities that share that cadre are rationed proportionally. This is a declared convention, not a prediction of how teams prioritise. Replacing it, for example with a priority order agreed with practitioners, changes only `deliverable`.

## 3. Worked example (one province, placeholders)

Population aged 60–69 = 10,000; 70–79 = 5,000; 80+ = 2,000.

| Step | Calculation | Result |
|---|---|---|
| Eligible (dependency) | 10,000×0.02 + 5,000×0.06 + 2,000×0.20 | 200 + 300 + 400 = **900** |
| Recipients | 900 × 0.80 coverage | **720** |
| Assessment | 720 × 1 at primary care; nurse 45 min | 720 contacts; 540 nurse h |
| Nurse home visit | 720 × 12; nurse 30 min + 30 min travel | 8,640 visits; 4,320 + 4,320 nurse h |
| Home rehabilitation | 720 × 4; physiotherapist 45 + 30 min travel | 2,880 sessions; 3,600 physio h |
| Physician review | 720 × 2, half at primary care, half remote; 15 min | 1,440 reviews; 360 physician h |
| Care-assistant visit | 720 × 52; 60 + 15 min travel | 37,440 visits; 46,800 h |
| Coordination | 720 × 2 h (nurse), counted once | 1,440 nurse h |
| Available hours per FTE | 1,920 × (1 − 0.10 leave − 0.10 other) | 1,536 h |
| Required FTE | nurse 10,620 ÷ 1,536; physiotherapist 3,600 ÷ 1,536; physician 360 ÷ 1,536; care assistant 46,800 ÷ 1,536 | **6.91; 2.34; 0.23; 30.47** |
| Hospital ledger | 2,880 home sessions × 0.5 avoided outpatient visits; × 20 physio-min | −1,440 hospital rehabilitation visits; 480 physio h freed |
| Deliverable with 5 nurse FTE | 5 ÷ 6.91 = 0.723 of assessments and nurse visits; other activities in full | 2,392 nurse visits unmet |

## 4. What must happen before real use

1. **Practitioner review** of eligibility, package content, frequencies, team composition and the substitution rate.
2. **Replace the placeholders:**
   - dependency prevalence by age, from an older-person survey or the LTC register;
   - task and travel times, from a small activity-time study;
   - working time by cadre, including part-time work and dual practice;
   - the current coverage baseline, from the รพ.สต. series up to 2022 (see [data readiness](data_readiness_inventory.md)) and from care-manager records.
3. **Reconcile with observed activity.** Compare the hospital ledger with outpatient rehabilitation volumes. Compare the community activity with recorded home visits before any province-level output is presented.
4. **Add outcomes only with a defensible model.** The existing amenable-YLL health-gain score stops at age 74. It cannot represent the benefits of this package (plan §6.2).

The ledger produces requirements alongside the Chapter 5 allocations; it does not feed them yet (plan §4.4).
