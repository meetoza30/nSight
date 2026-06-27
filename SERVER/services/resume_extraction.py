import pdfplumber
import json
import requests
import re
import datetime
import time
from dateutil import parser
from utils.generatepdf import generate_resume_pdf
from dotenv import load_dotenv
import os

load_dotenv()


def calculate_total_experience(experiences):
    total_months = 0
    now = datetime.datetime.now()
    
    for exp in experiences:
        duration_str = exp.get("duration", "")
        if not duration_str:
            continue
            
        # Clean up formats like "Aug'25" or "Aug’25" to "Aug 2025"
        duration_str = re.sub(r'[\'’](\d{2})\b', r' 20\1', duration_str)
            
        parts = re.split(r'\s*(?:-|to|–)\s*', duration_str, flags=re.IGNORECASE)
        if len(parts) == 2:
            start_str, end_str = parts[0].strip(), parts[1].strip()
            if not start_str or not end_str:
                continue
                
            try:
                start_date = parser.parse(start_str, default=datetime.datetime(now.year, 1, 1))
                if end_str.lower() in ["present", "current", "till date", "today", "now"]:
                    end_date = now
                else:
                    end_date = parser.parse(end_str, default=datetime.datetime(now.year, 1, 1))
                
                months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                if months > 0:
                    total_months += months
            except Exception:
                pass
                
    return round(total_months / 12.0, 1)

# 1. TEXT EXTRACTION

def extract_text_preserving_layout(pdf_path):
    """Extracts text from PDF."""
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                raw_text = page.extract_text(x_tolerance=1)
                if raw_text:
                    full_text += raw_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""
    return full_text

def extract_pages_preserving_layout(pdf_path):
    """Extracts text from PDF page by page."""
    pages_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                raw_text = page.extract_text(x_tolerance=1)
                pages_text.append(raw_text or "")
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []
    return pages_text

# 2. LLM EXTRACTION VIA OPENROUT


