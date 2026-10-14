# Chapter 5 — data requests (only inputs that change a stated conclusion)

Each row names the claim it would change. Until supplied, the plans remain
`exploratory_policy_scenario`; unrelated completed work is not held back.

| # | Input | Holder | Turns what into what |
|---|---|---|---|
| 1 | OPS physician stock by province, 30 Sep 2025 (same HROPS universe as the event files) | กองบริหารทรัพยากรบุคคล สป.สธ. | Replaces the provisional MOPH-wide baseline; allows a calibrated (not exploratory) OPS plan and a true stock–flow identity. The M5 scope bridge then uses U = MOPH − OPS on its own path (`scope.unmanaged_moph_component`). |
| 2 | Physician age (or year of first appointment) by province | same | Age-specific retirement instead of a flat event rate; timing of retirement waves. |
| 3 | Linked person-level HROPS records (anonymised ID, dates, event, employment type, origin/destination unit) | same | Unique-person departures instead of the event-to-person assumption; tenure-specific resignation (post-compulsory-service exits); real inter-provincial transfer routes and eligibility. |
| 4 | Annual graduates, licensing, compulsory-service (ใช้ทุน) placements and acceptance by province, 2015–2025; current enrolment by year of study | แพทยสภา / กสพท. / สป.สธ. | Calibrates `national_graduates` and `student_intake` modes; replaces the illustrative 2,000 accepted starts with an evidence-based pool and uncertainty. |
| 5 | Funded posts (กรอบอัตรากำลัง) and vacant posts by province/hospital; onboarding/training capacity | สป.สธ. | Replaces the illustrative 10% arrival cap with measured absorption capacity; determines which binding constraints are real. |
| 6 | Official provincial population projection by age and sex (NESDC/IPSR), or DOPA births and deaths by province | สศช. / สถาบันวิจัยประชากรฯ / กรมการปกครอง | Replaces the Hamilton–Perry fallback; separates mortality from migration. |
| 7 | Essential service rosters / minimum staffing of referral hospitals by province | สป.สธ. | Replaces the illustrative 95% origin protection with known service floors. |
| 8 | Activity time standards and available working time for physicians (WISN) | วิชาชีพ / สวรส. | A workload-derived staffing requirement instead of illustrative 10/90-minute allocation weights. |
| 9 | Service use by patient age and residence (OP/IP by age; e-claim residence vs hospital) | HDC / สปสช. | Age-specific need weights within M5 support; separating referral workload from local responsibility. |
| 10 | Salary, recruitment and transfer costs | สป.สธ. / กรมบัญชีกลาง | Budget feasibility (not claimed without these). |
| 11 | Workforce origin–destination moves and centre opening dates (see Chapter 4 request 9–10) | สป.สธ. | Anchor-policy scenarios with measured transfer shares instead of zero/adverse/favourable scenario values. |
| 12 | Care-package standards and activity–time data for community care (Chapter 4 requests 13–14) | วิชาชีพ / สวรส. | Feeding package FTE requirements into a multi-cadre allocation, instead of reporting them alongside the physician plans. |
