import os
import json
from contextgem import Document, DocumentLLM, Image, image_to_base64
from dotenv import load_dotenv
from schema.planned_machinery_survey_schema import planned_machinery_survey_concept

# Load environment variables from a .env file
load_dotenv()

def extract_data_from_image(image_path, output_base_dir, vlm_model, concept):
    """
    Processes a single image file, extracts structured data using a VLM,
    and saves the result as a JSON file, maintaining the source folder structure.

    Args:
        image_path (str): The full path to the image file.
        output_base_dir (str): The root directory where JSON files will be saved.
        vlm_model (DocumentLLM): An initialized DocumentLLM instance.
        concept (dict): The concept schema for data extraction.
    """
    print(f"Processing: {image_path}")
    try:
        # --- 1. Prepare the document for the VLM ---
        doc_image = Image(mime_type="image/jpeg", base64_data=image_to_base64(image_path))
        doc = Document(images=[doc_image])
        doc.add_concepts([concept])

        # --- 2. Extract concepts from the document ---
        extracted_concepts = vlm_model.extract_concepts_from_document(doc)

        # --- 3. Validate and retrieve the extracted data ---
        if not extracted_concepts or not extracted_concepts[0].extracted_items:
            print(f"  [WARNING] No data was extracted for {os.path.basename(image_path)}.")
            return

        report_data = extracted_concepts[0].extracted_items[0].value

        # --- 4. Define the output path ---
        # Get the relative path from the input root ('images') to the image's directory
        # e.g., for "images/LEADER_1/page_7.png", this will be "LEADER_1"
        relative_path = os.path.relpath(os.path.dirname(image_path), "images")
        
        # Get the original filename without its extension
        input_filename_without_ext = os.path.splitext(os.path.basename(image_path))[0]
        
        # Create the new JSON filename
        json_filename = f"{input_filename_without_ext}.json"
        
        # Create the full output directory path (e.g., "extracted/LEADER_1")
        output_dir_full_path = os.path.join(output_base_dir, relative_path)
        
        # Ensure the output directory exists
        os.makedirs(output_dir_full_path, exist_ok=True)
        
        # Create the final, full path for the output JSON file
        output_filepath = os.path.join(output_dir_full_path, json_filename)

        # --- 5. Save the data to the JSON file ---
        with open(output_filepath, 'w') as json_file:
            json.dump(report_data, json_file, indent=4)
            
        print(f"  -> Successfully saved to {output_filepath}")

    except Exception as e:
        print(f"  [ERROR] Failed to process {image_path}. Reason: {e}")


def main():
    """
    Main function to orchestrate the extraction process.
    It initializes the VLM and then iterates through all images in the
    specified input directory.
    """
    # --- Configuration ---
    input_root_dir = "images"
    output_root_dir = "extracted"
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        print("Error: GOOGLE_API_KEY not found in environment variables.")
        return
        
    if not os.path.isdir(input_root_dir):
        print(f"Error: Input directory '{input_root_dir}' not found.")
        return

    # --- Initialize the VLM (do this once to be efficient) ---
    print("Initializing Vision Language Model...")
    vlm = DocumentLLM(
        model="gemini/gemini-2.0-flash",
        api_key=google_api_key,
        role="extractor_vision",
    )
    print("Initialization complete.")

    # --- Walk through the directory structure ---
    print(f"\nStarting extraction from '{input_root_dir}'...")
    for dirpath, _, filenames in os.walk(input_root_dir):
        for filename in filenames:
            # Check for common image file extensions
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                full_image_path = os.path.join(dirpath, filename)
                # Call the extraction function for each image
                extract_data_from_image(
                    image_path=full_image_path,
                    output_base_dir=output_root_dir,
                    vlm_model=vlm,
                    concept=planned_machinery_survey_concept
                )
    
    print("\nExtraction process finished.")


if __name__ == "__main__":
    main()
