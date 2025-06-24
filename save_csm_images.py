from csm_module.code import CSMPageExtractor
import os
import json
from dotenv import load_dotenv
load_dotenv()

def extract_csm_images(pdf_file: str, output_dir: str):
    """
    Extracts CSM page images from the given PDF and saves them to the specified output directory.

    Args:
        pdf_file (str): Path to the PDF file.
        output_dir (str): Directory to save extracted images.
    """
    api_key = os.environ.get("GOOGLE_API_KEY_2")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY_2 is not set in the environment variables.")

    extractor = CSMPageExtractor(api_key=api_key)

    if not os.path.exists(pdf_file):
        print(f"Error: The PDF file was not found at: {pdf_file}")
        print("Please ensure the file exists and the path is correct.")
        return

    try:
        print(f"\n--- Processing {pdf_file} ---")
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        print(f"--- Saving CSM page images to {output_dir} ---")
        result = extractor.save_csm_pages(pdf_file, output_dir=output_dir)
        print(f"Extraction result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"An error occurred during CSM page extraction for {pdf_file}: {e}")

# Main execution block
if __name__ == "__main__":
    # Define the input directory containing PDF files.
    input_pdf_dir = "downloaded_pdfs"
    # Define the base output directory for extracted images.
    base_output_dir = "images"

    # Check if the input directory exists.
    if not os.path.isdir(input_pdf_dir):
        print(f"Error: Input directory not found at '{input_pdf_dir}'")
    else:
        # Walk through the input directory to find all PDF files.
        for root, _, files in os.walk(input_pdf_dir):
            for file in files:
                if file.lower().endswith(".pdf"):
                    # Construct the full path to the PDF file.
                    pdf_path = os.path.join(root, file)

                    # Determine the relative path of the PDF from the input directory.
                    relative_path = os.path.relpath(pdf_path, input_pdf_dir)

                    # Get the filename without the extension.
                    pdf_filename_without_ext = os.path.splitext(os.path.basename(relative_path))[0]
                    
                    # Get the directory part of the relative path.
                    pdf_dir_part = os.path.dirname(relative_path)

                    # Construct the final output directory for the images of the current PDF.
                    # This will be: base_output_dir / [subdirectory_structure] / [pdf_filename]
                    output_dir_for_pdf = os.path.join(base_output_dir, pdf_dir_part, pdf_filename_without_ext)
                    
                    # Call the extraction function for the current PDF.
                    extract_csm_images(
                        pdf_file=pdf_path,
                        output_dir=output_dir_for_pdf
                    )
        print("\n--- All PDF files processed. ---")