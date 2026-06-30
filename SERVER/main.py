from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from api import resume
from middleware.rate_limiter import get_load_info

app = FastAPI(
    title="nCircle Resume Parser API",
    description="Upload a resume PDF, review extracted data, and generate a formatted nCircle CV PDF",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Disposition",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include the endpoints from our API routers
app.include_router(resume.router)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend page"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend not found. Please check static/index.html</h1>")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "nCircle Resume Parser + JD Matcher",
        "version": "3.0.0"
    }

@app.get("/load")
async def load_info():
    """Return current server load and rate-limit status (for debugging)."""
    return get_load_info()

if __name__ == "__main__":
    import uvicorn
    print("Starting nCircle Resume Parser + JD Matcher API...")
    print("Extract resume:    POST /extract-resume")
    print("Generate PDF:      POST /generate-resume")
    print("Extract JD only:   POST /extract-jd")
    uvicorn.run(app, host="0.0.0.0", port=8000)