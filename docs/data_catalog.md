# Chapter 4 — data catalog

Raw sources are registered in `config/source_registry.toml`; hashes, sizes and roles are written to
`outputs/shared/source_inventory.csv` by `python -m chapter4.build --shared`.

## Raw sources (active)
| id | path | content | years | basis |
|---|---|---|---|---|
| S01_HRR | data/hrh_moph.xlsx | Health Resource Report: workforce by cadre × employer; services (table 4 all reporting; tables 5–7 MOPH RH/GH/CH; table 8 PC) | 2013–2025 | report year |
| S02_POP_AGE | data/pop/age/pop_{year}.xlsx | DOPA register, single age × sex, village rows; non-age-attributed groups as columns | 2013–2025 | December |
| S03_POP_GRAND | data/pop/grand/pop_{year}.xlsx | DOPA published totals | 2013–2025 | December |
| S04_NHSO | data/pop/nhso/pop.csv | NHSO entitlement register | 2010–2025 | December |
| S05_CASEMIX | data/cmi/CMI_{FY}.xlsx | Hospital case-mix returns | FY2018–2025 | fiscal |
| S06/S07_HDC | data/epi/*.csv (listed files only) | Diagnosed prevalence (6 used) and dental/pharmacy activity | 2022–2025 | HDC year |
| S15_BOD_AGE | data/epi/BOD_2022_Province_Disease_Age.csv | The same BOD 2022 estimates by 8 age groups: DALY/YLL/YLD/death counts, rates and mid-year population; canonical table `bod_province_age` (re-standardization reproduces S14 to 0.03%) | 2022 | calendar |
| S14_BOD | data/epi/BOD_2022_Provincial_ASR.xlsx | BOD Thailand (IHPP) provincial burden: age-standardized DALY/YLL/YLD/death rates per 100,000, 174 Level-3 causes, both sexes; canonical table `bod_province` | 2022 | calendar |
| S08_GPP | data/gpp.xlsx | GPP per capita (r/p flags kept) | 1995–2024 | calendar |
| S09_ENTRY | data/enter_moph.xlsx | HROPS entries (category × employment type) | FY2017–2026 | fiscal |
| S10_EXIT | data/loss_moph.xlsx | HROPS exits (reason) | FY2017–2026 | fiscal |
| S11 (audit) | data/enter_moph_condensed.xlsx | Same entry extract, condensed layout (supplied 25 Sep 2026); matches S09 in all 14,014 cells | FY2017–2026 | fiscal |
| S12/S13 (diagnostic) | data/hrh_aggregated.csv, data/hosp.csv | Facility staff returns + registry; tested and rejected as OPS stock | 2015–2024 | report year |

## Raw files not used by Chapter 4
* `data/epi/s_ca_*`, `s_emphysema_*`, `s_palliative_com`, `s_dental_4`, `s_ckd_stage_hosp` — kept in place because `scrp_epi.ipynb`, `scripts/pivot_epi.py` and `scripts/export_for_external_analysis.py` read them. `s_dental_4` (gold-card population only) is superseded by `s_dental_2` (all rights).
* `data/spc_aggregated.csv` — specialist project (`spc.ipynb`, `hrh.ipynb`).
* `data/cold_data/hrh_excel.xlsx` (moved) — two-year GIS-health provincial summary, superseded by S01.
* `data/cold_data/rtsd_pat.geojson` (moved, git-ignored, 705 MB) — geometry referenced by no code.

## Canonical tables (`data/processed/`, rebuilt by `--shared`)
| table | key | notes |
|---|---|---|
| province_key | prov_code | DOPA code, Thai/English names, health region (HROPS, consistent across all sheets), Bangkok flag |
| workforce_province | year, prov_code, cadre, sector | headcount; missing ≠ 0; published_total kept for reconciliation |
| services_province | year, prov_code, tier, metric | tiers all_reporting / rh / gh / ch / pc |
| casemix_hospital / casemix_province | fiscal_year, hospital_code / prov_code | cmi = ratio of sums |
| population_single_age | year, prov_code, sex, age | age-attributed civil register |
| population_registers | year, prov_code, register | civil_age, civil_grand, nhso_rights |
| population_register_parts | year | decomposition of the published total (identity gap 0) |
| nhso_province_scheme_age / nhso_audit | year, month, prov_code, right_code, age_band, sex | register audit |
| hdc_indicators | year, prov_code, indicator | prevalence (%) checked = 100·num/den; activity counts |
| gpp_province | year, prov_code | status final/revised/preliminary |
| flow_events | fiscal_year, row, cadre, direction, category, employment_type | component cells only, blank flag |
| flow_published | same | subtotal, cadre-total, grand-total columns and footers, summary sheet |
| province_panel_76 | year, prov_code | analytical panel with eligibility flags (`elig_m5_common`, …) |

## Shared audits (`outputs/shared/`)
source_inventory, province_region_crosswalk, coverage_by_year, missingness, duplicate_keys, join_audit,
workforce_reconciliation, service_nesting, service_nesting_province_anomalies, casemix_identity,
analysis_sample_flow, m5_exclusions, national_76_bridge.

## Section outputs
`outputs/chapter4_{1,2,3,4}/`: `tables/*.csv` (UTF-8 BOM), `figures/*.{png,svg,pdf}`, `figure_data/*_data.csv`,
`chapter4_X_tables.xlsx`, `claims.csv` (numeric claim registry), `assets.csv`, `run_manifest.json`.
