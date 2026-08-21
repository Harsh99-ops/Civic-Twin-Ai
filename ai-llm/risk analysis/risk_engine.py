"""
CIVIC-TWIN AI — Risk Prediction Engine
==========================================
Predicts which locations are at HIGH RISK of developing severe civic
issues, based on patterns in historical complaint data.

WHY RULE-BASED, NOT A TRAINED ML MODEL:
A trained model needs historical examples with known OUTCOMES (e.g. "this
pothole was reported, ignored, and caused an accident 2 months later").
That kind of labeled outcome data essentially doesn't exist for a
hackathon project — collecting it would take years of real municipal
tracking. Building a "trained model" without real outcome labels would
just be fake statistics dressed up as ML.

Instead, this uses transparent, explainable scoring based on genuine
risk signals from complaint patterns:
  1. COMPLAINT FREQUENCY — more reports in one area = more evidence of a
     real, worsening problem (not a one-off).
  2. ISSUE SEVERITY WEIGHT — a road damage/drainage cluster is inherently
     more dangerous than a streetlight cluster.
  3. TREND (ACCELERATION) — a zone getting MORE complaints recently
     (vs. earlier) suggests the issue is actively getting worse.

This approach is defensible: you can explain exactly why any location
got its risk score, which matters far more for a hackathon demo (and for
real trust from a municipal officer) than an opaque ML score would.

INPUT DATA EXPECTED (matches your noida_complaints_300.csv):
    complaint_id, latitude, longitude, complaint_category, date_time
"""

import pandas as pd
import numpy as np
from datetime import datetime

# How risky each issue category is, independent of frequency.
# Tune these based on real-world judgment — e.g. road damage and
# waterlogging pose more physical danger than a broken streetlight.
CATEGORY_RISK_WEIGHT = {
    "Road Damage": 0.95,
    "Drainage / Waterlogging": 0.90,
    "Streetlight / Electrical": 0.55,
    "Waste Management": 0.40,
}
DEFAULT_CATEGORY_WEIGHT = 0.5  # for any category not listed above

# Grid size for clustering nearby complaints into the same "zone".
# ~0.003 degrees latitude is roughly 300 meters — complaints within this
# distance of each other get grouped as the same location/issue.
GRID_SIZE = 0.003


def load_complaints(csv_path: str) -> pd.DataFrame:
    """Load complaint data from CSV, matching your noida_complaints_300.csv schema."""
    df = pd.read_csv(csv_path)
    df["date_time"] = pd.to_datetime(df["date_time"])
    return df


def assign_zones(df: pd.DataFrame) -> pd.DataFrame:
    """
    Group nearby complaints into the same 'zone' by snapping lat/lon to a grid.
    This is a simple, fast, beginner-friendly alternative to more complex
    geographic clustering algorithms (like DBSCAN) — good enough for a
    hackathon and easy to explain to judges.
    """
    df = df.copy()
    df["zone_lat"] = (df["latitude"] / GRID_SIZE).round() * GRID_SIZE
    df["zone_lon"] = (df["longitude"] / GRID_SIZE).round() * GRID_SIZE
    df["zone_id"] = df["zone_lat"].astype(str) + "_" + df["zone_lon"].astype(str)
    return df


def compute_zone_risk(df: pd.DataFrame, recent_days: int = 14) -> pd.DataFrame:
    """
    Compute a risk score (0-100) for each geographic zone.

    Args:
        df: complaint dataframe (after assign_zones has been applied)
        recent_days: complaints within this many days of the most recent
                     complaint in the dataset count as "recent" for trend analysis

    Returns:
        DataFrame with one row per zone, sorted by risk score descending.
    """
    df = assign_zones(df)
    latest_date = df["date_time"].max()
    recent_cutoff = latest_date - pd.Timedelta(days=recent_days)

    zone_rows = []
    for zone_id, zone_df in df.groupby("zone_id"):
        complaint_count = len(zone_df)

        # Average category risk weight for complaints in this zone
        category_weights = zone_df["complaint_category"].map(
            lambda c: CATEGORY_RISK_WEIGHT.get(c, DEFAULT_CATEGORY_WEIGHT)
        )
        avg_category_weight = category_weights.mean()

        # Trend: how many of this zone's complaints happened recently vs earlier
        recent_count = (zone_df["date_time"] >= recent_cutoff).sum()
        older_count = complaint_count - recent_count
        # Acceleration ratio: >1 means complaints are speeding up, <1 means slowing
        if older_count == 0:
            trend_multiplier = 1.3 if recent_count > 0 else 1.0
        else:
            trend_multiplier = min(1.0 + (recent_count / older_count) * 0.3, 1.5)

        # Frequency score: more complaints = higher risk, but with diminishing
        # returns (a zone with 20 complaints isn't 20x riskier than 1 complaint,
        # it's clearly bad but caps out)
        frequency_score = min(complaint_count / 8, 1.0)  # caps at 8+ complaints

        # Combine into final 0-100 score
        raw_score = (frequency_score * 0.5 + avg_category_weight * 0.5) * trend_multiplier * 100
        risk_score = round(min(raw_score, 100), 1)

        if risk_score >= 75:
            risk_level = "Critical"
        elif risk_score >= 50:
            risk_level = "High"
        elif risk_score >= 25:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        dominant_category = zone_df["complaint_category"].mode().iloc[0]

        zone_rows.append({
            "zone_id": zone_id,
            "latitude": round(zone_df["zone_lat"].iloc[0], 5),
            "longitude": round(zone_df["zone_lon"].iloc[0], 5),
            "complaint_count": int(complaint_count),
            "recent_complaint_count": int(recent_count),
            "dominant_category": dominant_category,
            "risk_score": risk_score,
            "risk_level": risk_level,
        })

    result_df = pd.DataFrame(zone_rows).sort_values("risk_score", ascending=False).reset_index(drop=True)
    return result_df


def predict_risk(csv_path: str, top_n: int = 20) -> list:
    """
    Full pipeline: load data, compute zone risk, return top N riskiest zones
    as a list of dicts (ready for JSON/API output).
    """
    df = load_complaints(csv_path)
    zone_risk_df = compute_zone_risk(df)
    return zone_risk_df.head(top_n).to_dict(orient="records")


if __name__ == "__main__":
    # Quick manual test — update this path to wherever your CSV actually is
    results = predict_risk("noida_complaints_300.csv", top_n=10)
    print(f"Top {len(results)} highest-risk zones:\n")
    for zone in results:
        print(f"  [{zone['risk_level']:8s}] score={zone['risk_score']:5.1f}  "
              f"({zone['latitude']}, {zone['longitude']})  "
              f"{zone['complaint_count']} complaints, mostly {zone['dominant_category']}")
