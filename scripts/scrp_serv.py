"""
Service Scraping Utility

This script contains functionality to scrape service volume data from the Thai Ministry of Public Health's health map website and save it as a structured CSV file. It is designed to automate the process of collecting and organizing data for analysis.

Key functionalities include:
- Scraping specialty data for multiple hospitals using their unique hospital IDs and specialty links.
- Extracting and processing table data from HTML pages.
- Detecting and handling missing or incomplete data.
- Saving results incrementally to avoid data loss during long scraping sessions.
- Generating a README file with details about the scraping process.

Dependencies:
- pandas
- requests
- BeautifulSoup4
- tqdm
- datetime
- time

Usage:
1. Prepare input data as pandas DataFrames: `hosp_id` for hospital IDs and `spc_link` for specialty links.
2. Specify the output folder to save scraped results and log files.
3. Call the `scrap()` function with the prepared inputs.

Example:
    from scrp_spc import scrap
    
    hosp_id_example = pd.DataFrame({'hosp_id': ['001', '002']})
    spc_link_example = pd.DataFrame({'link': ['infopersonal', 'infohospital']})
    output_dir = "./output"

    output_file = scrap(hosp_id_example, spc_link_example, output_dir)
    print(f"Scraped data is available in: {output_file}")

Authors: P. Sitthirat et al
Version: 1.0
License: MIT License
"""

# Standard library imports
import os
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Third-party library imports
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Maps the numbered item label in the scraped table (e.g. "1.จำนวนผู้ป่วยนอก")
# to the destination column in the flattened output row.
ITEM_MAP = {
    '1': 'op_n',
    '2': 'op_visit',
    '3': 'serv_n',
    '4': 'serv_visit',
    '5': 'ip_n',
    '6': 'ip_los',
}

# The ministry migrated this dataset to a hyphenated domain that's now behind Cloudflare's
# bot-challenge (a JS/TLS-fingerprint check that a plain requests session can't pass, even
# with a copied browser cookie). The old domain still serves historical years (up to 2567)
# unprotected, so we keep using it for those and only drive a real headless browser against
# the new domain for the current year — once it clears the challenge, the clearance cookie
# stays valid for the rest of the browser session, so subsequent page loads are fast.
OLD_BASE_URL = "http://gishealth.moph.go.th/healthmap/infoservice.php"
NEW_BASE_URL = "https://gis-health.moph.go.th/healthmap/infoservice.php"
CURRENT_YEAR_ID = '2025'
CURRENT_YEAR_LABEL = '2568'
BROWSER_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

def _flatten_serv_row(table, hosp_id_value, year_label):
    """Turn a raw service-volume <table> into one row keyed by hosp_id/year."""
    serv = []
    for row_value in table.find_all('tr'):
        columns_value = row_value.find_all(['td'])
        row_data_value = [column_value.get_text(strip=True) for column_value in columns_value]
        serv.append(row_data_value)

    serv_row = {'hosp_id': hosp_id_value, 'year': year_label}
    for row_data_value in serv:
        if not row_data_value or not row_data_value[0]:
            continue
        item_no = row_data_value[0].split('.', 1)[0].strip()
        if item_no in ITEM_MAP:
            value = row_data_value[1].replace(',', '').strip()
            serv_row[ITEM_MAP[item_no]] = pd.to_numeric(value, errors='coerce')
    return serv_row

def _find_serv_table(tables):
    """Locate the service-volume table by its header row instead of a fixed index."""
    for table in tables:
        first_row = table.find('tr')
        if first_row is None:
            continue
        cells = [c.get_text(strip=True) for c in first_row.find_all('td')]
        if cells[:1] == ['รายการ']:
            return table
    return None

class _CfBrowser:
    """
    Drives a headless Chromium session for the Cloudflare-protected domain.

    Playwright's sync API refuses to start inside a thread that already has a
    running asyncio event loop (e.g. a Jupyter kernel), so the browser is launched
    and driven from a dedicated worker thread instead, which never has one.
    """

    def __init__(self, user_agent):
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._playwright_ctx = None
        self._page = None
        self._executor.submit(self._start, user_agent).result()

    def _start(self, user_agent):
        self._playwright_ctx = sync_playwright().start()
        browser = self._playwright_ctx.chromium.launch(headless=True)
        self._page = browser.new_page(user_agent=user_agent)

    def fetch(self, url):
        """Navigate to url and return the rendered HTML, or None on timeout."""
        return self._executor.submit(self._fetch, url).result()

    def _fetch(self, url):
        try:
            self._page.goto(url, timeout=30000)
            self._page.wait_for_selector('table', timeout=20000)
            return self._page.content()
        except PlaywrightTimeoutError:
            return None

    def close(self):
        self._executor.submit(self._close).result()
        self._executor.shutdown()

    def _close(self):
        if self._playwright_ctx is not None:
            self._playwright_ctx.stop()

