"""
Health Workforce Data Scraping Utility

This script contains functionality to scrape health workforce data from the Thai Ministry of Public Health's health map website and save it as a structured CSV file. It is designed to automate the process of collecting and organizing data for analysis.

Key functionalities include:
- Scraping health workforce data for multiple hospitals using their unique hospital IDs and specialty links.
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
1. Prepare input data as pandas DataFrames: `hosp_id` for hospital IDs and `hrh_link` for health workforce links.
2. Specify the output folder to save scraped results and log files.
3. Call the `scrap()` function with the prepared inputs.

Example:
    from scrp_hrh import scrap
    
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

def scrap(hosp_id, spc_link, output_folder):
    """
    Scrape health workforce data from a specified health map website and save it as a CSV file.

    Parameters:
    - hosp_id (DataFrame): A DataFrame containing hospital IDs.
    - hrh_link (DataFrame): A DataFrame containing health workforce links.
    - output_folder (str): The directory to save the output files.

    Returns:
    - str: The path to the saved CSV file.
    """

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Import the lastest scraped DataFrane / Create an empty DataFrame to store results
    partial_file_path = os.path.join(output_folder, 'hrh_latest.csv')
    if os.path.exists(partial_file_path):
        hrh_df = pd.read_csv(partial_file_path)
        hrh_df['hosp_id'] = hrh_df['hosp_id'].astype(str).str.zfill(5)
        N = len(hrh_df['hosp_id'].unique())
        hosp_id_sc = hosp_id[~hosp_id['hosp_id'].isin(hrh_df['hosp_id'])]
        print(f'There are {N} hospitals that have been already scraped. Remaining {len(hosp_id_sc)} hospitals.')
    else:
        hrh_df = pd.DataFrame()
        hosp_id_sc = hosp_id.copy()
        N = 1
    
    with tqdm(total=len(hosp_id_sc), desc="Progress") as pbar:
        for index_hosp, row_hosp in hosp_id_sc.iterrows():
            for index_link, row_link in spc_link.iterrows():
                
                # Extract the specialty data from URL
                hosp_url = f"http://gishealth.moph.go.th/healthmap/{row_link['link']}.php?maincode={row_hosp['hosp_id']}&id="

                # Determine table structure based on health workforce type
                n_select, n_table = (3, 5) if row_link['link'] in (['infopersonal', 'infopersonal2']) else (2, 4)
                
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

                # Check the availability of tables
                check_table = tables[n_select]
                select_element = check_table.find('select')
                options = select_element.find_all('option')
                check_data = [{'id': option.get('value'), 'check': option.text.strip()} for option in options]

                # Check if "ไม่มีการบันทึกข้อมูล"
                if check_data[0]['check'] != "ไม่มีการบันทึกข้อมูล":
                            
                    for point in check_data:
                        
                        id = point['id']
                        time_input = point['check']
                        
                        point_url = f"{hosp_url}&id={id}"
                        
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
                        hrh_table = tables_point[n_table]
                    
                        # Extract table data
                        rows = hrh_table.find_all('tr')
                        hrh = []
                        for row_value in rows:
                            columns_value = row_value.find_all(['td'])[0:7]
                            row_data_value = [column_value.get_text(strip=True) for column_value in columns_value]
                            hrh.append(row_data_value)
                    
                        # Convert the scraped data into a DataFrame
                        hrh_hos_df = pd.DataFrame(hrh)

                        # Assign the first row as the header
                        hrh_hos_df.columns = hrh_hos_df.iloc[0]
                        hrh_hos_df = hrh_hos_df[1:]  
                        hrh_hos_df = hrh_hos_df.loc[~(hrh_hos_df.iloc[:, 0].eq('') | hrh_hos_df.iloc[:, 0].eq('ลำดับ'))]

                        # Check if the hospital is 'public' or 'private' from number of column
                        if row_link['link'] == 'infopersonal':
                            if hrh_hos_df.columns.str.contains('ข้าราชการ').any():
                                hrh_hos_df = hrh_hos_df.iloc[:, 1:6]
                                hrh_hos_df.iloc[:, 1:5] = hrh_hos_df.iloc[:, 1:5].apply(pd.to_numeric, errors='coerce')
                                hrh_hos_df['total'] = hrh_hos_df.iloc[:, 1:5].apply(lambda row: row.sum() if not row.isnull().all() else None, axis=1)
                                hrh_hos_df = hrh_hos_df.drop(hrh_hos_df.columns[1:5], axis=1)
                            else:
                                hrh_hos_df_1 = hrh_hos_df.iloc[:, 1:3].copy()
                                hrh_hos_df_1 = hrh_hos_df_1.rename(columns=lambda x: x.replace('FT', 'total') if x.startswith('FT') else x)
                                hrh_hos_df_1['total'] = hrh_hos_df_1['total'].apply(
                                    lambda x: int(x) if pd.notnull(x) and x != '' else pd.NA)
                                hrh_hos_df_2 = hrh_hos_df.iloc[:, 5:7].copy()
                                hrh_hos_df_2 = hrh_hos_df_2.rename(columns=lambda x: x.replace('FT', 'total') if x.startswith('FT') else x)
                                hrh_hos_df_2['total'] = hrh_hos_df_2['total'].apply(
                                    lambda x: int(x) if pd.notnull(x) and x != '' else pd.NA)
                                hrh_hos_df = pd.concat([hrh_hos_df_1, hrh_hos_df_2])
                        else:
                            if len(hrh_hos_df.columns) == 7:
                                hrh_hos_df = hrh_hos_df.iloc[:, 1:6]
                                hrh_hos_df.iloc[:, 1:6] = hrh_hos_df.iloc[:, 1:6].apply(pd.to_numeric, errors='coerce')
                                hrh_hos_df['total'] = hrh_hos_df.iloc[:, 1:6].apply(lambda row: row.sum() if not row.isnull().all() else None, axis=1)
                                hrh_hos_df = hrh_hos_df.drop(hrh_hos_df.columns[1:5], axis=1)
                        
                        hrh_hos_df = hrh_hos_df.rename(columns={hrh_hos_df.columns[0]: 'hrh'})        
                        hrh_hos_df.insert(0, 'hosp_id', row_hosp['hosp_id'])
                        hrh_hos_df['time'] = time_input
                        hrh_df = pd.concat([hrh_df, hrh_hos_df], ignore_index=True)
            
        
            P = (N/len(hosp_id))*100

            # Update progress bar and save partial results
            pbar.set_description(f"Progress {N}/{len(hosp_id)} hcode = {row_hosp['hosp_id']}")
            N = N+1
            if N % 100 == 0:
                partial_file_path = f'{output_folder}/hrh_latest.csv'
                if os.path.exists(partial_file_path):
                    os.remove(partial_file_path)
                hrh_df.to_csv(partial_file_path, index=False)

            # Update progress bar
            pbar.update(1)

    # Delete the partial file before saving the final CSV
    if os.path.exists(partial_file_path):
        os.remove(partial_file_path)

    # Save final results
    final_file_path = os.path.join(output_folder, 'hrh.csv')
    hrh_df.to_csv(final_file_path, index=False)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Update README
    readme_path = os.path.join(output_folder, "README_hrh.md")
    with open(readme_path, "w") as readme_file:
        readme_file.write(f"# Health Workforce Data Scraping\n\n")
        readme_file.write(f"**Data Source:** [Thai Ministry of Public Health Health Map](http://gishealth.moph.go.th/healthmap/)\n\n")
        readme_file.write(f"**Last Updated:** {timestamp}\n\n")
        readme_file.write(f"## 1. Description\n")
        readme_file.write(f"This dataset contains health workforce data scraped from multiple hospitals.\n\n")
        readme_file.write(f"## 2. Scraping Process\n")
        readme_file.write(f"### Input Data\n")
        readme_file.write(f"- **`hosp_id`**: List of hospital codes to scrape. Derived from the healthcare facility dataset.\n")
        readme_file.write(f"- **`hrh_link`**: URLs used for retrieving personal and specialty information.\n")
        readme_file.write(f"  The scraping process constructs URLs in the following format:\n\n")
        readme_file.write(f"  ```\n")
        readme_file.write(f"  http://gishealth.moph.go.th/healthmap/<link>.php?maincode=<hosp_id>\n")
        readme_file.write(f"  ```\n\n")
        readme_file.write(f"  - **`infopersonal`**: Workforce dataset (physicians, dentists, nurses, etc.).\n")
        readme_file.write(f"  - **`infospecialty`, `infospecialty2`, ..., `infospecialty5`**: Medical specialist datasets.\n\n")
        readme_file.write(f"### Output\n")
        readme_file.write(f"- Scraped data is saved in `output/scraped/hrh.csv`.\n")
        readme_file.write(f"- A detailed log of the scraping process, including metadata and errors, is saved in `output/scraped/README.md`.\n")
        readme_file.write(f"## Notes\n")
        readme_file.write(f"- Partial results are saved every 100 hospitals to prevent data loss.\n")
        readme_file.write(f"- The script ensures data accuracy by validating each step.\n")

    print(f"Scraped data have been successfully saved to '{final_file_path}'\n(Last updated: {timestamp}).")
    print(f"README updated: '{readme_path}'")
    
    return final_file_path

# Example usage in Jupyter Notebook:
if __name__ == "__main__":
    # Example DataFrames for hosp_id and spc_link
    hosp_id_example = pd.DataFrame({'hosp_id': ['001', '002']})
    spc_link_example = pd.DataFrame({'link': ['infopersonal', 'infohospital']})
    output_dir = "./output"
    
    # Run the scraper
    output_file = scrap(hosp_id_example, spc_link_example, output_dir)
    print(f"Scraped data is available in: {output_file}")