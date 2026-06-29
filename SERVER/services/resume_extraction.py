import pdfplumber
import json
import requests
import re
import datetime
import time
from dateutil import parser
# from utils.generatepdf import generate_resume_pdf
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

# 2. LLM EXTRACTION VIA OPENROUTER

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
            # print(result_text)
            
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
                        print("calculated_years : ", calculated_years)
                        # print()
                        # if calculated_years > 0:
                        #     parsed_json["Experience"]["total_experience_years"] = calculated_years

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

# 3. MAIN RUNNER

def process_resume(file_path):
    print(f"Reading file: {file_path}...")
    
    full_text = extract_text_preserving_layout(file_path)
    if not full_text:
        print("Empty or unreadable PDF")
        return
    print("text", full_text)
    print("Extracting data via LLM...")
    extracted_data = extract_resume_json(full_text)
    
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
        "./Resumes/Aman_Babu_s_Resume__Copy_ (1).pdf",
        # "./Resumes/Akash ShahakarQA26.pdf",
        # "./Resumes/maruf.pdf",
        # "./Resumes/Anjali_Verma_Resume.pdf",
        # "./Resumes/SagarManojNikam_DS.pdf",
        # "./Resumes/MeetOza_Resume.pdf",
    ]

    for pdf_path in resume_paths:
        process_resume(pdf_path)