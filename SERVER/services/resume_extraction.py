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


def extract_resume_json(resume_text, model="mistralai/mistral-nemo", token_usage_tracker=None):
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
            if token_usage_tracker is not None and isinstance(token_usage_tracker, list):
                token_usage_tracker.append(data["usage"])
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

def merge_resume_jsons(json_list):
    """
    Merges multiple parsed resume JSON objects into one.
    """
    merged = {
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
    
    for data in json_list:
        if not data or not isinstance(data, dict):
            continue
            
        # 1. Name: Take first non-empty name
        if not merged["Name"] and data.get("Name"):
            merged["Name"] = data["Name"]
            
        # 2. Education: Merge without duplicates
        for edu in data.get("Education", []):
            if not isinstance(edu, dict):
                continue
            college = edu.get("college", "") or ""
            degree = edu.get("degree", "") or ""
            college_clean = str(college).strip().lower()
            degree_clean = str(degree).strip().lower()
            
            exists = False
            for m_edu in merged["Education"]:
                m_college_clean = str(m_edu.get("college", "")).strip().lower()
                m_degree_clean = str(m_edu.get("degree", "")).strip().lower()
                if college_clean == m_college_clean and degree_clean == m_degree_clean:
                    # Update grade if not set
                    if not m_edu.get("grade") and edu.get("grade"):
                        m_edu["grade"] = edu["grade"]
                    # Update graduation_year if not set
                    if not m_edu.get("graduation_year") and edu.get("graduation_year"):
                        m_edu["graduation_year"] = edu["graduation_year"]
                    exists = True
                    break
            if not exists:
                merged["Education"].append(edu)
                
        # 3. Skills: Merge without duplicates
        skills_data = data.get("Skills", {})
        if isinstance(skills_data, dict):
            for category in ["Languages", "Web Technologies", "Tools", "Technologies", "Operating System"]:
                if category not in merged["Skills"]:
                    merged["Skills"][category] = []
                existing_skills_lower = {str(s).lower().strip(): s for s in merged["Skills"][category]}
                for skill in skills_data.get(category, []):
                    skill_clean = str(skill).strip()
                    if skill_clean.lower() not in existing_skills_lower:
                        merged["Skills"][category].append(skill_clean)
                        existing_skills_lower[skill_clean.lower()] = skill_clean
                        
        # 4. Achievements: Merge without duplicates
        for ach in data.get("Achievements", []):
            ach_clean = str(ach).strip()
            if ach_clean and ach_clean not in merged["Achievements"]:
                merged["Achievements"].append(ach_clean)
                
        # 5. Experience: Merge experiences
        exp_data = data.get("Experience", {})
        if isinstance(exp_data, dict):
            for exp in exp_data.get("experiences", []):
                if not isinstance(exp, dict):
                    continue
                company = exp.get("company", "") or ""
                designation = exp.get("designation", "") or ""
                company_clean = str(company).strip().lower()
                if not company_clean:
                    continue
                    
                # Try to find a matching company in merged experiences
                matched_exp = None
                for m_exp in merged["Experience"]["experiences"]:
                    if str(m_exp.get("company", "")).strip().lower() == company_clean:
                        matched_exp = m_exp
                        break
                        
                if matched_exp:
                    # Merge designation/duration/location if not set
                    if not matched_exp.get("designation") and designation:
                        matched_exp["designation"] = designation
                    if not matched_exp.get("duration") and exp.get("duration"):
                        matched_exp["duration"] = exp["duration"]
                    if not matched_exp.get("location") and exp.get("location"):
                        matched_exp["location"] = exp["location"]
                        
                    # Merge projects
                    for proj in exp.get("projects", []):
                        if not isinstance(proj, dict):
                            continue
                        proj_name = proj.get("project_name", "") or ""
                        proj_name_clean = str(proj_name).strip().lower()
                        
                        matched_proj = None
                        if proj_name_clean:
                            for m_proj in matched_exp.get("projects", []):
                                if str(m_proj.get("project_name", "")).strip().lower() == proj_name_clean:
                                    matched_proj = m_proj
                                    break
                                    
                        if matched_proj:
                            # Merge project details
                            if not matched_proj.get("client") and proj.get("client"):
                                matched_proj["client"] = proj["client"]
                            if not matched_proj.get("project_span") and proj.get("project_span"):
                                matched_proj["project_span"] = proj["project_span"]
                            if not matched_proj.get("role_responsibility") and proj.get("role_responsibility"):
                                matched_proj["role_responsibility"] = proj["role_responsibility"]
                                
                            # Merge technologies
                            existing_tech = {str(t).lower().strip() for t in matched_proj.get("technologies", [])}
                            for tech in proj.get("technologies", []):
                                tech_clean = str(tech).strip()
                                if tech_clean.lower() not in existing_tech:
                                    matched_proj["technologies"].append(tech_clean)
                                    existing_tech.add(tech_clean.lower())
                                    
                            # Merge description
                            for desc in proj.get("description", []):
                                desc_clean = str(desc).strip()
                                if desc_clean and desc_clean not in matched_proj["description"]:
                                    matched_proj["description"].append(desc_clean)
                        else:
                            matched_exp["projects"].append(proj)
                else:
                    merged["Experience"]["experiences"].append(exp)
                    
    return merged


def extract_resume_json_chunked(pages_text, model="mistralai/mistral-nemo"):
    """
    Processes the resume page-by-page/chunk-by-chunk. 
    - If total pages <= 3, combines them and makes a single LLM API call.
    - If total pages > 3, groups pages into chunks of 2 pages, extracts them in parallel,
      and merges the parsed JSON states in Python.
    Saves intermediate/final states to SERVER/temp_states/ on the server.
    """
    import concurrent.futures
    import uuid
    
    # Track all token usages
    token_usage_tracker = []
    
    # Filter out empty pages
    non_empty_pages = [(idx + 1, text) for idx, text in enumerate(pages_text) if text.strip()]
    if not non_empty_pages:
        return {
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
        
    total_pages = len(pages_text)
    server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_states_dir = os.path.join(server_dir, "temp_states")
    os.makedirs(temp_states_dir, exist_ok=True)
    
    process_uuid = str(uuid.uuid4())
    print(f"Starting optimized resume parsing. Process UUID: {process_uuid}, Total Pages: {total_pages}, Non-empty Pages: {len(non_empty_pages)}")

    # 1. Single call optimization for <= 3 pages
    if len(non_empty_pages) <= 3:
        print("Using single call extraction (<= 3 pages)...")
        combined_text = "\n\n".join([text for _, text in non_empty_pages])
        result = extract_resume_json(combined_text, model=model, token_usage_tracker=token_usage_tracker)
        
        # Print total token usage
        if token_usage_tracker:
            total_prompt = sum(u.get("prompt_tokens", 0) for u in token_usage_tracker)
            total_completion = sum(u.get("completion_tokens", 0) for u in token_usage_tracker)
            total_tokens = sum(u.get("total_tokens", 0) for u in token_usage_tracker)
            print("\n=== TOTAL RESUME EXTRACTION TOKEN USAGE ===")
            print(f"Total Prompt Tokens: {total_prompt}")
            print(f"Total Completion Tokens: {total_completion}")
            print(f"Total Tokens: {total_tokens}")
            print("============================================\n")
            
        if result:
            # Save final state to file as requested by the server logic
            final_file_path = os.path.join(temp_states_dir, f"resume_{process_uuid}_final.json")
            try:
                with open(final_file_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
                print(f"Saved final state to {final_file_path}")
            except Exception as se:
                print(f"Failed to save final state file: {se}")
            return result
        else:
            print("Single call extraction failed. Falling back to chunked processing.")

    # 2. Parallel Chunked Extraction for > 3 pages (or fallback if single call failed)
    # Group pages into chunks of 2 pages
    chunks = []
    current_chunk_pages = []
    current_chunk_text = []
    
    for page_num, text in non_empty_pages:
        current_chunk_pages.append(page_num)
        current_chunk_text.append(text)
        if len(current_chunk_pages) == 2:
            chunks.append((list(current_chunk_pages), "\n\n".join(current_chunk_text)))
            current_chunk_pages = []
            current_chunk_text = []
            
    if current_chunk_pages:
        chunks.append((current_chunk_pages, "\n\n".join(current_chunk_text)))
        
    print(f"Divided into {len(chunks)} chunks for parallel processing.")
    
    def extract_chunk(chunk_idx, chunk_info):
        pages_in_chunk, chunk_text = chunk_info
        print(f"Starting extraction for chunk {chunk_idx + 1}/{len(chunks)} (pages {pages_in_chunk})...")
        res = extract_resume_json(chunk_text, model=model, token_usage_tracker=token_usage_tracker)
        if res:
            # Save intermediate chunk state
            chunk_file_path = os.path.join(temp_states_dir, f"resume_{process_uuid}_chunk_{chunk_idx + 1}.json")
            try:
                with open(chunk_file_path, "w", encoding="utf-8") as f:
                    json.dump(res, f, indent=4, ensure_ascii=False)
                print(f"Saved state for chunk {chunk_idx + 1} to {chunk_file_path}")
            except Exception as se:
                print(f"Failed to save chunk file: {se}")
        return res

    chunk_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(chunks))) as executor:
        # Submit all tasks
        future_to_idx = {executor.submit(extract_chunk, idx, chunk): idx for idx, chunk in enumerate(chunks)}
        
        # Collect results ordered by chunk index
        results_by_idx = {}
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results_by_idx[idx] = future.result()
            except Exception as exc:
                print(f"Chunk {idx + 1} generated an exception: {exc}")
                results_by_idx[idx] = None
                
        for idx in range(len(chunks)):
            res = results_by_idx.get(idx)
            if res:
                chunk_results.append(res)
                
    # Print total token usage
    if token_usage_tracker:
        total_prompt = sum(u.get("prompt_tokens", 0) for u in token_usage_tracker)
        total_completion = sum(u.get("completion_tokens", 0) for u in token_usage_tracker)
        total_tokens = sum(u.get("total_tokens", 0) for u in token_usage_tracker)
        print("\n=== TOTAL RESUME EXTRACTION TOKEN USAGE ===")
        print(f"Total Prompt Tokens: {total_prompt}")
        print(f"Total Completion Tokens: {total_completion}")
        print(f"Total Tokens: {total_tokens}")
        print("============================================\n")
        
    if not chunk_results:
        print("Error: All chunk extractions failed.")
        return None
        
    print(f"Successfully extracted {len(chunk_results)}/{len(chunks)} chunks. Merging...")
    merged_state = merge_resume_jsons(chunk_results)
    
    # 3. Post-processing calculations & cleaning (done at the end)
    if "Experience" in merged_state and "experiences" in merged_state["Experience"]:
        calculated_years = calculate_total_experience(merged_state["Experience"]["experiences"])
        if calculated_years > 0:
            merged_state["Experience"]["total_experience_years"] = calculated_years

    # Clean bullet points in Achievements and Experience
    def clean_text(text):
        if isinstance(text, str):
            return re.sub(r'^[◆•\-*·\s]+', '', text).strip()
        return text

    if "Achievements" in merged_state and isinstance(merged_state["Achievements"], list):
        merged_state["Achievements"] = [clean_text(a) for a in merged_state["Achievements"] if clean_text(a)]
        
    if "Experience" in merged_state and isinstance(merged_state["Experience"], dict) and "experiences" in merged_state["Experience"]:
        for exp in merged_state["Experience"]["experiences"]:
            if "projects" in exp and isinstance(exp["projects"], list):
                for proj in exp["projects"]:
                    if "description" in proj and isinstance(proj["description"], list):
                        proj["description"] = [clean_text(d) for d in proj["description"] if clean_text(d)]

    # Save the final JSON state to the server
    final_file_path = os.path.join(temp_states_dir, f"resume_{process_uuid}_final.json")
    try:
        with open(final_file_path, "w", encoding="utf-8") as f:
            json.dump(merged_state, f, indent=4, ensure_ascii=False)
        print(f"Saved final state to {final_file_path}")
    except Exception as se:
        print(f"Failed to save final state file: {se}")

    return merged_state

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