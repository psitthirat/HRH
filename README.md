
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