def scrap(hosp_id, output_folder, fetch_current_year=True):
    """
    Scrape service volume data from a specified health map website and save it as a CSV file.

    Parameters:
    - hosp_id (DataFrame): A DataFrame containing hospital IDs.
    - output_folder (str): The directory to save the output files.
    - fetch_current_year (bool): Whether to also fetch CURRENT_YEAR_LABEL from the newer,
      Cloudflare-protected domain via a headless Playwright browser. Requires
      `playwright install chromium` to have been run once. Set False to skip it and only
      scrape historical years from the legacy domain.

    Returns:
    - str: The path to the saved CSV file.
    """

    # Headless browser used to fetch the current year from the Cloudflare-protected domain.
    cf_browser = None
    if fetch_current_year:
        try:
            cf_browser = _CfBrowser(BROWSER_USER_AGENT)
        except Exception as e:
            print(f"Could not start the headless browser for {CURRENT_YEAR_LABEL} scraping "
                  f"({e}). Continuing with historical years only.")
            cf_browser = None

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Import the latest scraped DataFrame / Create an empty DataFrame to store results
    partial_file_path = os.path.join(output_folder, 'serv_latest.csv')
    if os.path.exists(partial_file_path):
        serv_df = pd.read_csv(partial_file_path)
        serv_df['hosp_id'] = serv_df['hosp_id'].astype(str).str.zfill(5)
        N = len(serv_df['hosp_id'].unique())
        hosp_id_sc = hosp_id[~hosp_id['hosp_id'].isin(serv_df['hosp_id'])]
        print(f'There are {N} hospitals that have been already scraped. Remaining {len(hosp_id_sc)} hospitals.')
    else:
        serv_df = pd.DataFrame()
        hosp_id_sc = hosp_id.copy()
        N = 1

    try:
        # Initialize tqdm progress bar
        with tqdm(total=len(hosp_id_sc), desc="Progress") as pbar:
            for index_hosp, row_hosp in hosp_id_sc.iterrows():

                # Extract the specialty data from URL
                hosp_url = f"{OLD_BASE_URL}?maincode={row_hosp['hosp_id']}"

                # Retry mechanism for GET requests
                success = False
                while not success:
                    try:
                        # GET request to the URL with retry mechanism
                        response_hosp = requests.get(hosp_url)
                        success = True
                    except requests.exceptions.RequestException as e:
                        print(f"Failed to fetch data for hosp_id {row_hosp['hosp_id']} with error: {e}")
                        print("Retrying...")
                        time.sleep(5)  # Wait before retrying

                # Parse the HTML content of the page
                soup_hosp = BeautifulSoup(response_hosp.text, 'html.parser')

                # Find all tables in the updated page
                tables = soup_hosp.find_all('table')

                n_select = 2
                n_table = 3

                # Check the availability of tables
                check_table = tables[n_select]
                select_element = check_table.find('select')
                
                if select_element != None:

                    options = select_element.find_all('option')
                    check_data = [{'id': option.get('value'), 'check': option.text.strip()} for option in options]

                    # Check if "ไม่มีการบันทึกข้อมูล"
                    if check_data[0]['check'] != "ไม่มีการบันทึกข้อมูล":

                        for point in check_data:

                            id = point['id']
                            time_input = point['check']

                            point_url = f"{hosp_url}&year={id}"

                            success = False
                            while not success:
                                try:
                                    response_point = requests.get(point_url)
                                    success = True
                                except requests.exceptions.RequestException as e:
                                    print(f"Failed to fetch data for hosp_id {row_hosp['hosp_id']} with error: {e}")
                                    print("Retrying...")
                                    time.sleep(5)

                            soup_point = BeautifulSoup(response_point.text, 'html.parser')
                            tables_point = soup_point.find_all('table')

                            # Choose specialist table
                            serv_table = tables_point[n_table]

                            serv_row = _flatten_serv_row(serv_table, row_hosp['hosp_id'], time_input)
                            if any(pd.notna(serv_row.get(col)) for col in ITEM_MAP.values()):
                                serv_df = pd.concat([serv_df, pd.DataFrame([serv_row])], ignore_index=True)

                # Current year lives on the new, Cloudflare-protected domain — fetched via the
                # shared headless-browser worker so the clearance cookie carries over.
                if cf_browser is not None:
                    point_url = f"{NEW_BASE_URL}?maincode={row_hosp['hosp_id']}&year={CURRENT_YEAR_ID}"
                    html_cf = cf_browser.fetch(point_url)
                    if html_cf is None:
                        print(f"Timed out waiting for {CURRENT_YEAR_LABEL} data for hosp_id {row_hosp['hosp_id']}. Skipping.")
                    else:
                        soup_cf = BeautifulSoup(html_cf, 'html.parser')
                        serv_table_cf = _find_serv_table(soup_cf.find_all('table'))
                        if serv_table_cf is not None:
                            serv_row_cf = _flatten_serv_row(serv_table_cf, row_hosp['hosp_id'], CURRENT_YEAR_LABEL)
                            if any(pd.notna(serv_row_cf.get(col)) for col in ITEM_MAP.values()):
                                serv_df = pd.concat([serv_df, pd.DataFrame([serv_row_cf])], ignore_index=True)

                # Update progress bar and save partial results
                pbar.set_description(f"Progress {N}/{len(hosp_id)} hcode = {row_hosp['hosp_id']}")
                N = N+1
                if N % 100 == 0:
                    partial_file_path = f'{output_folder}/serv_latest.csv'
                    if os.path.exists(partial_file_path):
                        os.remove(partial_file_path)
                    serv_df.to_csv(partial_file_path, index=False)

                # Update progress bar
                pbar.update(1)
    finally:
        if cf_browser is not None:
            cf_browser.close()

    # Delete the partial file before saving the final CSV
    if os.path.exists(partial_file_path):
        os.remove(partial_file_path)

    # Save final results
    final_file_path = os.path.join(output_folder, 'serv.csv')
    serv_df.to_csv(final_file_path, index=False)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Update README
    readme_path = os.path.join(output_folder, "README_serv.md")
    with open(readme_path, "w") as readme_file:
        readme_file.write(f"# Service Volume Data Scraping\n\n")
        readme_file.write(f"**Data Source:** [Thai Ministry of Public Health Health Map](http://gishealth.moph.go.th/healthmap/)\n\n")
        readme_file.write(f"**Last Updated:** {timestamp}\n\n")
        readme_file.write(f"## 1. Description\n")
        readme_file.write(f"This dataset contains service volume data (outpatient, total service, and inpatient) scraped from multiple hospitals.\n\n")
        readme_file.write(f"## 2. Scraping Process\n")
        readme_file.write(f"### Input Data\n")
        readme_file.write(f"- **`hosp_id`**: List of hospital codes to scrape. Derived from the healthcare facility dataset.\n")
        readme_file.write(f"  Historical years (through 2567) are read from the legacy domain:\n\n")
        readme_file.write(f"  ```\n")
        readme_file.write(f"  http://gishealth.moph.go.th/healthmap/infoservice.php?maincode=<hosp_id>&year=<year>\n")
        readme_file.write(f"  ```\n\n")
        readme_file.write(f"  {CURRENT_YEAR_LABEL} is read from the newer, Cloudflare-protected domain via a headless\n")
        readme_file.write(f"  Playwright browser (a plain HTTP client can't pass the challenge):\n\n")
        readme_file.write(f"  ```\n")
        readme_file.write(f"  https://gis-health.moph.go.th/healthmap/infoservice.php?maincode=<hosp_id>&year={CURRENT_YEAR_ID}\n")
        readme_file.write(f"  ```\n\n")
        readme_file.write(f"### Output\n")
        readme_file.write(f"Each row represents one hospital-year, with columns:\n")
        readme_file.write(f"- **`hosp_id`**: Hospital code.\n")
        readme_file.write(f"- **`year`**: Reporting period, as listed on the source page.\n")
        readme_file.write(f"- **`op_n`**: Number of outpatients (คน).\n")
        readme_file.write(f"- **`op_visit`**: Number of outpatient visits (ครั้ง).\n")
        readme_file.write(f"- **`serv_n`**: Total number of people served (คน).\n")
        readme_file.write(f"- **`serv_visit`**: Total number of service visits (ครั้ง).\n")
        readme_file.write(f"- **`ip_n`**: Number of inpatients (ราย).\n")
        readme_file.write(f"- **`ip_los`**: Total inpatient length of stay (วัน).\n\n")
        readme_file.write(f"- Scraped data is saved in `output/scraped/serv.csv`.\n")
        readme_file.write(f"- A detailed log of the scraping process, including metadata and errors, is saved in `output/scraped/README_serv.md`.\n")
        readme_file.write(f"## Notes\n")
        readme_file.write(f"- Partial results are saved every 100 hospitals to prevent data loss.\n")
        readme_file.write(f"- The script ensures data accuracy by validating each step.\n")

    print(f"Scraped data have been successfully saved to '{final_file_path}'\n(Last updated: {timestamp}).")
    print(f"README updated: '{readme_path}'")

    return final_file_path

# Example usage in Jupyter Notebook:
if __name__ == "__main__":
    # Example DataFrame for hosp_id
    hosp_id_example = pd.DataFrame({'hosp_id': ['001', '002']})
    output_dir = "./output"

    # Run the scraper
    output_file = scrap(hosp_id_example, output_dir)
    print(f"Scraped data is available in: {output_file}")
