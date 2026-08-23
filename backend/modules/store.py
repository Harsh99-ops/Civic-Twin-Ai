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
