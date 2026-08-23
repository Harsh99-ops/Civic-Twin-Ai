# CIVIC-TWIN AI

A civic infrastructure reporting platform: citizens photograph and geotag
issues (potholes, waterlogging, streetlight faults, waste), an AI pipeline
detects and scores severity, duplicate reports of the same defect get
merged automatically by location, and a risk-scoring + budget-optimization
engine tells a municipal officer exactly which zones to fix first and what
it'll cost — split out by whether the road is under NHAI or State/Municipal
authority.

```
citizen photo + GPS + category
        │
        ▼
  POST /report ──► duplicate check (same category, ~120m radius)
        │                 │
        │            duplicate? ──► merge into existing ticket,
        │                            bump report_count
        │ not duplicate
        ▼
  AI detection (pothole → YOLO/heuristic CV; other categories → priors)
        │
        ▼
  road authority classification (NHAI vs State/Municipal)
        │
        ▼
  stored in complaints.csv
        │
        ▼
  risk engine (zone clustering + frequency + severity + trend)
        │
        ▼
  budget optimizer (greedy best-value-per-rupee) ──► GIS map + Priority Engine dashboard
```

## What changed from the original 5-module handoff

- **Complaint Analysis (LLM/Gemini text module) — removed entirely.** The
  actual citizen flow never collects complaint text, only a photo + GPS +
  category, so there was nothing for it to analyze.
- **Duplicate Detection — rebuilt as geolocation-only.** The original used
  Gemini text embeddings; since there's no complaint text, duplicates are
  now detected by proximity (same category within ~120m of an existing
  open report). No API key needed anymore.
- **Defect Detection** — kept the YOLOv8 + severity-scoring design, but
  added a built-in OpenCV heuristic fallback so the pipeline runs today
  without a trained model. Drop trained weights in later (see below) and
  it switches over automatically.
- **Risk Engine / Budget Optimizer** — kept the core rule-based scoring,
  extended to fold in AI severity and duplicate-report counts, and to
  break repair cost down by **NHAI vs State/Municipal** road authority.
- **New:** a road-authority classifier (approximate NHAI corridor
  geometry for Delhi-NCR) so every complaint and zone is tagged with
  which authority would actually pay for the repair.
- **New:** a real trained pothole-detection model (`backend/models/best.pt`)
  wired in with a 40% confidence validation gate, and a floating chat
  assistant that checks a travel route for reported issues.
- All five original modules' separate servers/ports were merged into
  **one FastAPI service** — much simpler to run for a demo.

## Project layout

```
backend/
  main.py                    FastAPI app — all endpoints
  modules/
    defect_detection.py      pothole detection (YOLO-ready + CV fallback) + severity scoring
    duplicate_check.py       geolocation-based duplicate detection
    road_classifier.py       NHAI vs State/Municipal heuristic classifier
    risk_engine.py           zone risk scoring
    budget_optimizer.py      budget-constrained repair prioritization
    store.py                 CSV-backed complaint store (+ auto-seeding)
  data/
    noida_complaints_300_seed.csv   original historical dataset (seed input)
    complaints.csv                  live unified store (generated on first run)
  requirements.txt

frontend/
  src/
    api.js                  fetch wrapper for the backend
    constants.js             shared categories / colors / formatters
    App.jsx                  routing + role switch + live alert banner
    components/
      TopNav.jsx / .css
      AlertBanner.jsx / .css
    pages/
      ReportIssue.jsx / .css   photo + GPS + AI Vision Analysis panel
      GisMap.jsx / .css        Leaflet map, severity + road-authority overlays
      Dashboard.jsx / .css     Priority Engine: budget slider, NHAI/State pie chart, ranked zone table
  package.json
```

## How to run

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The first run auto-seeds `data/complaints.csv` from the historical Noida
dataset (enriched with simulated severity/road-authority data so the risk
engine and dashboard have something real to show immediately). Visit
`http://localhost:8000/docs` for interactive API docs.

To wipe live data and re-seed: `POST http://localhost:8000/admin/reset-seed`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. It talks to the backend at the URL in
`frontend/.env` (`VITE_API_BASE_URL`, defaults to `http://localhost:8000`)
— change that if you deploy the backend elsewhere.

### 3. Try it

- **Report Issue** (citizen role): capture GPS, pick "Pothole / Road
  Damage", upload any road photo, submit — you'll see the AI Vision
  Analysis panel with a bounding box, confidence, and severity. Submit
  another photo near the same coordinates and category to see the
  duplicate-merge flow.
- **GIS Map**: all complaints plotted, colored by severity, filterable by
  category and road authority.
- **Priority Engine** (switch role to "Municipal / PWD Admin" in the top
  right): drag the budget slider and watch which zones get funded, the
  NHAI-vs-State repair cost pie chart, and the ranked priority table.

## Pothole detection model

A real trained YOLOv8 model (single class: `Pothole`) ships at
`backend/models/best.pt` and is used automatically once
`pip install -r requirements.txt` pulls in `ultralytics`/`torch`. If
those aren't installed (or the weights file is missing), detection
falls back to the built-in OpenCV heuristic so the pipeline still runs
— every response includes a `detector` field (`"yolov8-custom"` or
`"heuristic-cv"`) so you always know which path produced a result.

**Validation gate:** a Road Damage report is only stored if the model's
confidence is **≥ 40%**. Below that, `/report` returns
`{"status": "rejected", "message": "..."}` and nothing is written to the
complaint store — the photo is treated as not actually showing a
pothole. Adjust the threshold via `MIN_POTHOLE_CONFIDENCE` in
`modules/defect_detection.py`.

## CivicTwin Assistant (chatbot)

A floating chat widget (bottom-right) lets anyone ask things like:

> "from Sector 62 to Sector 18"
> "between 28.62,77.37 and 28.57,77.33"

It resolves each side to coordinates (Noida sector name lookup in
`modules/sectors.py`, or raw `lat,lon`), checks the straight-line path
between them for any stored complaint within ~350m (`modules/route_check.py`),
and replies with a plain-language summary — worst severity found, defect
type, distance from the route, and how many citizens flagged it. No LLM
call involved — it's a small deterministic parser (`modules/chat.py`)
matched to the one job this bot needs to do. Extend
`modules/sectors.py` with more sector coordinates if you need wider
coverage.

## Known simplifications (documented, not hidden)

- **Road authority classification** is a distance-to-known-corridor
  heuristic with a handful of hardcoded major Delhi-NCR highways — not a
  real GIS lookup against NHAI's road network. Good enough to demo the
  concept; swap in real shapefile data for production.
- **Non-pothole severity** (waterlogging, streetlight, waste) has no
  trained vision model behind it — it's scored from category risk priors
  with a small deterministic spread, clearly marked `detector:
  "category-prior"` in every response.
- **Storage is a CSV file**, not a database — fine for a hackathon demo,
  swap `modules/store.py` for real DB calls when you have a backend team
  and schema to integrate with.
