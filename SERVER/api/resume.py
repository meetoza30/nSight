import tempfile
import os
import shutil
import json
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from services.resume_processor import process_resume_file
from services.resume_extraction import extract_text_preserving_layout
from services.jdExtracter import extract_jd_with_llm
from services.matcher import match_resume_to_jd
from utils.generatepdf import generate_resume_pdf
from utils.generatereport import generate_match_report_pdf
from middleware.rate_limiter import check_rate_limit, increment_active, decrement_active

router = APIRouter()

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

@router.post("/extract-resume")
async def extract_resume(request: Request, file: UploadFile = File(...)):
    """
    Upload a resume PDF and extract structured data from it.
    
    - **file**: Resume PDF file to process
    
    Returns:
        dict: Extracted resume data as JSON for the frontend to display/edit
    """
    # ── Rate limit check ─────────────────────────────────────────────
    rate_headers = check_rate_limit(request, cost=1)

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are accepted. Please upload a PDF resume."
        )
    
    temp_dir = tempfile.mkdtemp()
    temp_input_path = os.path.join(temp_dir, file.filename)
    
    increment_active()
    try:
        with open(temp_input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        print(f"Processing resume: {file.filename}")
        extracted_data = process_resume_file(temp_input_path)
        
        print(f"Extracted Name: {extracted_data.get('Name', 'Unknown')}")
        
        response_data = {
            "success": True,
            "data": extracted_data
        }
        return JSONResponse(content=response_data, headers=rate_headers)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing resume: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing resume: {str(e)}"
        )
    finally:
        decrement_active()
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


@router.post("/generate-resume")
async def generate_resume(request: Request):
    """
    Generate a formatted nCircle CV PDF from the provided resume data JSON.
    
    Expects a JSON body with the full resume data structure (same format as extract-resume returns).
    
    Returns:
        FileResponse: The generated nCircle format PDF
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    if not body.get("Name"):
        raise HTTPException(status_code=400, detail="Name is required")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        candidate_name = body.get("Name", "Unknown")
        output_filename = f"{candidate_name.replace(' ', '_')}_NcircleCV.pdf"
        output_path = os.path.join(temp_dir, output_filename)
        
        generate_resume_pdf(body, output_path)
        print(f"PDF generated: {output_filename}")
        
        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating PDF: {str(e)}"
        )


@router.post("/match-bulk")
async def match_bulk_resumes(
    request: Request,
    jd_file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None),
    resume_files: List[UploadFile] = File(...)
):
    """
    Bulk match resumes against a single Job Description.

    JD input (provide exactly one):
      - jd_file: The JD as a PDF file upload
      - jd_text: The JD as a plain-text form field
      - resume_files: One or more candidate resume PDFs.

    Response:
      - results[]: per-candidate { filename, overall_score, grade, summary }
      - report_url: URL to download the generated PDF report (when >1 resume)
    """
    if not jd_file and not jd_text:
        raise HTTPException(status_code=400, detail="Either jd_file or jd_text must be provided.")

    if not resume_files or len(resume_files) == 0:
        raise HTTPException(status_code=400, detail="At least one resume file must be uploaded.")

    for rf in resume_files:
        if not rf.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are accepted. Invalid file: {rf.filename}"
            )

    if jd_file and not jd_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted for jd_file.")

    temp_dir = tempfile.mkdtemp()

    try:
        if jd_file:
            print(f"Extracting text from JD PDF: {jd_file.filename}")
            jd_temp_path = os.path.join(temp_dir, jd_file.filename)
            with open(jd_temp_path, "wb") as buffer:
                buffer.write(await jd_file.read())
            parsed_jd_text = extract_text_preserving_layout(jd_temp_path)
            if not parsed_jd_text:
                raise HTTPException(status_code=400, detail="Failed to read text from uploaded JD PDF.")
        else:
            parsed_jd_text = (jd_text or "").strip()
            if not parsed_jd_text:
                raise HTTPException(status_code=400, detail="Provided jd_text is empty.")

        print("Extracting JD structure via LLM...")
        jd_data = extract_jd_with_llm(parsed_jd_text)
        if not jd_data:
            raise HTTPException(status_code=500, detail="Failed to extract Job Description data via LLM.")

        internal_results = []
        frontend_results = []

        for file in resume_files:
            try:
                print(f"Processing resume: {file.filename}")
                file_temp_path = os.path.join(temp_dir, file.filename)
                with open(file_temp_path, "wb") as buffer:
                    buffer.write(await file.read())

                resume_data = process_resume_file(file_temp_path)

                print(f"Running matching engine for {file.filename}...")
                match_result = match_resume_to_jd(resume_data, jd_data)

                internal_results.append({
                    "filename": file.filename,
                    "success": True,
                    "match": match_result,
                })

                frontend_results.append({
                    "filename": file.filename,
                    "success": True,
                    "overall_score": match_result.get("overall_score"),
                    "grade":         match_result.get("grade"),
                    "summary":       match_result.get("summary"),
                    "candidate_name": match_result.get("candidate_name"),
                })

            except Exception as candidate_e:
                print(f"Failed to process {file.filename}: {candidate_e}")
                internal_results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(candidate_e),
                })
                frontend_results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(candidate_e),
                })

        report_download_url = None
        report_filename = "match_report.pdf"
        report_path = os.path.join(STATIC_DIR, report_filename)
        # print("internal jd match results : ", internal_results)
        try:
            generate_match_report_pdf(
                results=internal_results,
                jd_data=jd_data,
                output_path=report_path,
            )
            report_download_url = "/download-match-report"
            print(f"Match report saved: {report_path}")
        except Exception as pdf_e:
            print(f"PDF report generation failed (non-fatal): {pdf_e}")

        response_data = {
            "success": True,
            "results": frontend_results,
            "report_download_url": report_download_url,
        }
        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Bulk match API error: {e}")
        raise HTTPException(status_code=500, detail=f"Error in match-bulk: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.get("/download-match-report")
async def download_match_report():
    """
    Download the most recently generated bulk match PDF report.

    Call this endpoint after /match-bulk returns a `report_download_url`.
    The frontend should trigger a file download by navigating to this URL
    or using window.open() / an <a href> element with download attribute.

    """
    report_path = os.path.join(STATIC_DIR, "match_report.pdf")
    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=404,
            detail="No match report found. Run /match-bulk first to generate one."
        )
    return FileResponse(
        path=report_path,
        filename="match_report.pdf",
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="match_report.pdf"'},
    )

@router.post("/extract-jd")
async def extract_jd(request: Request):
    """
    Parse and structure a raw Job Description text.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
 
    jd_text = body.get("jd_text", "").strip()
    if not jd_text:
        raise HTTPException(status_code=400, detail="jd_text is required")
 
    jd_data = extract_jd_with_llm(jd_text)
    if not jd_data:
        raise HTTPException(status_code=500, detail="Failed to extract JD data via LLM.")
 
    return {"success": True, "data": jd_data}
