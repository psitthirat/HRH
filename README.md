# เว็บไซต์นำเสนอผลการวิจัย

เว็บไซต์สไลด์ปัจจุบันอยู่ใน `story/` เปิดด้วย `make story-serve` ส่วนต้นฉบับและบทผู้บรรยายใช้ repository ส่วนตัว `HRH-authoring` และชุดที่เผยแพร่ใช้ repository `HRH-slides`

สำหรับการทำงานต่อในเครื่องนี้ ให้เปิด `workspaces/HRH-authoring/` เป็น workspace ใหม่ โฟลเดอร์ HRH เดิมยังเก็บงานเดิมและ remote เดิมไว้

- [วิธีเผยแพร่และทำงานต่อบนเครื่องอื่น](docs/web_story/publishing.md)
- [การจัดชุดต้นฉบับและผลวิเคราะห์สำหรับแก้เว็บ](docs/web_story/portability.md)
- [วิธีแก้ภาษา บทพูด และข้อมูลสไลด์](docs/web_story/update_runbook.md)

ใช้ `make story-public` เพื่อสร้างเฉพาะไฟล์สำหรับสาธารณะ ห้ามเผยแพร่ `story/` ต้นฉบับโดยตรง เพราะมีบทผู้บรรยาย การวิเคราะห์ใหม่ไม่จำเป็นสำหรับการแก้ภาษาและ layout

---

# Chapter 4 — Thailand's health workforce: progress, shortage, or mismeasurement? (unified pipeline)

**Rebuild everything** (≈ 4 minutes; the population workbooks are read once and cached):

```bash
make chapter4                      # = PYTHONPATH=src .venv/bin/python -m chapter4.build --all
make chapter4-shared               # canonical tables + audits only
PYTHONPATH=src .venv/bin/python -m chapter4.build --section 4.3   # one notebook (checks its dependencies)
make chapter4-report               # Thai report from the template + claim registry
make chapter4-test
```

| What | Where |
|---|---|
| Four analysis notebooks (Thai, executed) | `notebooks/chapter4_1_counts_and_services.ipynb`, `…4_2_denominators_workload_and_need.ipynb`, `…4_3_distribution_and_inequality.ipynb`, `…4_4_entries_exits_and_growth.ipynb` |
| Integrated Thai report | `reports/chapter4_complete_th.md`, `reports/chapter4_complete_th.docx` (prose: `reports/templates/chapter4_th.md`) |
| Author's reference report (read-only) | `reports/source/` |
| Configuration (single source) | `config/analysis.toml`, `config/source_registry.toml` |
| Shared code | `src/chapter4/` (config, ingest, panels, metrics, models, reporting, report, build) |
| Canonical tables / audits | `data/processed/`, `outputs/shared/` |
| Tables, figures, plotted data, claim registry | `outputs/chapter4_{1,2,3,4}/` |
| Documentation | `docs/completion_report.md`, `docs/methods_and_limitations.md`, `docs/analytical_decisions.md`, `docs/reconciliation_log.csv`, `docs/data_catalog.md`, `docs/data_requests.md`, `docs/file_migration_manifest.csv` |
| Superseded Chapter 4 work | `archive/legacy_analysis/` (never read by the build); pre-consolidation snapshot in `archive/recovery_20260925/` |

Raw data remain at their original `data/` paths because other projects in this repository use them; unused raw files are in `data/cold_data/`.

---

# Chapter 5 — a 15-year provincial physician allocation plan (2026–2040)

Extends the Chapter 4 pipeline (same processed tables, M5 refitted and checked against the Chapter 4 export).
Every plan is an `exploratory_policy_scenario`: the baseline is the MOPH-wide stock standing in for OPS, and the
2,000/yr pool, 10% cap and 2% transfer limit are illustrative.

```bash
make chapter5                              # inputs → plans → uncertainty → comparison/figures/workbook → Thai report (≈1 h)
make chapter5 SET="supply.annual_path=2500" NAME=pool2500          # what-if; writes outputs/chapter5_scenarios/pool2500/
make chapter5 SET="allocation.cap_mode=net_growth targets.reference_per_1000=0.5" NAME=netcap_ref05
make chapter5-test                         # stress and boundary tests (section 13.3 of the task)
make chapter5-notebooks                    # execute the three Thai notebooks after a build
```

