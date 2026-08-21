"""
CIVIC-TWIN AI — Complaint Analysis API
==========================================
Wraps complaint_analyzer.py in an HTTP API so your backend teammate can
send complaint text and get structured JSON back — same pattern as the
defect detection API (api.py in the defect_detection module).

HOW TO RUN:
    uvicorn api:app --port 8002

HOW BACKEND CALLS IT:
    POST http://localhost:8002/analyze
    JSON body: {"complaint_text": "Huge pothole near Sector 62..."}
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from complaint_analyzer import analyze_complaint

app = FastAPI(title="CIVIC-TWIN AI — Complaint Analysis Service")


class ComplaintRequest(BaseModel):
    complaint_text: str


@app.get("/")
def health_check():
    return {"status": "ok", "service": "civic-twin-complaint-analysis"}


@app.post("/analyze")
def analyze(request: ComplaintRequest):
    """
    Accepts a citizen complaint's text, returns structured analysis JSON.
    """
    try:
        result = analyze_complaint(request.complaint_text)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
