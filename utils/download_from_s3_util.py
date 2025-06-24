import os
import requests
import logging
from typing import List

# --- Configuration ---
# Set up basic logging to see the function's progress and any errors.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def download_files_from_urls(urls: List[str], output_dir: str) -> List[str]:
    """
    A helper function to download files from a list of URLs and save them to a directory.

    Args:
        urls (List[str]): A list of public URLs to download files from.
        output_dir (str): The local directory where files will be saved.

    Returns:
        List[str]: A list of full file paths for the successfully downloaded files.
    """
    logging.info(f"Starting download of {len(urls)} files to '{output_dir}'...")
    # Create the output directory if it doesn't already exist.
    os.makedirs(output_dir, exist_ok=True)
    downloaded_files = []

    for url in urls:
        try:
            # Get a clean filename from the URL, stripping any query parameters.
            filename = os.path.basename(url.split('?')[0])
            local_filepath = os.path.join(output_dir, filename)

            logging.info(f"Downloading {url} -> {local_filepath}")
            # Use a streaming request to handle large files efficiently.
            response = requests.get(url, stream=True)
            # Raise an HTTPError for bad responses (e.g., 404 Not Found, 500 Server Error).
            response.raise_for_status()

            # Save the file to the specified directory chunk by chunk.
            with open(local_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            downloaded_files.append(local_filepath)
            logging.info(f"Successfully downloaded {filename}.")

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to download {url}. Reason: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while processing {url}. Reason: {e}")

    logging.info(f"Finished downloading. {len(downloaded_files)} of {len(urls)} files saved to '{output_dir}'.")
    return downloaded_files


# --- Example Usage ---
# This block will only run if you execute this script directly (e.g., `python download_util.py`).
if __name__ == '__main__':
    # A list of example URLs to test the function.
    example_links = [
        "https://s3.ap-south-1.amazonaws.com/sm2.0-etl-prod-ap-south-1-274743989443/CLASS/NK/Survey_Status/9278662/2025/6.Jun/JKT+MIRACLE_9278662_NK_23_Jun_25.pdf",
        "https://s3.ap-south-1.amazonaws.com/sm2.0-etl-prod-ap-south-1-274743989443/CLASS/NK/Survey_Status/9311036/2025/6.Jun/OKEE+JOHN+T_9311036_NK_23_Jun_25.pdf",
        "https://s3.ap-south-1.amazonaws.com/sm2.0-etl-prod-ap-south-1-274743989443/CLASS/NK/Survey_Status/9311048/2025/6.Jun/OKEE+ULF_9311048_NK_23_Jun_25.pdf"
    ]
    
    # The directory where you want to save the downloaded files.
    target_directory = "downloaded_s3_pdfs"

    print(f"--- Running download utility example ---")
    # Call the function with the example links and target directory.
    successful_downloads = download_files_from_urls(urls=example_links, output_dir=target_directory)
    print(f"\n--- Example complete ---")
    print(f"Successfully downloaded files are located at: {successful_downloads}")

