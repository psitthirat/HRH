# Chapter 4 consolidation — completion report (2026-09-26)

## What was built
* One pipeline: `src/chapter4/` (ingest → canonical tables → panels → metrics/models → section registries → report), driven by `config/analysis.toml` and `config/source_registry.toml`; `make chapter4` rebuilds everything from raw files (verified on a clean `data/processed/`).
* Four executed Thai notebooks in `notebooks/` (4.1 counts and services; 4.2 denominators, workload, M0–M5, standardization, age weights, 4.2.4 matrix; 4.3 inequality, convergence, scenarios, priorities; 4.4 entries/exits, reconciliation, PPML).
* 117 tables, 22 figures (PNG/SVG/PDF + plotted data) and 3,463 registered numeric claims; 482 claims and 35 assets are used in `reports/chapter4_complete_th.{md,docx}`.
* The author's LASTEST report is kept read-only in `reports/source/`; 4.1–4.2.2 prose preserved and corrected; 4.2.3, 4.2.4, 4.3, 4.4 and a chapter conclusion written.

## Answers to the required questions
1. **Growth by profession and sector** — physicians +71.6% (4.60%/yr), nurses incl. technical nurses +47.1% (3.27%/yr; professional only +54.7%), pharmacists +53.1%, dentists +16.6% (2013–2025). MOPH contributed the largest share of net growth (physicians 42.8%, nurses 41.2%, pharmacists 63.6%) while growing slowest; other public bodies grew as fast as the private sector.
2. **Denominators** — vs population: large gains; vs OP visits/inpatient days: staff grew faster than counted work; vs AdjRW: staff per unit of weighted output *fell* (MOPH physicians −20.1%, FY2018–2025), partly a FY2023 grouping step; vs M5 expected utilisation (2023–2025): close to population.
3. **Does age improve prediction?** Not established for any outcome (M0→M1 intervals cross zero).
4. **Are age weights usable?** No — all three fail the pre-declared gate (working-age weight at zero bound, order changes across universes, wide intervals). 4.3 uses declared scenarios.
5. **Beds vs workforce** — beds reduce out-of-sample error for all three outcomes (OP 26%, IP 39%, AdjRW 22%); adding physicians + nurses helps only AdjRW (24%, 4.6–40.9), driven by physicians; nurses add nothing once beds are in.
6. **M5 standardized denominator** — full M5 prediction with each province-year's age shares and recorded prevalence; GPP, beds, physicians, nurses and year fixed at the 76-province 2023 reference; normalized to 2023 equivalent population. Name: model-standardized expected utilisation.
7. **Supplier-induced demand** — only associations are identified; no causal design is supported by the data.
8. **Provincial inequality** — Gini (population-weighted) fell for all four professions in both scopes; MOPH pharmacists almost flat, with the between-region share rising 20→38%. Physicians remain most unequal. Within-province inequality is not identifiable.
9. **Priority provinces** — Kamphaeng Phet, Bueng Kan, Amnat Charoen and Loei are in the lowest quartile under all six (and nine) denominators; 41 provinces appear under at least one; Pathum Thani and Narathiwat switch most with the denominator. Bueng Kan ranks last under every denominator.
10. **Catching up** — beta convergence 2013–2025 for all professions; for all-sector physicians it stalled after 2018 and dispersion widened; highest-density quartile took 44% of new physicians. Growth alone never changes relative inequality.
11. **Stock–flow** — pharmacists reconcile nationally within 2%; nurses differ by 2,119 (−15.6%), partly because the stock includes technical nurses while HROPS events cover professional nurses only; physicians' recorded net inflow exceeds stock change by 2,722 (46%); provincial residuals are large for every profession.
12. **Workload–flow associations** — positive in the pre-specified offset model for physician entries (OP/physician) and nurse entries and resignations (IP days/nurse), but not robust to a free stock term (refill pattern). Not usable as causal responses.
13. **Model readiness** — entry, exit, resignation intensities usable for baseline scenarios with scope caveats; association coefficients not causal; normative inputs absent (`T423_NEED_READINESS`, `T44_FUTURE_MODEL_PARAMETERS`, `docs/data_requests.md`).

## Conclusions that changed (see `docs/reconciliation_log.csv`)
* Physician time illustration: the "below 240 days" reading holds only if all working time is direct care; under the draft's own 60% assumption OP+IP use 149% of the direct-care budget (flagged for author review).
* Age structure no longer "helps predict OP" once uncertainty is shown; the six-denominator list shrinks from five provinces to four (Chaiyaphum drops).
* OP/physician and AdjRW/physician use matched 76-province scope (5,939 and 484.0; not 5,641 and ~460).
* B.E. 2589 is 21 years after 2568, not 50.

## Files moved or removed
See `docs/file_migration_manifest.csv`: author notebooks, the earlier `chapter4_fresh` pipeline and old outputs → `archive/legacy_analysis/`; two unused raw files → `data/cold_data/`; one Excel lock file deleted. Full pre-change snapshot with hashes: `archive/recovery_20260925/`. Nothing was committed to git.

## Open items
* DOCX checked structurally (headings, embedded figures, captions); page-level rendering in Word not verified in this session.
* Author editorial review requested for: 4.2.2 time-budget conclusion (R06), the FY2020 nurse conversion hypothesis (4.4.1), and physician stock–flow residual interpretation (4.4.2).
