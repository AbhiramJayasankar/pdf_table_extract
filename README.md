````markdown
# PDF Table Extraction for Maritime Surveys

**GitHub Repository:** [https://github.com/AbhiramJayasankar/pdf_table_extract](https://github.com/AbhiramJayasankar/pdf_table_extract)

This project provides a complete, automated pipeline for extracting structured data from PDF documents, with a specific focus on the "Planned Machinery Survey" sections found in maritime survey reports. The pipeline leverages Google's Gemini AI models to intelligently identify relevant pages, convert them to images, and parse complex tables into a clean, structured JSON format.

---

## Table of Contents

- [Project Workflow](#project-workflow)
- [Directory Structure](#directory-structure)
- [Prerequisites](#prerequisites)
- [Setup and Configuration](#setup-and-configuration)
- [How to Run the Pipeline](#how-to-run-the-pipeline)
- [Script and Module Descriptions](#script-and-module-descriptions)
- [Customization](#customization)

---

## Project Workflow

The data extraction process is orchestrated by a single main pipeline script that automates the following stages:

1.  **Download PDF from URL:** The pipeline begins with a public URL to a PDF file (e.g., hosted on an S3 bucket). The script downloads the PDF to a local temporary directory.

2.  **Identify and Extract CSM Pages:** The downloaded PDF is processed by the `CSMPageExtractor` class, which uses a multimodal AI model (Gemini) to identify all pages belonging to the "Continuous Machinery Survey" (CSM) section. These specific pages are then extracted and saved as high-resolution PNG images.

3.  **Extract Structured Data from Images:** Each extracted image is passed to a Vision Language Model (VLM). Using a predefined JSON schema, the model accurately extracts the tabular data from the image, converting the rows and columns into structured JSON objects.

4.  **Aggregate and Save Final JSON:** The JSON data from all processed images is aggregated into a single list and saved to a final JSON file, named after the original PDF.

**High-Level Flow Diagram:**

```
[PDF URL]
    ↓
s3_link_to_json_pipeline.py
    ├─► utils/download_from_s3_util.py  (Downloads PDF)
    ├─► utils/csm_page_extractor.py     (Identifies and saves CSM pages as images)
    └─► utils/extract_func.py           (Extracts JSON from each image)
    ↓
[Final JSON Output]
```

---

## Directory Structure

Here is the accurate structure of the project:

-   **final_json_output/**: Default output directory for the final aggregated JSON files.
-   **schema/**: Contains the data structure definitions for the VLM.
    -   `planned_machinery_survey_schema.py`: Defines the target JSON schema for extracting machinery survey data.
-   **utils/**: Core utility modules that power the pipeline.
    -   `csm_page_extractor.py`: Class to find and extract CSM pages from PDFs.
    -   `download_from_s3_util.py`: Helper function to download files from URLs.
    -   `extract_func.py`: Function to extract structured data from a single image.
    -   `save_csm_images.py`: Script to save identified CSM pages as images (can also be run standalone).
-   **.env**: For storing environment variables like your API key. *(Must be created by the user)*
-   **.gitignore**: Specifies files and directories to be ignored by Git.
-   **requirements.txt**: A list of all required Python packages for the project.
-   **s3_link_to_json_pipeline.py**: The main script that orchestrates the entire workflow from URL to final JSON.

---

## Prerequisites

Before you begin, ensure you have the following installed:

-   **Python 3.8+**
-   **Pip** (Python's package installer)
-   **Poppler**: A PDF rendering library required for `pdf2image`.
    -   **macOS (via Homebrew):** `brew install poppler`
    -   **Windows:** Download the latest version, extract it, and add the `bin/` directory to your system's PATH.
    -   **Linux (Debian/Ubuntu):** `sudo apt-get update && sudo apt-get install -y poppler-utils`

---

## Setup and Configuration

1.  **Clone the Repository:**
    ```sh
    git clone [https://github.com/AbhiramJayasankar/pdf_table_extract.git](https://github.com/AbhiramJayasankar/pdf_table_extract.git)
    cd pdf_table_extract
    ```

2.  **Install Dependencies:**
    Install all the required packages using the `requirements.txt` file.
    ```sh
    pip install -r requirements.txt
    ```

3.  **Set Up Environment Variables:**
    Create a file named `.env` in the root directory of the project and add your Google AI API key:
    ```
    GOOGLE_API_KEY="your_google_api_key_here"
    ```

---

## How to Run the Pipeline

The entire process is managed by the `s3_link_to_json_pipeline.py` script.

1.  **Configure the Script:**
    Open `s3_link_to_json_pipeline.py` and modify the variables in the `if __name__ == '__main__':` block:
    -   `url_to_process`: Set this to the public URL of the PDF you want to process.
    -   `output_directory`: (Optional) Change the directory where the final JSON file will be saved. The default is `final_json_output`.

2.  **Execute the Pipeline:**
    Run the script from your terminal:
    ```sh
    python s3_link_to_json_pipeline.py
    ```

The script will log its progress in the console, from downloading the PDF to saving the final JSON file.

---

## Script and Module Descriptions

-   **s3_link_to_json_pipeline.py**: This is the main entry point for the project. It orchestrates the entire workflow by calling the necessary utility functions in sequence: downloading the source PDF, extracting the relevant pages as images, processing each image to get structured data, and saving the final result.

-   **utils/download_from_s3_util.py**: A utility function, `download_files_from_urls`, that takes a list of URLs and an output directory, and robustly downloads the files. It handles potential request errors.

-   **utils/csm_page_extractor.py**: Contains the `CSMPageExtractor` class, the core component for page identification. It converts a PDF to images, adds page numbers for clarity, and then uses the Gemini vision model to identify and return the page numbers of the "Planned Machinery Survey" section.

-   **utils/extract_func.py**: Provides the `extract_json_from_image` function, which takes a single image path and uses the Gemini VLM along with a predefined schema to extract structured data into a Python dictionary.

-   **schema/planned_machinery_survey_schema.py**: Defines the exact data structure (`JsonObjectConcept`) that the VLM should follow when extracting information from the images. This ensures the output is consistent, clean, and well-organized.

---

## Customization

This pipeline is highly customizable for different document types and data structures.

-   **Different Data Structures:** To extract different fields or change the final JSON organization, simply modify the `structure` dictionary within the `planned_machinery_survey_concept` in `schema/planned_machinery_survey_schema.py`.

-   **Different Document Types:** If you need to identify different sections in your PDFs (e.g., "Safety Certificates" instead of "Planned Machinery Survey"), update the prompt in the `identify_csm_pages` method within the `utils/csm_page_extractor.py` file to include the new keywords and titles to look for.

-   **Different Input Sources:** The main pipeline currently takes a single URL. You can easily modify the `if __name__ == '__main__':` block in `s3_link_to_json_pipeline.py` to read from a list of URLs, a CSV file, a database, or any other source.
````