"""
CIVIC-TWIN AI — Complaint Store
====================================
A simple CSV-backed store for the unified complaint schema. Every
complaint — whether seeded from historical data or reported live through
POST /report — lives in one file, which is exactly what the risk engine
and budget optimizer read from.

Swap this for a real database in production; the read/write functions
below are the only place that would need to change.
"""

import csv
import os
import random
from datetime import datetime, timedelta

from modules.road_classifier import classify_road
from modules.defect_detection import severity_for_category

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CSV_PATH = os.path.join(DATA_DIR, "complaints.csv")
SEED_CSV_PATH = os.path.join(DATA_DIR, "noida_complaints_300_seed.csv")

FIELDNAMES = [
    "complaint_id", "latitude", "longitude", "complaint_category",
    "defect_type", "ai_confidence", "severity", "severity_score",
    "road_type", "road_name", "date_time", "report_count", "status", "detector",
]


def _ensure_csv():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        _seed()


def _seed():
    """Build the initial complaints.csv from the historical Noida dataset,
    enriching each row with the fields the new pipeline expects (defect
    type, severity, road authority) so risk/budget scoring has real data
    to work with on first run."""
    rows = []
    if os.path.exists(SEED_CSV_PATH):
        with open(SEED_CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                cid = raw["complaint_id"]
                lat, lon = float(raw["latitude"]), float(raw["longitude"])
                category = raw["complaint_category"]
                road = classify_road(lat, lon)
                sev = severity_for_category(category, cid)
                defect_type = {
                    "Road Damage": "pothole",
                    "Drainage / Waterlogging": "waterlogging",
                    "Streetlight / Electrical": "streetlight-fault",
                    "Waste Management": "waste-pileup",
                }.get(category, category.lower())
                rng = random.Random(cid)
                rows.append({
                    "complaint_id": cid,
                    "latitude": lat,
                    "longitude": lon,
                    "complaint_category": category,
                    "defect_type": defect_type,
                    "ai_confidence": round(rng.uniform(0.6, 0.96), 3) if category == "Road Damage" else "",
                    "severity": sev["severity"],
                    "severity_score": sev["severity_score"],
                    "road_type": road["road_type"],
                    "road_name": road["road_name"],
                    "date_time": raw["date_time"],
                    "report_count": rng.choice([1, 1, 1, 1, 2, 2, 3]),
                    "status": "Open",
                    "detector": "seed-data",
                })
    write_all(rows)


def load_all() -> list:
    _ensure_csv()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_all(rows: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


def next_complaint_id(rows: list) -> str:
    max_n = 0
    for r in rows:
        cid = r.get("complaint_id", "")
        digits = "".join(ch for ch in cid.split("-")[-1] if ch.isdigit())
        if digits:
            max_n = max(max_n, int(digits))
    return f"CT-{max_n + 1:04d}"


def append_complaint(record: dict):
    rows = load_all()
    rows.append(record)
    write_all(rows)
    return record


def update_complaint(complaint_id: str, updates: dict):
    rows = load_all()
    updated = None
    for r in rows:
        if r["complaint_id"] == complaint_id:
            r.update(updates)
            updated = r
            break
    write_all(rows)
    return updated


def reset_to_seed():
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)
    _seed()


SEVERITY_RANK = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def search_complaints(category=None, road_type=None, min_severity=None,
                       near_lat=None, near_lon=None, radius_km=1.5, limit=25) -> list:
    """Flexible filter over the live store — backs the chat assistant's
    search_complaints tool as well as any future filtered views."""
    from modules.geo_utils import haversine_km

    rows = load_all()
    out = []
    for r in rows:
        if r.get("status") == "Resolved":
            continue
        if category and r.get("complaint_category") != category:
            continue
        if road_type and r.get("road_type") != road_type:
            continue
        if min_severity and SEVERITY_RANK.get(r.get("severity"), 0) < SEVERITY_RANK.get(min_severity, 0):
            continue
        if near_lat is not None and near_lon is not None:
            try:
                d = haversine_km(near_lat, near_lon, float(r["latitude"]), float(r["longitude"]))
            except (ValueError, TypeError):
                continue
            if d > radius_km:
                continue
            r = {**r, "distance_km": round(d, 3)}
        out.append(r)

    if near_lat is not None and near_lon is not None:
        out.sort(key=lambda r: r.get("distance_km", 0))
    else:
        out.sort(key=lambda r: SEVERITY_RANK.get(r.get("severity"), 0), reverse=True)

    return out[:limit]
