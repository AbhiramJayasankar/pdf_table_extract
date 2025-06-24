"""
CSM Page Extractor Module
Extracts Continuous Machinery Survey (CMS) pages from maritime PDF documents
"""

import os
import json
import base64
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any

from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path
import google.generativeai as genai
from google.generativeai import types

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
            logger.info(f"LLM Response: {result}")

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


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize extractor with the provided API key
    API_KEY = "AIzaSyDAmNAseyPYvOZEZ1WebRLyuHVr2hMteoQ"
    extractor = CSMPageExtractor(api_key=API_KEY)

    # Path to the PDF file.
    # Make sure the 'pdfs' directory exists and contains the specified PDF file.
    pdf_file = os.path.join("pdfs", "AL_AGAILA_1.pdf")
    
    if not os.path.exists(pdf_file):
        logger.error(f"The PDF file was not found at: {pdf_file}")
        logger.error("Please ensure the file exists and the path is correct.")
    else:
        try:
            # --- Choose one of the methods below to run ---

            # # Method 1: Just get page numbers
            # print("\n--- Method 1: Getting CSM page numbers ---")
            # csm_pages = extractor.extract_csm_pages(pdf_file)
            # print(f"CSM pages found: {csm_pages}")

            # Method 2: Extract and save pages
            print("\n--- Method 2: Saving CSM page images ---")
            result = extractor.save_csm_pages(pdf_file, output_dir="extracted_csm_pages")
            print(f"Extraction result: {json.dumps(result, indent=2)}")

        except Exception as e:
            logger.error(f"Failed to extract CSM pages: {e}", exc_info=True)