def extract_resume_json(resume_text, model="deepseek/deepseek-v4-flash"):
    """Sends the resume text to OpenRouter and returns a parsed JSON dictionary."""
    
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    current_year = datetime.date.today().year
    current_month = datetime.date.today().strftime("%B")
    
    system_prompt = f"""You are a JSON-only data extraction API. Output raw valid JSON — no markdown, no explanation.

TODAY'S DATE: {current_month} {current_year}

CORE RULES:
1. VERBATIM ONLY — Every value must come directly from the resume. Never invent or infer. Empty fields = "" or [].
2. IGNORE all "Projects"/"Personal Projects"/"Academic Projects" sections entirely.
3. EXPERIENCE = professional work only (jobs, internships). Never include personal/academic projects.
4. COMPANY vs CLIENT vs PROJECT — "company" = employer. "client" = external org served (only if explicitly named, else ""). "project_name" = specific system/product built. Multiple projects under one company = multiple entries in that company's "projects" array. Do NOT split one company into multiple experience entries.
5. TECHNOLOGIES per project — Only extract if resume explicitly labels them (e.g. "Technologies:", "Tech Stack:"). Do NOT extract tech names from bullet point descriptions. If unlabeled, output [].
6. SKILLS — Extract ONLY from the dedicated Skills/Technical Skills section. Map categories to schema (Languages, Web Technologies, Tools, Technologies, Operating System). Keep names exactly as written.
7. TOTAL EXPERIENCE — If resume states years explicitly, use that. Otherwise compute from earliest start date to today ("Present" = today). Round to 1 decimal. Count only professional work.
8. DESCRIPTIONS — Copy all bullet points into "description" array. Do NOT summarize. Remove any leading bullet symbols (e.g., ◆, •, -, *, etc.).
9. ROLE RESPONSIBILITY — Extract only if explicitly stated as "role"/"role responsibility". Do not put job titles here.
10. JOBS WITHOUT PROJECTS — Treat entire role as single project with empty "project_name" and "client".
11. EDUCATION GRADE — Extract the grade (CGPA, GPA, percentage, or marks) for each education entry. Look for explicit mentions like "CGPA", "GPA", "Grade", "Score", "%", or patterns like "85%", "8.5/10", "3.8 GPA". If not found, output "".
OUTPUT SCHEMA:
{{"Name":"","Education":[{{"college":"","degree":"","graduation_year":"","grade":""}}],"Skills":{{"Languages":[],"Web Technologies":[],"Tools":[],"Technologies":[],"Operating System":[]}},"Achievements":[],"Experience":{{"total_experience_years":0.0,"experiences":[{{"company":"","designation":"","duration":"","location":"","projects":[{{"client":"","project_name":"","project_span":"","technologies":[],"description":[],"role_responsibility":""}}]}}]}}}}"""



    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries} to extract data...")
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                data=json.dumps({
                    "model": model, 
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Extract this resume and return ONLY a valid JSON object with no markdown:\n\n{resume_text}"}
                    ],
                    "temperature": 0.1
                })
            )
            data = response.json()
            print("resume extraction")
            print("Prompt Tokens:", data["usage"]["prompt_tokens"])
            print("Completion Tokens:", data["usage"]["completion_tokens"])
            print("Total Tokens:", data["usage"]["total_tokens"])
            response.raise_for_status()
            result_text = response.json()['choices'][0]['message']['content'].strip()
            print(result_text)
            
            # JSON Catcher
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                clean_json_string = result_text[start_idx:end_idx+1]
                try:
                    parsed_json = json.loads(clean_json_string)
                    
                    # Fast validation to ensure key properties look right
                    if not isinstance(parsed_json, dict) or "Experience" not in parsed_json:
                        print(f"Format validation failed on attempt {attempt + 1}. Retrying...")
                        continue
                        
                    # --- APPLY PYTHON EXPERIENCE CALCULATION ---
                    if "Experience" in parsed_json and "experiences" in parsed_json["Experience"]:
                        calculated_years = calculate_total_experience(parsed_json["Experience"]["experiences"])
                        if calculated_years > 0:
                            parsed_json["Experience"]["total_experience_years"] = calculated_years

                    # --- CLEAN BULLET POINTS ---
                    def clean_text(text):
                        if isinstance(text, str):
                            return re.sub(r'^[◆•\-*·\s]+', '', text).strip()
                        return text

                    if "Achievements" in parsed_json and isinstance(parsed_json["Achievements"], list):
                        parsed_json["Achievements"] = [clean_text(a) for a in parsed_json["Achievements"] if clean_text(a)]
                        
                    if "Experience" in parsed_json and isinstance(parsed_json["Experience"], dict) and "experiences" in parsed_json["Experience"]:
                        for exp in parsed_json["Experience"]["experiences"]:
                            if "projects" in exp and isinstance(exp["projects"], list):
                                for proj in exp["projects"]:
                                    if "description" in proj and isinstance(proj["description"], list):
                                        proj["description"] = [clean_text(d) for d in proj["description"] if clean_text(d)]

                    return parsed_json
                except json.JSONDecodeError as e:
                    print(f"JSON Parsing Error on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        print(f"Raw output that failed:\n{clean_json_string}")
                        return None
            else:
                print(f"Error: Could not find {{}} brackets on attempt {attempt + 1}.")
                if attempt == max_retries - 1:
                    print(f"Raw output:\n{result_text}")
                    return None
                
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                print(f"Extraction failed on attempt {attempt + 1}: {e}\nResponse: {e.response.text}")
            else:
                print(f"Extraction failed on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(2)
            
    return None

def extract_resume_json_chunked(pages_text, model="deepseek/deepseek-v4-flash"):
    """
    Processes the resume page-by-page. For each page, sends the page text and the
    accumulated JSON state to the LLM to update/merge.
    Saves intermediate states to SERVER/temp_states/ on the server.
    """
    import uuid
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    current_year = datetime.date.today().year
    current_month = datetime.date.today().strftime("%B")
    
    # 1. Initialize the empty/template state
    current_state = {
        "Name": "",
        "Education": [],
        "Skills": {
            "Languages": [],
            "Web Technologies": [],
            "Tools": [],
            "Technologies": [],
            "Operating System": []
        },
        "Achievements": [],
        "Experience": {
            "total_experience_years": 0.0,
            "experiences": []
        }
    }
    
    # 2. Setup storage directory
    # SERVER directory is the parent of the folder containing this file (services)
    server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_states_dir = os.path.join(server_dir, "temp_states")
    os.makedirs(temp_states_dir, exist_ok=True)
    
    process_uuid = str(uuid.uuid4())
    print(f"Starting chunked processing. Process UUID: {process_uuid}")
    
    total_pages = len(pages_text)
    
    schema_string = json.dumps({
        "Name": "",
        "Education": [{"college": "", "degree": "", "graduation_year": "", "grade": ""}],
        "Skills": {
            "Languages": [],
            "Web Technologies": [],
            "Tools": [],
            "Technologies": [],
            "Operating System": []
        },
        "Achievements": [],
        "Experience": {
            "total_experience_years": 0.0,
            "experiences": [{
                "company": "",
                "designation": "",
                "duration": "",
                "location": "",
                "projects": [{
                    "client": "",
                    "project_name": "",
                    "project_span": "",
                    "technologies": [],
                    "description": [],
                    "role_responsibility": ""
                }]
            }]
        }
    })

    # Filter out empty pages, but keep track of indices for logging
    non_empty_pages = [(idx + 1, text) for idx, text in enumerate(pages_text) if text.strip()]
    if not non_empty_pages:
        return current_state
        
    for seq_num, (page_num, page_text) in enumerate(non_empty_pages):
        print(f"Processing page {page_num}/{total_pages} (Sequence {seq_num + 1}/{len(non_empty_pages)})...")
        
        system_prompt = f"""You are a JSON-only data extraction API. Output raw valid JSON — no markdown, no explanation.

TODAY'S DATE: {current_month} {current_year}

You are processing a multi-page resume page-by-page.
Currently processing Page {page_num} of {total_pages}.

You are given:
1. The accumulated JSON state from previous pages.
2. The raw text of the current page.

Your task is to extract information from the current page and update/merge it into the existing accumulated JSON state.

CORE RULES FOR EXTRACTION & MERGING:
1. VERBATIM ONLY — Every new value must come directly from the current page text. Never invent or infer.
2. NAME — If "Name" is empty in the accumulated JSON state, extract the candidate's name if it appears on this page. Otherwise, preserve the existing "Name".
3. EDUCATION — If new education entries are found, append them to the "Education" list. Ensure no duplicate degrees/colleges are added.
4. SKILLS — Extract skills ONLY from dedicated skills sections if present on this page. Merge them into the existing "Skills" categories (Languages, Web Technologies, Tools, Technologies, Operating System) without duplicates. Keep names exactly as written.
5. ACHIEVEMENTS — Append any new achievements found to the "Achievements" list verbatim.
6. EXPERIENCE:
   - Identify professional work experiences (jobs, internships) on this page.
   - If an experience belongs to a company already present in the accumulated JSON's "experiences" list (match by company name), merge the new projects/descriptions into that existing company's entry rather than creating a new company entry.
   - If it's a new company, append a new experience entry to the list.
   - Ensure you do NOT delete or lose any existing companies or projects from the accumulated JSON state. All previous experience and projects MUST be preserved.
   - Copy all bullet points into the "description" array. Do NOT summarize. Remove leading bullet symbols (e.g. ◆, •, -, *, etc.).
   - Treat roles without explicit projects as a single project with empty "project_name" and "client".
7. TOTAL EXPERIENCE — Set "total_experience_years" to 0.0 for now. It will be computed at the end in Python.
8. IGNORE all "Projects"/"Personal Projects"/"Academic Projects" sections. Extract professional experience only.
9. OUTPUT FORMAT — Output ONLY the final updated JSON matching the schema below. Keep all keys and structure intact.

JSON SCHEMA:
{schema_string}
"""

        max_retries = 3
        success = False
        parsed_json = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    data=json.dumps({
                        "model": model,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": f"Accumulated JSON State:\n{json.dumps(current_state, ensure_ascii=False)}\n\nCurrent Page Text:\n{page_text}"
                            }
                        ],
                        "temperature": 0.1
                    })
                )
                response.raise_for_status()
                data = response.json()
                result_text = data['choices'][0]['message']['content'].strip()
                
                # JSON Catcher
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    clean_json_string = result_text[start_idx:end_idx+1]
                    parsed_json = json.loads(clean_json_string)
                    
                    if isinstance(parsed_json, dict) and "Experience" in parsed_json:
                        success = True
                        break
                    else:
                        print(f"Format validation failed on page {page_num}, attempt {attempt + 1}. Retrying...")
                else:
                    print(f"Could not find brackets on page {page_num}, attempt {attempt + 1}.")
            except Exception as e:
                print(f"Error on page {page_num}, attempt {attempt + 1}: {e}")
                time.sleep(2)
                
        if success and parsed_json:
            current_state = parsed_json
            # Save intermediate state to the server
            page_file_path = os.path.join(temp_states_dir, f"resume_{process_uuid}_page_{page_num}.json")
            current_file_path = os.path.join(temp_states_dir, f"resume_{process_uuid}_current.json")
            
            try:
                with open(page_file_path, "w", encoding="utf-8") as f:
                    json.dump(current_state, f, indent=4, ensure_ascii=False)
                with open(current_file_path, "w", encoding="utf-8") as f:
                    json.dump(current_state, f, indent=4, ensure_ascii=False)
                print(f"Saved state for page {page_num} to {page_file_path}")
            except Exception as se:
                print(f"Failed to save intermediate files: {se}")
        else:
            print(f"Warning: Failed to extract page {page_num} successfully. Continuing with existing state.")

    # 3. Post-processing calculations & cleaning (done at the end)
    if "Experience" in current_state and "experiences" in current_state["Experience"]:
        calculated_years = calculate_total_experience(current_state["Experience"]["experiences"])
        if calculated_years > 0:
            current_state["Experience"]["total_experience_years"] = calculated_years

    # Clean bullet points in Achievements and Experience
    def clean_text(text):
        if isinstance(text, str):
            return re.sub(r'^[◆•\-*·\s]+', '', text).strip()
        return text

    if "Achievements" in current_state and isinstance(current_state["Achievements"], list):
        current_state["Achievements"] = [clean_text(a) for a in current_state["Achievements"] if clean_text(a)]
        
    if "Experience" in current_state and isinstance(current_state["Experience"], dict) and "experiences" in current_state["Experience"]:
        for exp in current_state["Experience"]["experiences"]:
            if "projects" in exp and isinstance(exp["projects"], list):
                for proj in exp["projects"]:
                    if "description" in proj and isinstance(proj["description"], list):
                        proj["description"] = [clean_text(d) for d in proj["description"] if clean_text(d)]

    # Save the final JSON state to the server
    final_file_path = os.path.join(temp_states_dir, f"resume_{process_uuid}_final.json")
    try:
        with open(final_file_path, "w", encoding="utf-8") as f:
            json.dump(current_state, f, indent=4, ensure_ascii=False)
        print(f"Saved final state to {final_file_path}")
    except Exception as se:
        print(f"Failed to save final state file: {se}")

    return current_state

