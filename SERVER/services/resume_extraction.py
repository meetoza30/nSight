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

# 2. LLM EXTRACTION VIA OPENROUTER

def extract_resume_json(resume_text):
    """Sends the resume text to OpenRouter and returns a parsed JSON dictionary."""
    
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    current_year = datetime.date.today().year
    current_month = datetime.date.today().strftime("%B")
    
    system_prompt = """
    You are a backend data extraction API. You ONLY output raw, valid JSON. No markdown, no explanation, no preamble.

    RULE 1 — COPY FROM RESUME ONLY. NEVER INVENT OR INFER.
    Every single value in the output JSON must come verbatim (or as a direct, minimal paraphrase) from the resume text.
    - You should completely ignore the resume's 'Projects' or 'Personal Projects' section. 
    - Do NOT add skills, technologies, tools, or descriptions that are not explicitly written in the resume.
    - Do NOT infer technologies from project descriptions or bullet points unless the resume explicitly lists them as technologies used.
    - If a field has no data in the resume, output an empty string "" or empty array [].

    RULE 2 — EXPERIENCE: CLIENT vs COMPANY vs PROJECT
    Read this carefully. These are three DIFFERENT things:

    "company"      = The main employer who hired/paid the candidate.
                    Examples: "Orbit Analytics", "HCL", "IT-Networkz", "nCircle Tech Pvt Ltd"

    "client"       = An external customer, bank, or business that the company served.
                    Examples: "Barclays", "FinGuard Banking", "ShopTrendz E-Commerce", "ABC Corp"
                    A client is ONLY present if the resume explicitly names one under that role's work.
                    If no client is mentioned for a project, set "client": "".

    "project_name" = The specific application, system, or product built.
                    Examples: "AI Personalization Engine", "Inventory Management System"

    HOW TO IDENTIFY A CLIENT:
    - The resume may write it as: "Client: Barclays", "Client - ABC Corp", or inline like
        "Delivered support to Barclays(Banking)" or "ShopTrendz E-Commerce - AI Personalization Engine".
    - Any named external organization that is NOT the candidate's direct employer is a client.
    - Do NOT leave the client field blank if a client name is written anywhere under that company's work.

    HOW TO HANDLE MULTIPLE PROJECTS UNDER ONE COMPANY:
    - If the resume lists several clients or projects under one company/employer, create one entry per project
        inside the "projects" array of that company.
    - Do NOT split one company into multiple experience entries just because it has multiple projects.

    RULE 3 — NO PERSONAL PROJECTS IN EXPERIENCE
    The "Experience" section is strictly ONLY for PROFESSIONAL WORK EXPERIENCE (e.g., full-time, part-time jobs, and internships at a company).
    - Do NOT include academic projects, personal projects, or side projects under the "Experience" section.
    - If a section in the resume is titled "Projects", "Academic Projects", or "Personal Projects", you MUST completely ignore all content within that entire section. Do NOT try to extract them.
    - NEVER reuse or duplicate a company name (e.g., from a real job) just to attach a personal project to it.
    - Only include a project under a company if the resume explicitly indicates it was built AS PART OF your employment AT that specific company.
    - Every entry in the "experiences" array MUST be a distinct, real job with a valid "company" name. Do NOT create empty/fake experiences.

    RULE 4 — TECHNOLOGIES IN EXPERIENCE: EXPLICIT ONLY
    The "technologies" array inside each project MUST be empty [] UNLESS the resume explicitly
    states a technology list for that project or role. Examples of explicit statements:
    - "Technologies: React, Node.js, MongoDB"
    - "Tech Stack: Python, Kafka"
    - "Technologies: PyTorch, LangChain"

    DO NOT extract technology names from bullet point descriptions like:
    - "Utilized Selenium for test automation" → do NOT add "Selenium" to technologies
    - "Delivered support using ServiceNow" → do NOT add "ServiceNow" to technologies
    - "Building frontend features for an AI/ML application" → do NOT add anything

    If the technology list is not explicitly labeled/separated in the resume for a specific experience,
    output "technologies": [].

    RULE 5 — SKILLS SECTION: USE RESUME SECTION ONLY
    Extract skills ONLY from the resume's dedicated Skills / Technical Skills section.
    - Do NOT pull skill names from the experience descriptions, bullet points, or project descriptions.
    - Place each item in the correct category as labeled in the resume (Languages, Web Technologies, Tools, etc.).
    - If the resume uses a different category name (e.g. "Frameworks", "Libraries", "Databases"), map it to the
    closest matching category in the schema, or put it in "Technologies".
    - Keep the skill names exactly as written in the resume (e.g. "Core Java" not "Java", "C/C++" not "C++").

    RULE 6 — TOTAL EXPERIENCE CALCULATION
    Use this priority order:
    1. If the resume's summary/profile explicitly states a number (e.g. "4 years of experience",
        "7+ years"), use that number as total_experience_years.
    2. Otherwise, find the EARLIEST start date among all experience entries, compute the
        difference to today's date (treat "Present" as today), and round to 1 decimal place.
    3. Count only professional work experience (full-time, part-time, internship).
        Do NOT count education years or personal projects.

    RULE 7 — EXPERIENCE DESCRIPTION
    If the 'role' or 'role responsibility' is explicitly mentioned in the under any experience, extract it and put it in the 'role_responsibility' field and dont put the role like frontend developer or full stack developer in the 'role_responsibility' field.
    Extract all bullet points, day-to-day responsibilities, and tasks performed under each job/project experience into the "description" array.
    - This MUST be an array of strings, where each string is a bullet point from the resume.
    - Do NOT summarize or shorten the bullet points; copy them exactly as written in the resume.
    - If there are no bullet points or descriptions for an experience, output an empty array [].

    RULE 8 — JOBS WITHOUT EXPLICIT PROJECTS
    If a job/experience lists bullet points but does NOT explicitly group them under specific projects:
    - Treat the entire role as a single project inside the "projects" array.
    - Leave "project_name" and "client" as empty strings "".
    - Put ALL the bullet points for that role into the "description" array of this single project.



    OUTPUT SCHEMA (map ALL resume content to this exact structure)
    {
        "Name": "Full Name from resume",
        "Education": [
            {
                "college": "Institution name",
                "degree": "Degree title",
                "graduation_year": "Year or range as written (e.g. '2021 – 2025' or '2019')",
                "grade": "CGPA or % as written (e.g. '9.64' or '85%'). Use key 'grade'."
            }
        ],
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
            "experiences": [
                {
                    "company": "Employer name",
                    "designation": "Job title",
                    "duration": "Date range as written in resume",
                    "location": "Location if mentioned, else ''",
                    "projects": [
                        {
                            "client": "External client name if explicitly stated, else ''",
                            "project_name": "Project/system name if mentioned, else ''",
                            "project_span": "Project date range if mentioned, else ''",
                            "technologies": [],
                            "description": [
                                "Bullet point 1 copied from resume exactly as written",
                                "Bullet point 2 copied from resume exactly as written"
                            ],
                            "role_responsibility": "Role/responsibility text if explicitly stated, else ''"
                        }
                    ]
                }
            ]
        }
    }
    """

    system_prompt = system_prompt.replace("{current_year}", str(current_year)).replace("{current_month}", str(current_month))

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
                    "model": "google/gemma-3-12b-it", 
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Extract this resume and return ONLY a valid JSON object with no markdown:\n\n{resume_text}"}
                    ],
                    "temperature": 0.1
                })
            )
            
            response.raise_for_status()
            result_text = response.json()['choices'][0]['message']['content'].strip()
            
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
                    # if "Experience" in parsed_json and "experiences" in parsed_json["Experience"]:
                    #     calculated_years = calculate_total_experience(parsed_json["Experience"]["experiences"])
                    #     parsed_json["Experience"]["total_experience_years"] = calculated_years

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
        # "./Resumes/Priyanshi.pdf",
        "./Resumes/Akash ShahakarQA26.pdf",
        # "./Resumes/maruf.pdf",
        # "./Resumes/Anjali_Verma_Resume.pdf",
        # "./Resumes/SagarManojNikam_DS.pdf",
        # "./Resumes/MeetOza_Resume.pdf",
    ]

    for pdf_path in resume_paths:
        process_resume(pdf_path)