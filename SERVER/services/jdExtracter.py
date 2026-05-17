import json
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()


def extract_jd_with_llm(jd_text: str) -> dict | None:
    """
    Sends a raw Job Description text to the LLM and returns a structured JSON dict.
    Mirrors the same pattern used in resume_extraction.py for resume extraction.
    """

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    system_prompt = """
    You are a backend data extraction API. You ONLY output raw, valid JSON. No markdown, no explanation, no preamble.

    Your task is to parse a Job Description (JD) into a structured JSON object.

    RULES:
    - Extract ONLY what is explicitly stated in the JD. Do NOT infer or invent.
    - For skills/technologies, separate "required" (must-have, mandatory) from "preferred" (nice-to-have, bonus, plus).
    - If the JD does not differentiate required vs preferred, put all skills under "required_skills" and leave "preferred_skills" empty.
    - For experience, extract the minimum years mentioned (e.g. "3+ years" → 3). If a range is given (e.g. "3-5 years"), use the lower bound.
    - If no experience requirement is stated, use 0.
    - For education, extract the minimum degree level mentioned (e.g. "Bachelor's", "Master's", "Any Graduate").
    - Extract the responsibilities as a list of strings, copied exactly from the JD.
    - Extract key_domain as the industry/domain the role is in (e.g. "FinTech", "E-Commerce", "Healthcare", "General IT").
      Infer this from context if not explicitly stated.

    OUTPUT SCHEMA (use this exact structure):
    {
        "job_title": "Exact job title from JD",
        "company": "Company name if mentioned, else ''",
        "key_domain": "Industry or domain (e.g. FinTech, E-Commerce, Healthcare)",
        "experience_required_years": 0,
        "education_required": "e.g. Bachelor's in Computer Science, Any Graduate, Master's preferred",
        "required_skills": [
            "Skill or technology that is mandatory"
        ],
        "preferred_skills": [
            "Skill or technology that is nice-to-have"
        ],
        "responsibilities": [
            "Responsibility bullet point copied from JD"
        ],
        "other_requirements": [
            "Any other requirements like soft skills, certifications, location, travel, etc."
        ]
    }
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"JD extraction attempt {attempt + 1}/{max_retries}...")
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
                        {"role": "user", "content": f"Parse this Job Description and return ONLY a valid JSON object:\n\n{jd_text}"}
                    ],
                    "temperature": 0.1
                })
            )
            data = response.json()
            print("jd extraction")
            print("Prompt Tokens:", data["usage"]["prompt_tokens"])
            print("Completion Tokens:", data["usage"]["completion_tokens"])
            print("Total Tokens:", data["usage"]["total_tokens"])
            
            response.raise_for_status()
            result_text = response.json()['choices'][0]['message']['content'].strip()
            # print("extracted jd (json) : ", result_text)
            # Extract JSON safely
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}')

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                clean_json = result_text[start_idx:end_idx + 1]
                try:
                    parsed = json.loads(clean_json)
                    print("parsed",parsed)

                    # Basic validation
                    if not isinstance(parsed, dict) or "job_title" not in parsed:
                        print(f"JD format validation failed on attempt {attempt + 1}. Retrying...")
                        continue

                    # Ensure all expected keys exist with defaults
                    parsed.setdefault("company", "")
                    parsed.setdefault("key_domain", "")
                    parsed.setdefault("experience_required_years", 0)
                    parsed.setdefault("education_required", "")
                    parsed.setdefault("required_skills", [])
                    parsed.setdefault("preferred_skills", [])
                    parsed.setdefault("responsibilities", [])
                    parsed.setdefault("other_requirements", [])

                    # Normalize skills to lowercase for consistent matching
                    parsed["required_skills_normalized"] = [s.lower().strip() for s in parsed["required_skills"]]
                    parsed["preferred_skills_normalized"] = [s.lower().strip() for s in parsed["preferred_skills"]]

                    print(f"JD extracted successfully: {parsed['job_title']}")
                    return parsed

                except json.JSONDecodeError as e:
                    print(f"JD JSON parse error on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        return None
            else:
                print(f"No JSON brackets found in JD response on attempt {attempt + 1}.")
                if attempt == max_retries - 1:
                    return None

        except Exception as e:
            print(f"JD extraction failed on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(2)

    return None