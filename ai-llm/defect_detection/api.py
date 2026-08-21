"""
CIVIC-TWIN AI — Defect Detection API
========================================
Wraps the model in a simple HTTP API so your backend teammates can send
an uploaded citizen photo and get structured defect data back — without
needing to know anything about YOLO or Python ML code.

HOW TO RUN:
    uvicorn api:app --reload --port 8001

HOW BACKEND CALLS IT (example):
    POST http://localhost:8001/detect
    form-data: file = <the image>

    Response: JSON with detections, severity, bounding boxes (see detect.py)
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
import uuid

from detect import detect_defects

app = FastAPI(title="CIVIC-TWIN AI — Defect Detection Service")

# Path to your trained model weights. Update this after training.
WEIGHTS_PATH = os.environ.get("MODEL_WEIGHTS", "runs/detect/civic_twin_defect_model/weights/best.pt")
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)


@app.get("/")
def health_check():
    """Simple endpoint so the backend team can verify the service is alive."""
    return {"status": "ok", "service": "civic-twin-defect-detection"}


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """
    Accepts an uploaded image, runs defect detection, returns structured JSON.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Save the upload temporarily so YOLO can read it from disk.
    temp_filename = f"{TEMP_DIR}/{uuid.uuid4().hex}_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = detect_defects(temp_filename, WEIGHTS_PATH)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
    finally:
        # Clean up the temp file regardless of success/failure.
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
