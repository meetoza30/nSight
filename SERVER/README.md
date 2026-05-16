# nCircle Resume Parser API

This project provides a FastAPI backend for parsing resume PDFs using an LLM (via OpenRouter) and generating a standardized "nCircle CV" PDF. 

## 🛠 Required Libraries breakdown

The libraries used in this project are defined in `requirements.txt`:

### Used in `main.py` (API Server)
* **`fastapi`**: The web framework for building the API endpoints.
* **`uvicorn`**: The ASGI server used to run the FastAPI app.
* **`python-multipart`**: Enables FastAPI to parse uploaded files (`UploadFile`).

### Used in Imported Files
* **`resume_extraction.py` (Data Extraction):**
  * **`pdfplumber`**: For extracting raw text from uploaded resume PDFs while somewhat preserving layout/content ordering.
  * **`requests`**: For making HTTP POST requests to the OpenRouter API for LLM data extraction.
  * **`python-dateutil`**: For dynamically parsing and calculating total work experience dates (e.g., parsing "Aug '25", "Present").
  * **`python-dotenv`**: For loading the `OPENROUTER_API_KEY` from a `.env` file securely.
* **`generatepdf.py` (PDF Generation):**
  * **`reportlab`**: For constructing the nCircle branded PDF programmatically using standard formatting, shapes, colors, and layouts.

---

## 🚀 Installation & Setup Guide for Contributors

Follow these steps to set up this project locally for development.

### Prerequisites
* Python 3.8 or higher installed on your system.

### 1. Clone the repository
Clone the repository to your local machine (or just obtain the source code folder).
```bash
# If using git:
git clone <repository-url>
cd <repository-directory>
```

### 2. Set up a Virtual Environment
It's highly recommended to use a virtual environment to manage dependencies.
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install all the required third-party libraries:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
1. Create a file named `.env` in the root directory.
2. Add your OpenRouter API Key to the file:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 5. Add Static Assets
Ensure the nCircle logo (`ncircle_tech_logo.jpg`) is present in the root directory, as it's required for placing the branding logo onto the generated PDFs. A `static` folder is also mounted by `main.py` to serve a frontend GUI if one exists.

### 6. Run the Application
You can start the FastAPI server using Python:
```bash
python main.py
```
Alternatively, you can run it via Uvicorn with auto-reload enabled for development:
```bash
uvicorn main:app --reload
```

### 7. Access the Application
Once running, you can access:
* **Swagger UI (Interactive API Docs):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Local Web Interface:** [http://localhost:8000](http://localhost:8000) (if `static/index.html` exists)

---

## 🧑‍💻 Architecture Overview

1. **`main.py`**: The entry point. Handles incoming HTTP requests, serves the frontend interface, routes uploaded resumes to `resume_extraction.py`, and maps the extracted JSON to `generatepdf.py`.
2. **`resume_extraction.py`**: Reads the PDF buffer with `pdfplumber`, creates a strict system prompt, calls the LLM via `requests` to get structured JSON, and calculates total experience dates utilizing `dateutil`.
3. **`generatepdf.py`**: Takes the structured JSON data and uses `reportlab` to map the results onto a branded A4 PDF document that is returned to the user.
