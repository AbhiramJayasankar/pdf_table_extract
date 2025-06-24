import os
import json
import logging
import tempfile
import base64
import shutil
from pathlib import Path
from typing import List, Dict, Any

import requests
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path
from google.generativeai import types
from contextgem import Document, DocumentLLM, Image as ContextGemImage, image_to_base64

# Assuming the schema is in a file named `planned_machinery_survey_schema.py`
# in a directory called `schema`.
# If your structure is different, you may need to adjust the import.
from schema.planned_machinery_survey_schema import planned_machinery_survey_concept


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


# 2. Import the core class used by save_csm_images.py
"""
CSM Page Extractor Module
Extracts Continuous Machinery Survey (CMS) pages from maritime PDF documents
"""
logger = logging.getLogger(__name__)


class CSMPageExtractor:
    """Extracts CSM (Continuous Machinery Survey) pages from PDF documents"""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp",
                 temp_dir: str = "temp_csm_pages"):
        """
        Initialize CSM Page Extractor

        Args:
            api_key: Google AI API key
            model_name: Gemini model to use
            temp_dir: Directory for temporary files
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.temp_files = []

        # Initialize Gemini client
        genai.configure(api_key=api_key)
        self.client = genai
        self.model = model_name

        logger.info(f"Initialized CSM Page Extractor with model: {model_name}")

    def add_page_number(self, image: Image.Image, page_number: int) -> Image.Image:
        """
        Add page number overlay to an image

        Args:
            image: PIL Image object
            page_number: Page number to add

        Returns:
            Modified PIL Image with page number
        """
        # Create a copy to avoid modifying the original
        img = image.copy()
        draw = ImageDraw.Draw(img)

        # Try to use a nice font, fallback to default if not available
        font_size = 40
        try:
            # Try common font paths
            font_paths = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "C:\\Windows\\Fonts\\Arial.ttf",
                "arial.ttf"
            ]
            font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break
            if not font:
                font = ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Could not load custom font: {e}")
            font = ImageFont.load_default()

        # Calculate text position
        margin = 20
        padding = 10
        text = f"Page {page_number}"

        # Get text bounding box using the recommended method
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Position in top-right corner
        x = img.width - text_width - margin - padding
        y = margin

        # Draw white background rectangle
        rect_x1 = x - padding
        rect_y1 = y - padding
        rect_x2 = x + text_width + padding
        rect_y2 = y + text_height + padding

        draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2],
                       fill='white', outline='black', width=2)

        # Draw the page number
        draw.text((x, y), text, fill='black', font=font)

        logger.debug(f"Added page number {page_number} to image")
        return img

    def pdf_to_numbered_images(self, pdf_path: str, dpi: int = 200) -> List[Dict[str, Any]]:
        """
        Convert PDF to numbered images with base64 encoding

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for conversion

        Returns:
            List of dicts with 'page_number', 'base64_data', and 'temp_path'
        """
        logger.info(f"Converting PDF to images: {pdf_path}")

        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Convert PDF to PIL images
        try:
            pil_images = convert_from_path(pdf_path, dpi=dpi)
            logger.info(f"Converted PDF to {len(pil_images)} images at {dpi} DPI")
        except Exception as e:
            logger.error(f"Error converting PDF: {e}")
            raise

        # Process each page
        numbered_images = []

        for i, pil_img in enumerate(pil_images):
            page_num = i + 1
            logger.info(f"Processing page {page_num}/{len(pil_images)}")

            # Add page number overlay
            numbered_img = self.add_page_number(pil_img, page_num)

            # Save to temporary file
            temp_file = self.temp_dir / f"page_{page_num:03d}.png"
            numbered_img.save(temp_file, "PNG", optimize=True)
            self.temp_files.append(str(temp_file))

            # Convert to base64
            with open(temp_file, 'rb') as f:
                base64_data = base64.b64encode(f.read()).decode('utf-8')

            numbered_images.append({
                'page_number': page_num,
                'base64_data': base64_data,
                'temp_path': str(temp_file)
            })

            logger.debug(f"Page {page_num} converted and encoded")

        logger.info(f"✅ Successfully processed {len(numbered_images)} pages")
        return numbered_images

    def identify_csm_pages(self, images_base64: List[Dict[str, str]]) -> List[int]:
        """
        Identify pages containing CSM (Continuous Machinery Survey) content

        Args:
            images_base64: List of dicts with 'page_number' and 'base64_data'

        Returns:
            List of page numbers containing CSM content
        """
        logger.info(f"Identifying CSM pages from {len(images_base64)} images")

        # Build the prompt
        prompt = """You are an intelligent assistant analyzing a maritime survey document. Each page image has a page number clearly marked in the top-right corner.

Your task is to identify ALL pages that are part of the 'Planned Machinery Survey' section, which is related to the Continuous Machinery Survey (CMS).

Look for the following indicators:
- The exact heading: 'NK-SHIPS: Survey Status - Planned Machinery Survey'
- Text that explicitly mentions 'System applied: CMS: Continuous Machinery Survey'
- Tables containing machinery survey data, often with survey codes (e.g., 311001, 313001).
- Pages that are clear continuations of the planned machinery survey tables from a previous page.

The planned machinery survey section can span multiple consecutive pages. Ensure you identify all pages belonging to this section.

Respond with a JSON object in the following format:
{
  "found": true/false,
  "page_numbers": [list of integer page numbers],
  "description": "A brief summary of your findings."
}

