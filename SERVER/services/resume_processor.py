from fastapi import HTTPException
from services.resume_extraction import extract_text_preserving_layout, extract_resume_json

def process_resume_file(file_path: str) -> dict:
    """
    Process a resume PDF file and return extracted data.
    
    Args:
        file_path: Path to the uploaded resume PDF
        
    Returns:
        dict: Extracted resume data
    """
    full_text = extract_text_preserving_layout(file_path)
    
    if not full_text:
        raise HTTPException(status_code=400, detail="Empty or unreadable PDF")
        
    extracted_data = extract_resume_json(full_text)
    if not extracted_data:
        raise HTTPException(status_code=500, detail="Failed to extract data using LLM after retries.")
        
    return extracted_data
