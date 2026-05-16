import json
import re
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# SECTION 1 — Pure Python scoring helpers (fast, no LLM needed)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation for fuzzy comparison."""
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()


def _skills_from_resume(resume: dict) -> list[str]:
    """
    Collect every skill/technology from the resume:
    - Skills section (all categories)
    - Technologies listed in project blocks
    Returns a flat list of normalized strings.
    """
    skills = []

    # From dedicated Skills section
    skills_section = resume.get("Skills", {})
    for category, skill_list in skills_section.items():
        if isinstance(skill_list, list):
            skills.extend(skill_list)

    # From experience project technologies
    for exp in resume.get("Experience", {}).get("experiences", []):
        for proj in exp.get("projects", []):
            for tech in proj.get("technologies", []):
                skills.append(tech)

    return [_normalize(s) for s in skills if s]

def _score_skills(resume: dict, jd: dict) -> dict:
    """
    Compare JD required + preferred skills against all resume skills.
    Returns score 0-100 and matched/missing lists.
    """
    resume_skills = set(_skills_from_resume(resume))

    required = jd.get("required_skills_normalized", [])
    preferred = jd.get("preferred_skills_normalized", [])

    def fuzzy_match(jd_skill: str, resume_set: set) -> bool:
        """True if jd_skill appears anywhere as a substring in resume skills or vice versa."""
        jd_norm = _normalize(jd_skill)
        for r in resume_set:
            if jd_norm in r or r in jd_norm:
                return True
        return False

    matched_required = [s for s in required if fuzzy_match(s, resume_skills)]
    missing_required = [s for s in required if not fuzzy_match(s, resume_skills)]
    matched_preferred = [s for s in preferred if fuzzy_match(s, resume_skills)]
    missing_preferred = [s for s in preferred if not fuzzy_match(s, resume_skills)]

    # Score: required skills count for 80%, preferred for 20%
    req_score = (len(matched_required) / len(required) * 100) if required else 100
    pref_score = (len(matched_preferred) / len(preferred) * 100) if preferred else 100
    final_score = round(req_score * 0.80 + pref_score * 0.20)

    return {
        "score": final_score,
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_preferred": matched_preferred,
        "missing_preferred": missing_preferred,
        "detail": f"{len(matched_required)}/{len(required)} required skills matched"
                  + (f", {len(matched_preferred)}/{len(preferred)} preferred" if preferred else "")
    }

def _score_experience(resume: dict, jd: dict) -> dict:
    """
    Compare candidate total experience years vs JD requirement.
    Also checks domain/industry overlap using job titles.
    """
    candidate_years = resume.get("Experience", {}).get("total_experience_years", 0)
    required_years = jd.get("experience_required_years", 0)

    # Years scoring
    if required_years == 0:
        years_score = 100
        years_detail = "No experience requirement specified"
    elif candidate_years >= required_years:
        # Give full marks if meets requirement; slight bonus taper for over-qualification
        years_score = min(100, round(100 - max(0, candidate_years - required_years - 2) * 3))
        years_detail = f"{candidate_years} yrs present vs {required_years} yrs required"
    else:
        # Partial credit: ratio of actual to required, floored at 20
        ratio = candidate_years / required_years
        years_score = max(20, round(ratio * 90))
        years_detail = f"{candidate_years} yrs present, {required_years} yrs required — below requirement"

    # Domain match — compare JD key_domain against candidate's company/project context
    jd_domain = _normalize(jd.get("key_domain", ""))
    jd_title = _normalize(jd.get("job_title", ""))
    candidate_titles = [
        _normalize(exp.get("designation", ""))
        for exp in resume.get("Experience", {}).get("experiences", [])
    ]
    candidate_clients = [
        _normalize(proj.get("client", ""))
        for exp in resume.get("Experience", {}).get("experiences", [])
        for proj in exp.get("projects", [])
    ]
    candidate_context = " ".join(candidate_titles + candidate_clients)

    # Very loose domain check — does the candidate's background touch this domain?
    domain_words = jd_domain.split() + jd_title.split()
    domain_hits = sum(1 for w in domain_words if len(w) > 3 and w in candidate_context)
    domain_score = min(100, domain_hits * 20) if domain_words else 50

    final_score = round(years_score * 0.75 + domain_score * 0.25)

    return {
        "score": final_score,
        "years_score": years_score,
        "domain_score": domain_score,
        "detail": years_detail
    }

def _score_education(resume: dict, jd: dict) -> dict:
    """
    Check if candidate's education meets the JD requirement.
    """
    jd_edu = _normalize(jd.get("education_required", ""))
    candidate_degrees = [
        _normalize(edu.get("degree", ""))
        for edu in resume.get("Education", [])
    ]

    if not jd_edu or "any" in jd_edu:
        return {"score": 100, "detail": "No specific education requirement"}

    # Degree level ladder
    degree_ladder = ["diploma", "bachelor", "b.e", "b.tech", "b.sc", "b.com",
                     "master", "m.tech", "m.sc", "mba", "phd", "doctorate"]

    def degree_level(text: str) -> int:
        for i, keyword in enumerate(degree_ladder):
            if keyword in text:
                return i
        return -1

    required_level = degree_level(jd_edu)
    candidate_max_level = max((degree_level(d) for d in candidate_degrees), default=-1)

    if required_level == -1:
        # Can't determine requirement — partial credit
        score = 70
        detail = "Education requirement unclear — partial match assumed"
    elif candidate_max_level >= required_level:
        score = 100
        detail = "Education requirement met"
    elif candidate_max_level >= 0:
        # Has some degree, just not matching level
        score = 60
        detail = "Degree present but may not meet specific requirement"
    else:
        score = 30
        detail = "No matching education found in resume"

    return {"score": score, "detail": detail}