If no such pages are found, set "found" to false and provide an empty list for "page_numbers".
"""

        # Build content list with prompt and images
        content = [prompt]

        for img_data in images_base64:
            image_part = {
                "mime_type": "image/png",
                "data": base64.b64decode(img_data['base64_data'])
            }
            content.append(image_part)

        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(
                content,
                generation_config=types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                )
            )

            # Parse the response
            result = json.loads(response.text)
            #logger.info(f"LLM Response: {result}")

            if result.get('found', False):
                page_numbers = result.get('page_numbers', [])
                logger.info(f"✅ Identified {len(page_numbers)} pages with CSM content: {page_numbers}")
                return page_numbers
            else:
                logger.warning("❌ No CSM pages found")
                return []

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from LLM response: {e}")
            logger.error(f"Raw response: {response.text}")
            return []
        except Exception as e:
            logger.error(f"Error identifying pages: {e}")
            return []

    def extract_csm_pages(self, pdf_path: str, dpi: int = 200) -> List[int]:
        """
        Main method to extract CSM pages from a PDF

        This method:
        1. Converts PDF to images (page-wise)
        2. Adds page numbers to each image
        3. Passes images to LLM for CSM page identification
        4. Returns list of page numbers containing CSM information

        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for PDF conversion (default: 200)

        Returns:
            List of page numbers that contain CSM information
        """
        try:
            logger.info(f"Starting CSM page extraction from: {pdf_path}")

            # Step 1: Convert PDF to numbered images
            numbered_images = self.pdf_to_numbered_images(pdf_path, dpi)

            # Step 2: Identify CSM pages using LLM
            csm_page_numbers = self.identify_csm_pages(numbered_images)

            logger.info(f"✅ CSM page extraction complete. Found {len(csm_page_numbers)} pages.")
            return csm_page_numbers

        except Exception as e:
            logger.error(f"Error in CSM page extraction: {e}")
            raise
        finally:
            # Cleanup temporary files
            self.cleanup()

    def save_csm_pages(self, pdf_path: str, output_dir: str = "csm_pages",
                       dpi: int = 200) -> Dict[str, Any]:
        """
        Extract and save CSM pages to a directory

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save CSM pages
            dpi: Resolution for PDF conversion

        Returns:
            Dictionary with extraction results and saved file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        try:
            # Convert PDF to numbered images
            numbered_images = self.pdf_to_numbered_images(pdf_path, dpi)

            # Identify CSM pages
            csm_page_numbers = self.identify_csm_pages(numbered_images)

            # Save identified pages
            saved_files = []
            for img_data in numbered_images:
                if img_data['page_number'] in csm_page_numbers:
                    # Copy the temp file to output directory
                    src_path = img_data['temp_path']
                    dst_path = output_path / f"csm_page_{img_data['page_number']:03d}.png"

                    if Path(src_path).exists():
                        shutil.copy2(src_path, dst_path)
                        saved_files.append(str(dst_path))
                        logger.debug(f"Saved CSM page {img_data['page_number']} to {dst_path}")

            result = {
                'pdf_path': pdf_path,
                'total_pages': len(numbered_images),
                'csm_pages': csm_page_numbers,
                'csm_page_count': len(csm_page_numbers),
                'saved_files': saved_files,
                'output_directory': str(output_path)
            }

            logger.info(f"✅ Saved {len(saved_files)} CSM pages to {output_dir}")
            return result

        except Exception as e:
            logger.error(f"Error saving CSM pages: {e}")
            raise
        finally:
            # Cleanup temporary files
            self.cleanup()

    def cleanup(self):
        """Clean up temporary files"""
        logger.info("Cleaning up temporary files...")

        # Remove temp files
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Could not delete {temp_file}: {e}")

        # Remove temp directory if empty
        try:
            if self.temp_dir.exists() and not any(self.temp_dir.iterdir()):
                self.temp_dir.rmdir()
                logger.info(f"Removed empty temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Could not remove temp directory: {e}")

        self.temp_files.clear()
        logger.info("✅ Cleanup completed")



# Load environment variables from a .env file
load_dotenv()

def extract_json_from_image(image_path: str) -> dict | None:
    """
    Processes a single image file, extracts structured data using a
    Vision Language Model (VLM), and returns the data as a Python dictionary.

    Args:
        image_path (str): The full path to the image file to process.

    Returns:
        dict | None: A dictionary containing the extracted data if successful,
                     otherwise None.
    """
    # --- 1. Configuration & Validation ---
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        print("Error: GOOGLE_API_KEY not found in environment variables.")
        return None

    if not os.path.isfile(image_path):
        print(f"Error: Image file not found at '{image_path}'")
        return None

    print(f"Processing: {image_path}")

    try:
        # --- 2. Initialize the VLM ---
        # It's often more efficient to initialize this once outside the function
        # if you are processing many images in a loop. For a self-contained
        # function, initializing it here is fine.
        vlm = DocumentLLM(
            model="gemini/gemini-2.0-flash",
            api_key=google_api_key,
            role="extractor_vision",
        )

        # --- 3. Prepare the document for the VLM ---
        doc_image = ContextGemImage(mime_type="image/jpeg", base64_data=image_to_base64(image_path))
        doc = Document(images=[doc_image])
        doc.add_concepts([planned_machinery_survey_concept])

        # --- 4. Extract concepts from the document ---
        extracted_concepts = vlm.extract_concepts_from_document(doc)

        # --- 5. Validate and return the extracted data ---
        if not extracted_concepts or not extracted_concepts[0].extracted_items:
            print(f"   [INFO] No data was extracted for {os.path.basename(image_path)}.")
            return None

        # Retrieve the structured data from the first extracted item
        report_data = extracted_concepts[0].extracted_items[0].value
        print(f"   -> Successfully extracted data for {os.path.basename(image_path)}.")

        return report_data

    except Exception as e:
        print(f"   [ERROR] An error occurred while processing {image_path}. Reason: {e}")
        return None

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