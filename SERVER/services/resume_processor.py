from fastapi import HTTPException
from services.resume_extraction import extract_pages_preserving_layout, extract_resume_json_chunked

def process_resume_file(file_path: str) -> dict:
    """
    Process a resume PDF file and return extracted data.
    
    Args:
        file_path: Path to the uploaded resume PDF
        
    Returns:
        dict: Extracted resume data
    """
    pages_text = extract_pages_preserving_layout(file_path)
    
    if not pages_text or all(not p for p in pages_text):
        raise HTTPException(status_code=400, detail="Empty or unreadable PDF")
        
    extracted_data = extract_resume_json_chunked(pages_text)
    if not extracted_data:
        raise HTTPException(status_code=500, detail="Failed to extract data using LLM after retries.")
        
    return extracted_data

