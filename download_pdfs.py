import pandas as pd
import requests
import os
import re

def download_pdfs_from_excel(excel_path, sheet_name=0):
    """
    Reads an Excel file, extracts PDF links and corresponding names,
    and downloads them into a dedicated folder.

    Args:
        excel_path (str): The path to the Excel file.
        sheet_name (str or int): The name or index of the sheet to read.
                                 Defaults to the first sheet (0).
    """
    # Define the folder where PDFs will be saved
    download_folder = "downloaded_pdfs"

    # Create the folder if it doesn't exist
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
        print(f"Created folder: {download_folder}")

    try:
        # Read the Excel file into a pandas DataFrame
        # Assumes column names are 'vesselName' and 'linkForSyla' based on the image
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        
        # Check if required columns exist
        if 'vesselName' not in df.columns or 'linkForSyia' not in df.columns:
            print("Error: Excel file must contain 'vesselName' and 'linkForSyia' columns.")
            return

        print(f"Found {len(df)} rows in the Excel file.")

        # Iterate over each row in the DataFrame
        for index, row in df.iterrows():
            vessel_name = row['vesselName']
            pdf_url = row['linkForSyia']

            # --- Input Validation ---
            # Check if vessel_name or pdf_url is empty or not a string
            if not isinstance(vessel_name, str) or not vessel_name.strip():
                print(f"Skipping row {index + 2}: Invalid or empty vessel name.")
                continue
            
            if not isinstance(pdf_url, str) or not pdf_url.startswith('http'):
                print(f"Skipping row {index + 2}: Invalid or empty URL for '{vessel_name}'.")
                continue

            # --- Filename Sanitization ---
            # Remove any characters that are not letters, numbers, hyphens, or underscores
            sanitized_name = re.sub(r'[^\w\s-]', '', vessel_name).strip()
            # Replace spaces or multiple hyphens with a single hyphen
            sanitized_name = re.sub(r'[-\s]+', '-', sanitized_name)
            
            # Construct the full path for the PDF file
            file_name = f"{sanitized_name}.pdf"
            file_path = os.path.join(download_folder, file_name)

            print(f"\nDownloading for '{vessel_name}'...")
            print(f"URL: {pdf_url}")

            try:
                # --- File Download ---
                # Make a GET request to the URL
                response = requests.get(pdf_url, stream=True, timeout=30)
                
                # Check if the request was successful (status code 200)
                response.raise_for_status() 

                # Write the content to the local file
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"SUCCESS: Saved to {file_path}")

            except requests.exceptions.RequestException as e:
                # Handle connection errors, timeouts, etc.
                print(f"ERROR: Could not download from {pdf_url}. Reason: {e}")
            except Exception as e:
                # Handle other potential errors during file writing etc.
                print(f"An unexpected error occurred: {e}")

        print("\n--------------------")
        print("Download process finished.")

    except FileNotFoundError:
        print(f"Error: The file '{excel_path}' was not found.")
    except Exception as e:
        print(f"An error occurred while reading the Excel file: {e}")


if __name__ == "__main__":
    # --- IMPORTANT ---
    # Replace 'your_excel_file.xlsx' with the actual name of your Excel file.
    # Make sure the Excel file is in the same directory as this script,
    # or provide the full path to the file.
    excel_file = "NK.xlsx"
    download_pdfs_from_excel(excel_file)