| What | Where |
|---|---|
| 15-year annual plans (all provinces, years, plans; transfer routes; national balance) | `outputs/chapter5/plans/chapter5_annual_allocation_plans.xlsx` (+ CSV/parquet equivalents in the same folder) |
| Thai report | `reports/chapter5_complete_th.md`, `reports/chapter5_complete_th.docx` (prose: `reports/templates/chapter5_th.md`) |
| Notebooks | `notebooks/chapter5_1_inputs_and_projection.ipynb`, `…5_2_allocation_and_simulation.ipynb`, `…5_3_comparison_and_policy.ipynb` |
| Configuration | `config/chapter5.toml` (provenance of every value: observed / estimated / illustrative / policy / convention) |
| Code | `src/chapter5/` (config, inputs, demography, supply, responsibilities, allocation, simulation, pipeline, analysis, evaluation, figures, workbook, reporting, report, build) |
| Tables, figures, plot data, validation, claims | `outputs/chapter5/{tables,figures,plot_data,validation}/`, `outputs/chapter5/claims_*.csv` |
| Documentation | `docs/chapter5_methods.md`, `docs/chapter5_decisions.md`, `docs/chapter5_data_requests.md`, `docs/chapter5_completion_report.md` |

---


# Addressing Inequity in Medical Specialist Distribution in Thailand

This repository contains the code and supplementary materials for the research study:

**"Disparities in Medical Specialist Distribution in Thailand: An Analysis of National Health Workforce Database Between 2015 and 2024"**

## Overview

This study examines the distribution of medical specialists across Thailand over a ten-year period (2015–2024) using data from national health workforce records. It evaluates workforce policies, such as mandatory rural service and task-shifting, and their impacts on equity and healthcare access. The analysis provides critical insights for policymakers aiming to improve equitable access to specialist care.

## Key Features

- **Equity Analysis**: Calculation of Gini coefficients to measure disparities in specialist distribution.
- **Data Visualization**: Heatmaps and scatter plots to depict trends in equity and density.
- **Policy Impact Evaluation**: Analysis of targeted workforce interventions on specialist availability and distribution.

## Data Sources

