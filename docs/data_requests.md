# Data requests (only inputs that would change a stated conclusion)

| # | Input | Holder | Would enable |
|---|---|---|---|
| 1 | OPS staff stock by province × cadre × fiscal year (same HROPS universe as the event files), ideally at 30 Sep | กองบริหารทรัพยากรบุคคล สป.สธ. | A true stock–flow identity in 4.4.2 instead of a diagnostic against the broader MOPH stock |
| 2 | Linked person-level HROPS records (anonymised ID, dates, employment type, event, origin/destination unit) | same | Unique persons vs events; separating employment-status conversion (e.g. FY2020 nurses) from real exits; tenure-specific retention; transfer routes between provinces |
| 3 | MOPH hospital staff by facility with stable coverage (RH/GH/CH only) | กองยุทธศาสตร์และแผนงาน | Matched staff–service ratios in 4.2.2 without the broader MOPH-wide denominator |
| 4 | Service use by patient age (OP visits, admissions/AdjRW by age group) at province level | HDC / สปสช. | Directly estimated age-specific utilisation weights (4.2.3 C6), replacing assumed age scenarios in 4.3 |
| 5 | Patient residence vs hospital province (referral / cross-province flows) | สปสช. e-claim / HDC | Separating local responsibility from referral workload; interpretation of Pathum Thani / Narathiwat and of supply–service associations |
| 6 | Grouper (Thai DRG) version by fiscal year in the case-mix returns | กองบริหารการสาธารณสุข | Separating coding change from severity in the FY2023 CMI step |
| 7 | A policy-driven change in supply or payment unrelated to local need (allocation rules with thresholds; fee changes) | สป.สธ. / สปสช. | Any causal test of supplier-induced demand (4.2.3) or of workload effects on attrition (4.4.4) |
| 8 | Survey-based prevalence (e.g. NHES), care-package standards, activity time standards by cadre, FTE conversion | สวรส. / วิชาชีพ | Normative need and required-FTE calculations (T423_NEED_READINESS) |

## Next-phase modules (added 14 Oct 2026; see [data readiness](data_readiness_inventory.md))

| # | Input | Holder | Would enable |
|---|---|---|---|
| 9 | Workforce origin–destination moves between facilities/provinces (anonymised, with dates and cadre) | กองบริหารทรัพยากรบุคคล สป.สธ. | Measuring backwash into new centres and donor-area losses (anchoring module) instead of scenario values |
| 10 | Facility opening/expansion dates, funded posts and specialty services by facility | กองยุทธศาสตร์และแผนงาน | Event timelines for an anchoring evaluation; centre definitions for scenarios |
| 11 | Patient referral flows (residence → treating facility) by service line | สปสช. e-claim / HDC | Provider- vs residence-based workload; catchments for centre scenarios |
| 12 | Travel time between communities and facilities (road network) | GIS / กรมทางหลวง / open data | Access outcomes; replaces great-circle distance, which is not patient travel time |
| 13 | Dependency/functional status (ADL, frailty) by age and province; LTC care-manager and caregiver records | กรมอนามัย / สปสช. (LTC) / สำนักงานสถิติแห่งชาติ (older-person survey) | Replaces the placeholder care-state prevalence and coverage of the older-person package |
| 14 | Activity–time study for community and home care tasks by cadre, including travel and coordination | วิชาชีพ / สวรส. / participating facilities | Replaces placeholder task times and working-time deductions in the activity/FTE ledger |
| 15 | Treated kidney failure by residence and age: incident/prevalent HD, PD, transplant, conservative care, deaths; dialysis units, chairs, hours and staff | สมาคมโรคไตฯ (TRT registry) / สปสช. | An ESRD cohort and activity model (plan Phase 4); CKD stage 5 and DALYs cannot substitute |
| 16 | Cancer registry incidence by site, age, stage and residence; treatment pathway activity; radiotherapy/oncology equipment and staff | สถาบันมะเร็งแห่งชาติ / population-based registries | A single-pathway cancer module; the diagnosed-prevalence files cannot substitute |
