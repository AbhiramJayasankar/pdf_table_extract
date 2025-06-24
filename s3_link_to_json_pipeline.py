import os
import json
import logging
import tempfile
from dotenv import load_dotenv

# --- Import existing functions and classes from your utils ---

# 1. Import the downloader function
from utils.download_from_s3_util import download_files_from_urls

# 2. Import the core class used by save_csm_images.py
from utils.csm_page_extractor import CSMPageExtractor

# 3. Import the per-image extraction function directly from the util file
from utils.extract_func import extract_json_from_image

# --- Configuration ---
load_dotenv()
# Using a simpler format for cleaner lines, and adding the requested logger silencing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logging.getLogger("LiteLLM").setLevel(logging.WARNING)


def run_full_pipeline(pdf_url: str, final_output_dir: str):
    """
    Orchestrates the entire pipeline by calling the existing utility functions in sequence.

    Args:
        pdf_url (str): The public URL of the PDF to process.
        final_output_dir (str): The directory to save the final JSON output.
    """
    logging.info("====================================================================")
    logging.info(f"--- Starting Pipeline for: {pdf_url} ---")
    logging.info("====================================================================")
    print() # Add space
    
    # Use a managed temporary directory for all intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        # --- STEP 1: Download the PDF using the downloader util ---
        logging.info("Step 1: Downloading PDF...")
        downloaded_pdf_paths = download_files_from_urls(urls=[pdf_url], output_dir=temp_dir)
        
        if not downloaded_pdf_paths:
            logging.error("Download step failed. Aborting pipeline for this URL.")
            return
        
        local_pdf_path = downloaded_pdf_paths[0]
        logging.info(f"PDF downloaded to: {local_pdf_path}")

        logging.info("--------------------------------------------------------------------")
        print() # Add space

        # --- STEP 2: Extract CSM Images using the extractor class ---
        logging.info("Step 2: Extracting CSM pages as images...")
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            logging.error("GOOGLE_API_KEY not found. Aborting.")
            return
            
        image_extractor = CSMPageExtractor(api_key=google_api_key, temp_dir=os.path.join(temp_dir, "csm_temp"))
        images_output_dir = os.path.join(temp_dir, "images")
        
        extraction_result = image_extractor.save_csm_pages(local_pdf_path, output_dir=images_output_dir)
        csm_image_paths = extraction_result.get('saved_files', [])

        if not csm_image_paths:
            logging.warning("CSM image extraction did not yield any images. Aborting.")
            return
        logging.info(f"Successfully extracted {len(csm_image_paths)} images.")

        logging.info("--------------------------------------------------------------------")
        print() # Add space

        # --- STEP 3: Call the per-page function for each image ---
        logging.info("Step 3: Extracting JSON by calling the function for each image...")
        print() # Add space
        all_pages_data = []
        for image_path in sorted(csm_image_paths): # Sort to maintain page order
            logging.info(f" - Processing image: {os.path.basename(image_path)}")
            # Call the function from extract_func.py for one image
            json_data = extract_json_from_image(image_path)
            if json_data:
                all_pages_data.append(json_data)
            else:
                logging.warning(f"   No data extracted for {os.path.basename(image_path)}.")
            
            print() # Add space after each extraction attempt
        
        if not all_pages_data:
            logging.error("JSON extraction step failed for all pages. Aborting.")
            return

        logging.info("--------------------------------------------------------------------")
        print() # Add space

        # --- STEP 4: Save the final list of JSON objects ---
        logging.info("Step 4: Saving final JSON output...")
        os.makedirs(final_output_dir, exist_ok=True)
        pdf_filename = os.path.basename(pdf_url.split('?')[0])
        json_filename = f"{os.path.splitext(pdf_filename)[0]}.json"
        final_json_path = os.path.join(final_output_dir, json_filename)
        
        # The final output is now a list of dictionaries
        with open(final_json_path, 'w') as f:
            json.dump(all_pages_data, f, indent=4)
        
        logging.info(f"✅ Pipeline complete! Final JSON saved to: {final_json_path}")
        logging.info("====================================================================")
        print("\n") # Add extra space at the very end


# --- Main execution block to run the pipeline ---
if __name__ == '__main__':
    url_to_process = "https://s3.ap-south-1.amazonaws.com/sm2.0-etl-prod-ap-south-1-274743989443/CLASS/NK/Survey_Status/9278662/2025/6.Jun/JKT+MIRACLE_9278662_NK_23_Jun_25.pdf"
    output_directory = "final_json_output"

    run_full_pipeline(pdf_url=url_to_process, final_output_dir=output_directory)