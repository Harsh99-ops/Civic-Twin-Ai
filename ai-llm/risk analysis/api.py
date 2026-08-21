"""
CIVIC-TWIN AI — Risk Prediction API
========================================
HOW TO RUN:
    uvicorn api:app --port 8004

ENDPOINTS:
    GET  /risk-zones           — get risk zones from the bundled/default CSV
    POST /risk-zones/upload    — upload a new complaints CSV and get risk zones back
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
import shutil
import os
import uuid
from risk_engine import predict_risk

app = FastAPI(title="CIVIC-TWIN AI — Risk Prediction Service")

# Path to the default complaints dataset. Update this to match wherever
# your noida_complaints_300.csv actually lives relative to this script.
DEFAULT_CSV_PATH = os.environ.get("COMPLAINTS_CSV", "noida_complaints_300.csv")
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "civic-twin-risk-prediction"}


@app.get("/risk-zones")
def get_risk_zones(top_n: int = 20):
    """
    Get the top N highest-risk zones using the default complaints dataset.
    """
    try:
        zones = predict_risk(DEFAULT_CSV_PATH, top_n=top_n)
        return {"zones": zones, "total_zones": len(zones)}
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Default complaints CSV not found at '{DEFAULT_CSV_PATH}'. "
                   f"Set the COMPLAINTS_CSV environment variable to the correct path."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk prediction failed: {str(e)}")


@app.post("/risk-zones/upload")
async def upload_and_predict(file: UploadFile = File(...), top_n: int = 20):
    """
    Upload a complaints CSV (matching the expected schema: complaint_id,
    latitude, longitude, complaint_category, date_time) and get risk zones back.
    Useful for your backend to send live/updated complaint data instead of
    relying on the static default file.
    """
    temp_path = f"{TEMP_DIR}/{uuid.uuid4().hex}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        zones = predict_risk(temp_path, top_n=top_n)
        return {"zones": zones, "total_zones": len(zones)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk prediction failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