# 3. MAIN RUNNER

def process_resume(file_path):
    print(f"Reading file: {file_path}...")
    
    pages_text = extract_pages_preserving_layout(file_path)
    if not pages_text or all(not p for p in pages_text):
        print("Empty or unreadable PDF")
        return

    print("Extracting data via LLM (chunked)...")
    extracted_data = extract_resume_json_chunked(pages_text)
    
    if extracted_data:
        print("\n--- EXTRACTION RESULT ---")
        print(json.dumps(extracted_data, indent=4, ensure_ascii=False))
        
        # Generate the PDF (Uncomment when ready)
        # candidate_name = extracted_data.get("Name", "Unknown")
        # pdf_name = candidate_name.replace(" ", "_") + "_NcircleCV.pdf"
        # generate_resume_pdf(extracted_data, pdf_name)
        # print(f"Generated PDF: {pdf_name}")

if __name__ == "__main__":
    resume_paths = [
        # "./Resumes/Priyanshi.pdf",
        "./Resumes/Akash ShahakarQA26.pdf",
        # "./Resumes/maruf.pdf",
        # "./Resumes/Anjali_Verma_Resume.pdf",
        # "./Resumes/SagarManojNikam_DS.pdf",
        # "./Resumes/MeetOza_Resume.pdf",
    ]

    for pdf_path in resume_paths:
        process_resume(pdf_path)