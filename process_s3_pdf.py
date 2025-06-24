import os
import json
import requests
import logging
import tempfile
from dotenv import load_dotenv

# Your project's existing modules
from csm_module.csm_page_extractor import CSMPageExtractor
from schema.planned_machinery_survey_schema import planned_machinery_survey_concept

# The contextgem library, as used in your original extract.py
# Make sure this library is installed.
from contextgem import Document, DocumentLLM, Image, image_to_base64

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_data_from_images(image_paths: list, vlm_model: DocumentLLM, concept: dict) -> dict | None:
    """
    Sends a list of image paths to the VLM and extracts structured data based on a concept.

    Args:
        image_paths (list): A list of file paths to the page images.
        vlm_model (DocumentLLM): An initialized DocumentLLM instance.
        concept (dict): The concept schema for data extraction.

    Returns:
        A dictionary containing the extracted data, or None if extraction fails.
    """
    if not image_paths:
        logging.warning("Image paths list is empty. Nothing to process.")
        return None

    try:
        logging.info(f"Preparing {len(image_paths)} images for the VLM...")
        # Sort images by path to maintain page order (e.g., page_001.png, page_002.png)
        sorted_image_paths = sorted(image_paths)

        # Create a Document with all page images
        doc_images = [Image(mime_type="image/png", base64_data=image_to_base64(p)) for p in sorted_image_paths]
        doc = Document(images=doc_images)
        doc.add_concepts([concept])

        # Extract concepts from the document
        logging.info("Sending document to VLM for data extraction...")
        extracted_concepts = vlm_model.extract_concepts_from_document(doc)

        if not extracted_concepts or not extracted_concepts[0].extracted_items:
            logging.warning("VLM did not return any structured data.")
            return None

        # Return the structured data
        report_data = extracted_concepts[0].extracted_items[0].value
        logging.info("Successfully extracted data from VLM.")
        return report_data

    except Exception as e:
        logging.error(f"An error occurred during VLM data extraction: {e}", exc_info=True)
        return None


def process_pdf_from_url(pdf_url: str, final_output_dir: str):
    """
    The main function to process a single PDF from a public URL.
    It downloads the PDF, identifies survey pages, extracts them as images,
    parses the data from the images, and saves the final result as a single JSON file.

    Args:
        pdf_url (str): The public HTTPS URL to the PDF file.
        final_output_dir (str): The local directory to save the final JSON output.
    """
    logging.info(f"--- Starting processing for URL: {pdf_url} ---")
    try:
        # --- 1. Define Filenames ---
        pdf_filename = os.path.basename(pdf_url.split('?')[0]) # Get filename before any query params
        pdf_name_without_ext = os.path.splitext(pdf_filename)[0]
        json_filename = f"{pdf_name_without_ext}.json"

        # Use a single managed temporary directory for all intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            local_pdf_path = os.path.join(temp_dir, pdf_filename)
            images_output_dir = os.path.join(temp_dir, "images")

            # --- 2. Download PDF from Public URL ---
            logging.info(f"Downloading from {pdf_url} to temporary location...")
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()  # Will raise an HTTPError for bad responses (4xx or 5xx)
            with open(local_pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info("Download complete.")

            # --- 3. Identify and Extract CSM Pages as Images ---
            # NOTE: A Google API key is still required for the AI-powered extraction.
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                logging.error("GOOGLE_API_KEY not found in environment variables. This is required for data extraction.")
                return

            logging.info("Initializing CSMPageExtractor to find relevant pages...")
            extractor = CSMPageExtractor(api_key=google_api_key, temp_dir=os.path.join(temp_dir, "csm_temp"))
            result = extractor.save_csm_pages(local_pdf_path, output_dir=images_output_dir)
            
            csm_image_paths = result.get('saved_files', [])
            if not csm_image_paths:
                logging.warning(f"No CSM pages were found for {pdf_filename}. Stopping process for this file.")
                return

            logging.info(f"Found and saved {len(csm_image_paths)} CSM pages.")

            # --- 4. Extract Structured Data from All Images at Once ---
            logging.info("Initializing VLM...")
            vlm = DocumentLLM(
                model="gemini/gemini-2.0-flash", # Using the vision model
                api_key=google_api_key,
                role="extractor_vision",
            )

            report_data = extract_data_from_images(
                image_paths=csm_image_paths,
                vlm_model=vlm,
                concept=planned_machinery_survey_concept
            )

            if not report_data:
                logging.error(f"Failed to extract structured data for {pdf_filename}.")
                return

            # --- 5. Save Final JSON Output ---
            os.makedirs(final_output_dir, exist_ok=True)
            final_json_path = os.path.join(final_output_dir, json_filename)
            
            logging.info(f"Saving final structured data to {final_json_path}")
            with open(final_json_path, 'w') as f:
                json.dump(report_data, f, indent=4)
            
            logging.info(f"✅ Successfully processed and saved output to {final_json_path}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download file from URL {pdf_url}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"A critical error occurred during the processing of {pdf_url}: {e}", exc_info=True)
    finally:
        logging.info(f"--- Finished processing for URL: {pdf_url} ---")


# --- Main execution block ---
if __name__ == '__main__':
    # List of public HTTPS URLs to process
    pdf_links = [
        "https://s3.ap-south-1.amazonaws.com/sm2.0-etl-prod-ap-south-1-274743989443/CLASS/NK/Survey_Status/9278662/2025/6.Jun/JKT+MIRACLE_9278662_NK_23_Jun_25.pdf",
        "https://s3.ap-south-1.amazonaws.com/sm2.0-etl-prod-ap-south-1-274743989443/CLASS/NK/Survey_Status/9311036/2025/6.Jun/OKEE+JOHN+T_9311036_NK_23_Jun_25.pdf",
        "https://s3.ap-south-1.amazonaws.com/sm2.0-etl-prod-ap-south-1-274743989443/CLASS/NK/Survey_Status/9311048/2025/6.Jun/OKEE+ULF_9311048_NK_23_Jun_25.pdf"
    ]
    
    output_directory = "final_json_output"

    for link in pdf_links:
        process_pdf_from_url(
            pdf_url=link,
            final_output_dir=output_directory
        )