1. **Specialist Distribution**: Ministry of Public Health (MOPH) open-access platform ([http://gishealth.moph.go.th](http://gishealth.moph.go.th)).
2. **Population Data**: National Population Registry, Bureau of Registration Administration, Ministry of Interior, Thailand.
3. **Healthcare Facilities**: Healthcare Facility Registry Dataset, Office of the Permanent Secretary, MOPH.

## Methods

- Equity measured using Gini coefficients at regional and provincial levels.
- Specialist-to-population ratios calculated across 13 health regions and 77 provinces.
- Data analyzed and visualized using Python and Tableau.

## Results Highlights

- **Increased Availability**: Total specialists grew significantly from 2015 to 2024, with general practitioners seeing a 210% increase.
- **Improved Equity**: Gini coefficients for general practitioners improved markedly, from 0.35 to 0.20 provincially.
- **Persistent Gaps**: Low-density specialties, such as pathology and rehabilitation medicine, remain inequitable despite progress.

## Repository Structure

- **`/data`**: Datasets used in the analysis and relevant dictionaries.
- **`/output`**: Cleaned dataset and analytical output
- **`/scripts`**: Python scripts for data processing, analysis, and visualization.
- **`/results`**: Outputs including charts, metrics, and statistical summaries.

## Getting Started

### Prerequisites

- **Python 3.x**: Required for analysis scripts.
- **Tableau**: For creating visualizations (optional).

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/psitthirat/HRH.git
   cd HRH
   ```

2. Install dependencies:

   ```bash
   pip install -r scripts/requirements.txt
   ```

### Usage

1. Place datasets in the `/data` folder.
2. Open the main analysis notebook in Jupyter Notebook:

   ```bash
   jupyter notebook main.ipynb
   ```

3. Run the cells in `/main.ipynb` to perform the analysis and generate results.
4. Review results in `/results` or use Tableau for further exploration.

## Ethical Considerations

This research uses publicly available, anonymized datasets. Ethical approval was not required for secondary data analysis.

## Citation

If referencing this work prior to formal publication, please use the following format:

```
Sitthirat, P., Suppawitaya, P., Yoadsanit, S., Osotthanakorn, P., Suriyawongpaisal, P., Srithamrongsawat, S., Kaewkamjornchai, P., & Tangcharoensathien, V. (2024). Disparities in Medical Specialist Distribution in Thailand: An Analysis of National Health Workforce Database Between 2014 and 2023. *Unpublished Manuscript*. Available at: https://github.com/psitthirat/HRH.
```

## License

This repository is licensed under the [MIT License](LICENSE).

---

## Chapter 4 — Situation of Thailand's Health Workforce

The Chapter 4 analysis lives in `hrh.ipynb` §5–13 and is delivered three ways: an English
Word report, a bilingual dashboard page, and the notebook itself.

**§5–10** are the descriptive situation analysis: stock, growth, skill mix, geographic
maldistribution, the specialist landscape, and service workload. **§11** is the extended
analysis of the second edition — the age–utilisation gradient, determinants of service
volume, dynamic-panel tests of direction, and the sensitivity grids. **§12** adds case
complexity, disease burden and cadre-specific activity from three sources that arrived
later. **§13** adds the ministry's separation register, which for the first time lets the
workforce be read as two flows rather than one stock. Each layer is kept separate so
earlier results stay reproducible exactly as published, and so a reader can see which
conclusions changed.

### Rebuilding everything

```bash
python scripts/build_ch4_analysis.py        # all extended results -> output/analyse/ch4x/
python scripts/build_ch4_figures.py         # Figures A–Q, Thai and English
python scripts/build_ch4_handover.py        # parameter, synthesis, changelog tables
python scripts/build_report_figures_en.py   # English Figures 3–11 -> output/analyse/ch4/en/
python scripts/build_report_docx.py         # -> output/report/Chapter 4 - ....docx
```

Run in that order: the figures read the tables, and the manuscript reads both.

### The analysis modules

| Module | Contents |
|---|---|
| `scripts/ch4.py` | first-edition toolkit: loaders, the master panel, inequality indices, convergence, two-way FE, figure style, the bilingual label layer |
| `scripts/ch4x.py` | second-edition toolkit: GPP and insurance-population loaders, the age-curve estimator and its identification check, nested service models, Arellano–Bond difference GMM with diagnostics, multiplicity control, sensitivity grids, decoupled priority axes |
| `scripts/ch4e.py` | case-mix, epidemiology and cadre-activity toolkit: the DRG case-mix loader and its benchmark comparison, the NCD credibility screen and ascertainment test, the burden-weighted denominator counterfactual, cadre-specific workload and elasticity |
| `scripts/ch4l.py` | workforce-flow toolkit: the separation-register parser and its self-check, the administrative-event tests, the stock–flow reconciliation and implied-entry identity, fixed-effects Poisson attrition models, the between-province permutation test, the entry/exit variance decomposition, retirement pressure |
| `scripts/build_ch4_analysis.py` | driver — runs every extended analysis once and writes tidy CSVs |
| `scripts/build_ch4_figures.py` | Figures A–Q in both languages from one set of plotting code |
| `scripts/build_ch4_handover.py` | the four handover tables, with values read from the results rather than typed |

`ch4x.py`, `ch4e.py` and `ch4l.py` never mutate `ch4.py`'s outputs. The extended panel is written to
`output/analyse/ch4x/panel_extended.csv` with its variable definitions alongside in
`panel_dictionary.csv`.

### 1. Word report (English — the master text)

The narrative is held as structured text in **`scripts/report_content.py`** — one block per
heading, paragraph, list, figure, table, finding or note. To change a sentence, edit the
string there and re-run the builder; no layout code needs touching.

Typography follows academic-book rather than journal convention: Cambria for running text
at 11 pt, Calibri for captions, tables and running heads, first-line indents instead of
blank lines between paragraphs, horizontal-rule-only tables, and a running head with
centred folios. Citations are bracketed numerals resolved against the `REFERENCES` list.

### Two figure sets, one set of plotting code

The notebook draws its figures in Thai, which is what the dashboard and any Thai edition
need. The English report needs the same figures in English. Rather than maintaining two
copies of the plotting code, every display string in the figure cells passes through
`ch4.t()` and every label lookup through `ch4.hrh_label` / `ch4.spc_label` /
`ch4.service_label` / `ch4.tier_label`. `scripts/build_report_figures_en.py` then
re-executes the notebook's own figure cells with `ch4.set_lang("en")` and the output
redirected:

| Directory | Language | Consumed by |
|---|---|---|
| `output/analyse/ch4/` | Thai | notebook, dashboard, Thai edition |
| `output/analyse/ch4/en/` | English | the Word report |
| `output/analyse/ch4x/` | Thai | notebook §11–13, Thai edition |
| `output/analyse/ch4x/en/` | English | the Word report |

Only *display* strings are translated. DataFrame column names stay in Thai throughout,
because they are keys rather than labels and translating them would break every lookup
that depends on them. To add or reword a figure label in the numbered figures, edit
`EN_LABELS` in `scripts/ch4.py`; anything missing there falls through untranslated rather
than disappearing.

The lettered figures use a stricter variant. `FIG_TEXT` in `build_ch4_figures.py` holds
both languages against one key, and an unknown key raises immediately instead of falling
back. In a figure set that must exist in two languages, failing loudly is worth more than
falling back, because a Thai label inside an English figure is a defect the reader sees
and the author does not.

### 2. Dashboard report page

`web/report.html` renders the same chapter in the browser, bilingual, with the map
dashboard's existing look. Its prose is **a separate, hand-maintained copy** in:

- `web/content/report.th.md` — Thai (the default)
- `web/content/report.en.md` — English

Both are ordinary Markdown. Open either in any text editor, change a paragraph, save, and
reload the page. Four extra directives give the report its structure without writing HTML:

```markdown
{{figure:9 | caption text}}      insert a figure with a caption

:::finding 3                     a numbered finding box
text of the finding
:::

:::note label                    a boxed aside
text of the note
:::

:::stats                         a row of headline numbers
- +1.12% | need-weighted population, per year
:::
```

Refresh the figures and the manifest after re-running the notebook:

```bash
python scripts/build_report_assets.py            # copies figures into web/figures/
python scripts/build_report_assets.py --seed-th  # re-seed report.th.md from the Word text
```

The seeder refuses to overwrite a content file that has been hand-edited unless you also
pass `--force`, so local edits are safe.

**Note on the two copies.** The Word document and the dashboard hold the same text in two
places by design — the Word file is the master and the Markdown is a separate copy, so
editing one does not change the other. If keeping them in step becomes a chore, the
`--seed-th` path already converts the master into Markdown and can be made the routine.

### 3. Bilingual dashboard

Both pages default to Thai and carry a TH/EN toggle in the header; the choice is
remembered across pages. Interface strings live in **`web/i18n.js`** — one file, two
tables, edit the string you want to change. Years display as Buddhist Era in Thai and
Common Era in English; region and cadre names switch with the language.

### Outputs

| Path | Contents |
|---|---|
| `output/analyse/ch4/` | Figures 3–11 (300-dpi PNG + vector PDF) and 20+ tables (UTF-8-BOM CSV) |
| `output/analyse/ch4x/` | Figures A–Q, 69 result tables, the extended panel and its data dictionary |
| `output/report/` | the Word document |
| `web/figures/`, `web/content/` | dashboard figures and editable prose |
| `chapters/` | a standalone HTML version of the chapter |

Four tables in `output/analyse/ch4x/` are the handover to Chapters 5–7 and are worth
knowing by name:

| File | Contents |
|---|---|
| `tab_parameters_for_projection.csv` | every parameter offered forward, classified as observed, descriptive, model-estimated or normative, with its uncertainty, level, window, source, recommended use and caveat |
| `tab_synthesis_projection_evidence.csv` | each finding against the population-, service- and need-based approaches, with confidence and recommended use |
| `tab_changelog.csv` | every methodological change from the first edition, why it was made, and its effect on the interpretation |
| `tab_not_feasible.csv` | analyses specified for this revision that the data could not support, with what would be required |

### A note on what later editions withdrew

Several earlier conclusions did not survive re-analysis, and the chapter says so rather
than quietly restating them. Appendix 4.A of the report records all of them.

**Second edition.** The finding that nurse establishment leads service capacity rested on
a Nickell-biased estimator; the specification that corrects the bias is weakly identified
on this panel (first-stage F between 0.1 and 4.9 against a threshold of 10), so the
direction is now reported as unresolved. The priority-province classification used two axes
sharing the physician count, correlated −0.40 by construction. The 50-year dentist
convergence half-life came from a β that was not significant.

**Third edition.** Bangkok is excluded from provincial priority setting: its UC population
is largely enrolled with contracted private clinics that file no ministerial return, so the
MOPH count captures ~8% of its physicians against ~90% in the median province. Its
first-place priority ranking was an artefact. The second edition's claim that the
replacement axes "share no variable" was also wrong — they share the population denominator
— and a permutation test now reports how much of each pair's correlation is induced rather
than real. A comparability defect is fixed too: the all-sector robustness share had been
computed over 4 cells against the MOPH share's 20, so the two columns were never comparable.

**Fourth edition.** Nothing is withdrawn, but one description is corrected. The chapter
had reported convergence in provincial density without being able to say how it happened;
the separation register shows it ran through recruitment rather than retention, so the
instrument implied by the earlier text — holding staff in under-served provinces — is not
the one that moved the distribution. Two administrative events in the register are also
identified and set aside rather than read as attrition: the 2020 conversion of contract
staff to established posts, and the 2023–25 devolution of sub-district health promoting
hospitals, which moved 7,182 nurses and 6,518 public health officers out of the ministry
and is a structural break in the MOPH stock series.

The claim that service volume tracks beds is qualified: it holds for
outpatient visits, and for inpatient work it is substantially an artefact of measuring
output in bed-days, which the bed stock mechanically determines. Measured as admissions or
as DRG-adjusted output, supply explains under one per cent of within-province variation.
Every workload figure derived from the generic "outpatient visits per staff member" proxy
is now flagged provisional, because where a cadre-specific measure exists to check it, the
two correlate −0.46 for dentistry.

### Three questions the third edition set out to answer

| Question | Answer |
|---|---|
| Does case complexity determine service volume? | No. The apparent relationship is a pandemic composition effect that vanishes outside 2020–2022. But complexity-adjusted output grew at 5.2%/yr against 0.9% for bed-days, so the *measure* matters even though the *relationship* does not. |
| Does disease burden determine service volume? | No — it adds under one percentage point of explained variation where supply adds fifty. And recorded prevalence rises with the density of the physicians who record it, so it cannot serve as a need weight either. |
| What does cadre-specific activity add? | Pharmacy workload is distributed more equally than pharmacists are; dental workload less equally than dentists are; dental activity is supply-elastic above one. And the generic proxy the chapter used is a poor substitute — for dentistry, an actively misleading one. |

### Three questions the fourth edition set out to answer

| Question | Answer |
|---|---|
| Does service load or staffing density drive people out of MOPH? | Not within a province: none of 24 fixed-effects coefficients survives a multiplicity correction. Between provinces, workload does for physicians and nurses — and so does the provincial economy, which is the cleaner result because it shares no term with the outcome. MOPH loses staff fastest where the outside option is best, not where the posting is hardest. |
| Was the convergence in provincial density a retention story or a recruitment story? | Recruitment, in every profession. Entry carries 84% of the cross-provincial variance in physician growth and falls steeply with initial density (−0.41 physicians, −0.52 dentists, −0.67 nurses); separation is unrelated to it. The priority provinces of §4.16 are not haemorrhaging staff — their net physician growth is 0.03%/yr against 1.96% elsewhere. |
| What can the register hand to a projection model? | Gross flows the project has never had: separation by cause and implied entry, by province and profession, FY2018–2024. And a warning — retirement runs at a twelfth to two fifths of the level a stationary workforce would show and is growing at 14–22% a year, so it cannot be carried forward as a constant. |
