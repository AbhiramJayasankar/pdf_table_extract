import os
import json
from contextgem import Document, DocumentLLM, Image, image_to_base64
from dotenv import load_dotenv

# Assuming the schema is in a file named `planned_machinery_survey_schema.py`
# in a directory called `schema`.
# If your structure is different, you may need to adjust the import.
from schema.planned_machinery_survey_schema import planned_machinery_survey_concept

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
        doc_image = Image(mime_type="image/jpeg", base64_data=image_to_base64(image_path))
        doc = Document(images=[doc_image])
        doc.add_concepts([planned_machinery_survey_concept])

        # --- 4. Extract concepts from the document ---
        extracted_concepts = vlm.extract_concepts_from_document(doc)

        # --- 5. Validate and return the extracted data ---
        if not extracted_concepts or not extracted_concepts[0].extracted_items:
            print(f"  [INFO] No data was extracted for {os.path.basename(image_path)}.")
            return None

        # Retrieve the structured data from the first extracted item
        report_data = extracted_concepts[0].extracted_items[0].value
        print(f"  -> Successfully extracted data for {os.path.basename(image_path)}.")

        return report_data

    except Exception as e:
        print(f"  [ERROR] An error occurred while processing {image_path}. Reason: {e}")
        return None


def main():
    """
    Example usage of the extract_json_from_image function.
    """
    # --- Configuration ---
    # IMPORTANT: Replace this with the actual path to an image you want to test.
    # For this example, we assume there's an image in 'images/LEADER_1/page_7.png'

    test_image_path = os.path.join("images", "ACE-ETERNITY", "CSM_PAGE_007.png")

    if not os.path.isfile(test_image_path):
        print(f"Test image not found: {test_image_path}")
        print("Please update the 'test_image_path' variable in the main() function.")
        return

    # --- Call the extraction function ---
    extracted_data = extract_json_from_image(test_image_path)

    # --- Print the result ---
    if extracted_data:
        print("\n--- Extracted JSON Data ---")
        # Pretty-print the JSON data
        print(json.dumps(extracted_data, indent=4))
        print("---------------------------\n")
    else:
        print("\n--- No data was returned. ---\n")


if __name__ == "__main__":
    # This block will run when the script is executed directly
    main()
