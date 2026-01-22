# Specialty Data Scraping

**Data Source:** [Thai Ministry of Public Health Health Map](http://gishealth.moph.go.th/healthmap/)

**Last Updated:** 2024-12-30 15:14:44

## Description
This dataset contains medical specialty data scraped from multiple hospitals.

## 2. Scraping Process
### Input Data
- **`hosp_id`**: List of hospital codes to scrape. Derived from the healthcare facility dataset.
- **`spc_link`**: URLs used for retrieving personal and specialty information.
  The scraping process constructs URLs in the following format:

  ```
  http://gishealth.moph.go.th/healthmap/<link>.php?maincode=<hosp_id>
  ```

  - **`infopersonal`**: Workforce dataset (physicians, dentists, nurses, etc.).
  - **`infospecialty`, `infospecialty2`, ..., `infospecialty5`**: Medical specialist datasets.

### Output
- Scraped data is saved in `output/scraped/spc.csv`.
- A detailed log of the scraping process, including metadata and errors, is saved in `output/scraped/README.md`.

## Notes
- Partial results are saved every 100 hospitals to prevent data loss.
- The script ensures data accuracy by validating each step.