# ---------------------------------------------------------------------------
# SECTION 2 — LLM scoring for role alignment + overall summary
# ---------------------------------------------------------------------------
def _score_role_alignment_with_llm(resume: dict, jd: dict) -> dict:
    """
    Uses LLM to evaluate semantic alignment between the candidate's role/
    responsibilities and the JD's responsibilities. Returns score 0-100.
    """
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    # Build compact summaries to keep prompt small
    candidate_summary = {
        "designations": [
            exp.get("designation", "") for exp in resume.get("Experience", {}).get("experiences", [])
        ],
        "responsibilities": [
            point
            for exp in resume.get("Experience", {}).get("experiences", [])
            for proj in exp.get("projects", [])
            for point in proj.get("description", [])[:3]  # top 3 per project to save tokens
        ][:15]  # max 15 total
    }

    jd_summary = {
        "job_title": jd.get("job_title", ""),
        "responsibilities": jd.get("responsibilities", [])[:10]
    }

    prompt = f"""
You are evaluating how well a candidate's work experience aligns with a job description.

CANDIDATE EXPERIENCE SUMMARY:
{json.dumps(candidate_summary, indent=2)}

JOB DESCRIPTION REQUIREMENTS:
{json.dumps(jd_summary, indent=2)}

Score the alignment from 0 to 100 where:
- 90-100: Near-perfect role match, responsibilities almost identical
- 70-89: Strong overlap, candidate has done similar work
- 50-69: Partial overlap, some relevant experience
- 30-49: Limited overlap, different domain or responsibilities
- 0-29: Very little alignment

Respond ONLY with a JSON object, no markdown:
{{
  "score": <number 0-100>,
  "detail": "<one sentence explanation>"
}}
"""

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                data=json.dumps({
                    "model": "google/gemma-3-12b-it",
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                })
            )
            response.raise_for_status()
            raw = response.json()['choices'][0]['message']['content'].strip()
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                result = json.loads(raw[start:end + 1])
                score = max(0, min(100, int(result.get("score", 50))))
                return {"score": score, "detail": result.get("detail", "")}
        except Exception as e:
            print(f"Role alignment LLM call failed attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)

    # Fallback: title-based heuristic
    jd_title_words = set(_normalize(jd.get("job_title", "")).split())
    candidate_titles = " ".join([
        _normalize(exp.get("designation", ""))
        for exp in resume.get("Experience", {}).get("experiences", [])
    ])
    hits = sum(1 for w in jd_title_words if len(w) > 3 and w in candidate_titles)
    fallback_score = min(80, hits * 20 + 30)
    return {"score": fallback_score, "detail": "Scored via title keyword match (LLM unavailable)"}


def _generate_match_summary_with_llm(
    resume: dict,
    jd: dict,
    overall_score: int,
    breakdown: dict
) -> str:
    """
    Generates a short human-readable summary of the match result.
    """
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    candidate_name = resume.get("Name", "The candidate")
    jd_title = jd.get("job_title", "this role")
    missing_skills = breakdown.get("skills", {}).get("missing_required", [])

    prompt = f"""
Write a 2-3 sentence professional recruiter summary for this resume-JD match.

Candidate: {candidate_name}
Role: {jd_title}
Overall match score: {overall_score}/100
Skills score: {breakdown['skills']['score']}/100
Experience score: {breakdown['experience']['score']}/100
Role alignment score: {breakdown['role_alignment']['score']}/100
Education score: {breakdown['education']['score']}/100
Missing required skills: {', '.join(missing_skills[:5]) if missing_skills else 'None'}

Be concise, factual, and professional. Do not use bullet points. 
Start with the candidate's name and their fit level (Strong/Good/Moderate/Weak).
Respond with ONLY the summary text, no JSON, no markdown.
"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "google/gemma-3-12b-it",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 150
            })
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Summary generation failed: {e}")
        # Deterministic fallback
        grade = _score_to_grade(overall_score)
        missing_str = (", ".join(missing_skills[:3]) + " missing") if missing_skills else "no critical skill gaps"
        return (
            f"{candidate_name} is a {grade} for the {jd_title} role with an overall score of "
            f"{overall_score}/100. Key highlights: {missing_str}."
        )


# ---------------------------------------------------------------------------
# SECTION 3 — Orchestrator
# ---------------------------------------------------------------------------

# Score weights — must sum to 1.0
WEIGHTS = {
    "skills": 0.40,
    "experience": 0.30,
    "role_alignment": 0.20,
    "education": 0.10,
}


def _score_to_grade(score: int) -> str:
    if score >= 80:
        return "Strong Match"
    elif score >= 65:
        return "Good Match"
    elif score >= 50:
        return "Moderate Match"
    elif score >= 35:
        return "Weak Match"
    else:
        return "Poor Match"


def _score_to_color(score: int) -> str:
    """Returns a color hint for the frontend."""
    if score >= 80:
        return "green"
    elif score >= 65:
        return "blue"
    elif score >= 50:
        return "amber"
    else:
        return "red"

def match_resume_to_jd(resume: dict, jd: dict) -> dict:
    """
    Master function. Takes extracted resume dict and extracted JD dict.
    Returns a complete match result with overall score, breakdown, and summary.

    Args:
        resume: Structured resume data (output of resume_extraction.py extract_resume_with_llm)
        jd:     Structured JD data (output of jd_extractor.py extract_jd_with_llm)

    Returns:
        dict with keys: overall_score, grade, color, breakdown, summary, missing_skills
    """
    print("Running skills scoring...")
    skills_result = _score_skills(resume, jd)

    print("Running experience scoring...")
    experience_result = _score_experience(resume, jd)

    print("Running education scoring...")
    education_result = _score_education(resume, jd)

    print("Running role alignment scoring (LLM)...")
    role_result = _score_role_alignment_with_llm(resume, jd)

    breakdown = {
        "skills": skills_result,
        "experience": experience_result,
        "role_alignment": role_result,
        "education": education_result,
    }

    # Weighted aggregate
    overall_score = round(
        skills_result["score"] * WEIGHTS["skills"] +
        experience_result["score"] * WEIGHTS["experience"] +
        role_result["score"] * WEIGHTS["role_alignment"] +
        education_result["score"] * WEIGHTS["education"]
    )

    grade = _score_to_grade(overall_score)
    color = _score_to_color(overall_score)

    print(f"Generating match summary (LLM)...")
    summary = _generate_match_summary_with_llm(resume, jd, overall_score, breakdown)

    # Flat list of all missing skills for convenience
    all_missing = (
        skills_result.get("missing_required", []) +
        skills_result.get("missing_preferred", [])
    )

    return {
        "overall_score": overall_score,
        "grade": grade,
        "color": color,
        "summary": summary,
        "breakdown": breakdown,
        "missing_skills": all_missing,
        "matched_skills": skills_result.get("matched_required", []),
        "candidate_name": resume.get("Name", ""),
        "job_title": jd.get("job_title", ""),
        "weights_used": WEIGHTS,
    }


if __name__ == "__main__":
    import json
    from resume_extraction import extract_resume_with_llm, extract_text_preserving_layout
    from jdExtracter import extract_jd_with_llm

    # A sample Job Description for testing
    sample_jd_text = """
    Role: Senior Software Engineer (Python)
    Experience: 3-5 years
    Domain: FinTech / SaaS

    We are looking for a skilled Backend Developer with 3+ years of experience to join our core API team. 
    You will be responsible for building high-performance server-side web applications.

    Required Skills:
    - Proficiency in Python and server-side logic
    - Experience with frameworks like Django or FastAPI
    - Strong understanding of SQL databases like PostgreSQL
    - REST API design and development

    Preferred Skills:
    - Experience with AWS (EC2, S3)
    - Familiarity with CI/CD pipelines
    - Understanding of Docker containerization
    - Agile development methodologies

    Education: Bachelor's degree in Computer Science or related field.

    Responsibilities:
    - Write clean, maintainable, and efficient Python code.
    - Design robust APIs to support front-end applications.
    - Participate in code reviews and architectural discussions.
    """

    # Provide local resume paths you want to test here just like in resume_extraction.py
    resume_paths = [
        # "./Resumes/Priyanshi.pdf",
        # "./Resumes/Akash ShahakarQA26.pdf",
        # "./Resumes/maruf.pdf",
        "./Resumes/MeetOza_Resume.pdf",
    ]

    for pdf_path in resume_paths:
        print(f"\n--- Processing {pdf_path} ---")
        
        # 1. Extract raw text from PDF
        resume_text = extract_text_preserving_layout(pdf_path)
        if not resume_text:
            print(f"Could not extract text from {pdf_path}")
            continue
            
        # 2. Parse resume text to JSON structure
        print("Extracting resume data with LLM...")
        resume_data = extract_resume_with_llm(resume_text)
        if not resume_data:
            print("Failed to parse resume.")
            continue
            
        # 3. Parse JD text to JSON structure
        print("Extracting JD data with LLM...")
        jd_data = extract_jd_with_llm(sample_jd_text)
        if not jd_data:
            print("Failed to parse JD.")
            continue
            
        # 4. Run the Matcher
        print("Matching Resume to JD...")
        match_result = match_resume_to_jd(resume_data, jd_data)
        
        # 5. Display the matching result
        print("\n=== FINAL MATCH RESULT ===")
        print(json.dumps(match_result, indent=4, ensure_ascii=False))
        print("==========================\n")
