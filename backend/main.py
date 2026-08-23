"""
CIVIC-TWIN AI — Unified Backend
====================================
One FastAPI service combining defect detection, geolocation-based
duplicate checking, risk prediction, and budget-aware maintenance
prioritization. Complaint Analysis (Module 2, text/LLM based) has been
removed — this pipeline is photo + GPS + category only, per the actual
citizen-reporting flow.

RUN:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Interactive API docs once running: http://localhost:8000/docs
"""

from datetime import datetime, timezone

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from modules import store
from modules.defect_detection import detect_pothole, severity_for_category, MIN_POTHOLE_CONFIDENCE
from modules.duplicate_check import find_duplicate
from modules.road_classifier import classify_road
from modules.risk_engine import predict_risk
from modules.budget_optimizer import run_full_pipeline
from modules.route_check import check_route
from modules.chat import handle_chat_message

app = FastAPI(title="CIVIC-TWIN AI — Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo/dev; restrict to your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_CATEGORIES = [
    "Road Damage",
    "Drainage / Waterlogging",
    "Streetlight / Electrical",
    "Waste Management",
]


@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok", "service": "civic-twin-ai-backend"}


# ---------------------------------------------------------------------------
# Report a new issue: photo + GPS + category -> AI analysis -> dedupe -> store
# ---------------------------------------------------------------------------

@app.post("/report")
async def report_issue(
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: str = Form(...),
    file: UploadFile | None = File(None),
):
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of {VALID_CATEGORIES}")

    rows = store.load_all()

    # 1. Duplicate check — same category within ~120m of an existing open complaint.
    match, distance_m = find_duplicate(rows, latitude, longitude, category)
    if match:
        new_count = int(match.get("report_count", 1)) + 1
        store.update_complaint(match["complaint_id"], {"report_count": new_count})
        return {
            "status": "duplicate",
            "message": f"Duplicate detected — merged with existing ticket #{match['complaint_id']}",
            "matched_complaint_id": match["complaint_id"],
            "distance_m": distance_m,
            "report_count": new_count,
            "complaint": {**match, "report_count": new_count},
        }

    # 2. AI analysis. Vision model only runs for Road Damage (pothole); other
    #    categories are scored from category risk priors (no trained model exists
    #    for them — see defect_detection.py).
    complaint_id = store.next_complaint_id(rows)
    detector = "n/a"
    defect_type = None
    ai_confidence = ""

    if category == "Road Damage" and file is not None:
        image_bytes = await file.read()
        result = detect_pothole(image_bytes)

        # Validation gate: only accept this as a real pothole complaint if
        # the model is confident enough. A low/near-zero confidence (or no
        # detection at all) means the photo likely doesn't show a pothole,
        # so we reject rather than store a bogus complaint.
        confidence = result["confidence"]
        if result["defect_type"] is None or confidence is None or confidence < MIN_POTHOLE_CONFIDENCE:
            return {
                "status": "rejected",
                "message": (
                    "Complaint not added — no pothole detected in the photo "
                    f"(confidence {'n/a' if confidence is None else f'{confidence*100:.1f}%'}, "
                    f"needs at least {MIN_POTHOLE_CONFIDENCE*100:.0f}%)."
                ),
                "detection": result,
            }

        defect_type = result["defect_type"]
        ai_confidence = confidence
        severity, severity_score = result["severity"], result["severity_score"]
        detector = result["detector"]
    else:
        sev = severity_for_category(category, complaint_id)
        severity, severity_score = sev["severity"], sev["severity_score"]
        defect_type = {
            "Drainage / Waterlogging": "waterlogging",
            "Streetlight / Electrical": "streetlight-fault",
            "Waste Management": "waste-pileup",
        }.get(category, category.lower())
        detector = "category-prior" if file is None else "heuristic-cv"

    # 3. Road authority classification (NHAI vs State/Municipal).
    road = classify_road(latitude, longitude)

    # 4. Persist.
    record = {
        "complaint_id": complaint_id,
        "latitude": latitude,
        "longitude": longitude,
        "complaint_category": category,
        "defect_type": defect_type,
        "ai_confidence": ai_confidence,
        "severity": severity,
        "severity_score": severity_score,
        "road_type": road["road_type"],
        "road_name": road["road_name"],
        "date_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "report_count": 1,
        "status": "Open",
        "detector": detector,
    }
    store.append_complaint(record)

    return {"status": "created", "message": "New complaint registered", "complaint": record}


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@app.get("/complaints")
def list_complaints(category: str | None = None, road_type: str | None = None):
    rows = store.load_all()
    if category:
        rows = [r for r in rows if r["complaint_category"] == category]
    if road_type:
        rows = [r for r in rows if r["road_type"] == road_type]
    return {"complaints": rows, "total": len(rows)}


@app.get("/risk-zones")
def risk_zones(top_n: int = 20):
    return {"zones": predict_risk(top_n=top_n)}


@app.get("/prioritize")
def prioritize(budget: float = 500000, top_n: int = 50):
    return run_full_pipeline(budget=budget, top_n_zones=top_n)


@app.get("/stats")
def stats():
    rows = store.load_all()
    total = len(rows)
    by_category = {}
    by_severity = {}
    by_road_type = {}
    for r in rows:
        by_category[r["complaint_category"]] = by_category.get(r["complaint_category"], 0) + 1
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + 1
        by_road_type[r["road_type"]] = by_road_type.get(r["road_type"], 0) + 1

    critical_high = sum(1 for r in rows if r["severity"] in ("Critical", "High"))

    return {
        "total_complaints": total,
        "critical_or_high": critical_high,
        "by_category": by_category,
        "by_severity": by_severity,
        "by_road_type": by_road_type,
    }


class RouteCheckRequest(BaseModel):
    origin: str
    destination: str


@app.post("/route-check")
def route_check(req: RouteCheckRequest):
    """Straight-line check for reported issues between two places (Noida
    sector names or 'lat,lon' coordinates)."""
    return check_route(req.origin, req.destination)


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    """Conversational front-end for route_check — parses free-text like
    "from Sector 62 to Sector 18" and replies in natural language."""
    return handle_chat_message(req.message)


@app.post("/admin/reset-seed")
def reset_seed():
    """Dev helper: wipes live complaints and re-seeds from the historical dataset."""
    store.reset_to_seed()
    return {"status": "reset"}
