# Data readiness for the next service modules

Date: 14 October 2026. This is backlog item 3 of the [next-phase plan](next_phase_development_plan_2026-10-14.md).

`scripts/data_readiness_inventory.py` measures the facts below directly from the files: columns, years, units, strata and coverage breaks. Its outputs are `outputs/shared/data_readiness_inventory.csv` and `outputs/shared/data_readiness_breaks.csv`. The readiness class and the candidate module are judgements recorded in that script.

## Summary by module

| Module | Usable now | Present but unvalidated | Missing (blocks the module) |
|---|---|---|---|
| Ageing / community care | Age structure (DOPA), age-specific BOD burden | รพ.สต. outpatient persons/visits (PC tier); community palliative coverage | Dependency/ADL/frailty by age; home-care, LTC and caregiver records; activity–time standards |
| ESRD / kidney failure | Diagnosed CKD stages 3–5 (type-area series) | CKD by hospital denominator; specialist headcount (no nephrology category) | Treated kidney failure by modality, incidence, transplant and deaths; dialysis capacity and staff |
| Cancer pathway | — | Diagnosed prevalence counts for breast, cervix and lung | Registry incidence by site/age/stage/residence; treatment activity; oncology equipment and staff |
| Task/FTE layer | Headcount by cadre (HRR) | Facility headcount by 19 cadres (GIS Health) | FTE, working time, task–time standards |
| Spatial / anchoring | Province geometry, great-circle distances | Facility-level staff and specialty returns | Workforce origin–destination moves, patient referral flows, facility opening dates |

## Findings that change how the files can be used

1. **The PC tier is not a stable series.**
   - Outpatient visits jump 88% in 2016 and fall back 42% in 2017. Persons do not move with them, so this is a reporting or definition artefact.
   - Reporting provinces fall from 76 to 70, 64 and 60 in 2023–2025, after health-promoting hospitals were transferred to provincial administrative organisations.
   - A community-care baseline built on this series must stop at 2022 or model the transfer explicitly.
2. **The cancer files have no age strata despite their names.** `s_ca_*_pop_age.csv` hold one prevalence count and its population per province-year.
   - Cervical-cancer diagnosed prevalence rises 119% in 2024, a further definition or reporting break.
   - None of the files identifies incidence, stage or treatment.
3. **CKD stage 5 is not kidney failure on treatment.** Neither CKD file records dialysis modality, transplant, incident cases or deaths. An ESRD module cannot be calibrated from them or from DALYs.
4. **The facility returns break in 2016.** Reporting facilities grow by about a third in 2016 in both `spc_aggregated.csv` and `hrh_aggregated.csv`. The specialty list has no nephrology, medical or radiation oncology, or geriatrics, so it cannot staff the ESRD or cancer modules.
5. **Community palliative care is a coverage percentage.** Its denominators are small target counts. It carries no episodes, visits or staff time.

## What this means for the order of work

- **Ageing / community care:** the first pilot can still proceed as a transparent calculator, using the demographic and burden inputs that are usable, with every care-state prevalence, package frequency and task time labelled as an assumption until the missing data arrive. The [activity/FTE ledger](activity_fte_ledger.md) is built that way.
- **ESRD:** stays conditional (plan Phase 4) until treated-kidney-failure data by modality are obtained.
- **Cancer:** stays conditional until registry incidence and treatment data are obtained.

The missing items are added to the data requests in [data_requests.md](data_requests.md) and [chapter5_data_requests.md](chapter5_data_requests.md). Each is tied to the module decision it unblocks.
