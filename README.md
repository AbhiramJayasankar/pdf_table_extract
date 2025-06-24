# PDF Table Extraction for Maritime Surveys

**GitHub Repository:**  
[https://github.com/AbhiramJayasankar/pdf_table_extract](https://github.com/AbhiramJayasankar/pdf_table_extract)

This project automates extracting structured data from PDF documents, focusing on "Planned Machinery Survey" sections within maritime survey reports. It uses a multi-step pipeline powered by Google's Gemini AI models to identify relevant pages, extract them as images, and parse tabular data into a structured JSON format.

---

## Table of Contents

- [PDF Table Extraction for Maritime Surveys](#pdf-table-extraction-for-maritime-surveys)
  - [Table of Contents](#table-of-contents)
  - [Project Workflow](#project-workflow)
  - [Directory Structure](#directory-structure)
  - [Prerequisites](#prerequisites)
  - [Setup and Configuration](#setup-and-configuration)
  - [How to Run](#how-to-run)
  - [Script Descriptions](#script-descriptions)
  - [Customization](#customization)

---

## Project Workflow

The data extraction process is broken down into three main stages:

1. **PDF Downloading:**  
   Start with an Excel file (`NK.xlsx`) containing links to PDF survey reports. The script downloads each PDF.

2. **CSM Page Identification & Extraction:**  
   Each PDF is processed to identify pages relevant to the "Continuous Machinery Survey" (CSM) using a vision-capable AI model. These pages are saved as PNG images.

3. **Structured Data Extraction:**  
   The PNG images are passed to a Vision Language Model (VLM), which extracts tabular data into clean, organized JSON files.

**High-level flow diagram:**

```
[NK.xlsx] 
   ↓
download_pdfs.py 
   ↓
[PDF Files] 
   ↓
save_csm_images.py 
   ↓
[PNG Images] 
   ↓
extract.py 
   ↓
[JSON Data]
```

---

## Directory Structure

- **csm_module/**: Module for identifying and extracting CSM pages from PDFs.
- **downloaded_pdfs/**: Output directory for downloaded PDF files. *(Git-ignored)*
- **images/**: Output directory for extracted PNG page images. *(Git-ignored)*
- **extracted/**: Output directory for final JSON data. *(Git-ignored)*
- **schema/**: Defines the JSON schema for data extraction.
- **.env**: Environment variables file for API keys. *(Must be created)*
- **download_pdfs.py**: Script to download PDFs from an Excel list.
- **extract.py**: Script to extract structured data from images.
- **NK.xlsx**: Input Excel file with links to PDFs. *(Must be provided)*
- **requirements.txt**: Lists all Python dependencies. *(Should be created)*
- **save_csm_images.py**: Script to save the identified CSM pages as images.

---

## Prerequisites

Ensure you have the following installed:

- **Python 3.8+**
- **Pip** (Python package installer)
- **Poppler** (for PDF handling):
  - **macOS:** `brew install poppler`
  - **Windows:** Download from the official website and add the `bin/` directory to your PATH.
  - **Linux (Debian/Ubuntu):** `sudo apt-get install poppler-utils`

---

## Setup and Configuration

1. **Clone the Repository:**
    ```sh
    git clone https://github.com/AbhiramJayasankar/pdf_table_extract.git
    cd pdf_table_extract
    ```

2. **Create a `requirements.txt` File:**  
   Add the following dependencies:
    ```
    pandas
    openpyxl
    requests
    pdf2image
    google-generativeai
    Pillow
    python-dotenv
    contextgem
    ```

3. **Install Dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4. **Set Up Environment Variables:**  
   Create a `.env` file in the root directory:
    ```
    GOOGLE_API_KEY_2="your_google_api_key_here"
    ```

5. **Prepare Input File:**  
   Place your Excel file named `NK.xlsx` in the root directory. It must contain two columns: `vesselName` and `linkForSyia`.

---

## How to Run

Execute the scripts sequentially after setup:

**Step 1: Download the PDFs**
```sh
python download_pdfs.py
```
This populates the `downloaded_pdfs/` directory.

**Step 2: Identify and Save CSM Pages as Images**
```sh
python save_csm_images.py
```
This saves relevant pages as PNGs in the `images/` directory.

**Step 3: Extract Structured Data to JSON**
```sh
python extract.py
```
This saves the extracted data as JSON files in the `extracted/` directory.

---

## Script Descriptions

- **download_pdfs.py:** Reads `NK.xlsx`, downloads PDFs from URLs, and saves them using sanitized vessel names.
- **csm_module/code.py:** The core AI module. `CSMPageExtractor` uses the Gemini model to identify pages belonging to the 'Planned Machinery Survey' section.
- **save_csm_images.py:** Uses `CSMPageExtractor` to process all downloaded PDFs and save relevant pages as images.
- **schema/bao_min.py:** Defines the target data structure for the VLM, instructing it how to parse tables and format the JSON output.
- **extract.py:** Sends images and schema to the Gemini VLM and saves the structured output as JSON.

---

## Customization

- **Different Data Structures:**  
  Modify the schema in `schema/bao_min.py` to change the extracted fields and JSON structure.
- **Different Document Types:**  
  Update the prompt in the `identify_csm_pages` method in `csm_module/code.py` to look for different keywords or page titles.
- **Different Input Sources:**  
  Modify `download_pdfs.py` to read from a different source like a CSV file, database, or API.
