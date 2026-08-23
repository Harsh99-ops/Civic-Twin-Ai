"""
CIVIC-TWIN AI — Risk Prediction Engine
==========================================
Predicts which locations are at HIGH RISK of developing severe civic
issues, based on patterns in the live complaint store (patched from the
original module to read our unified CSV schema and add road-authority
and AI-severity signals into the score).

WHY RULE-BASED, NOT A TRAINED ML MODEL:
A trained model needs historical examples with known OUTCOMES. That kind
of labeled data doesn't exist here — so this uses transparent,
explainable scoring based on genuine risk signals in the complaint data:

  1. FREQUENCY — more reports in one zone = stronger evidence of a real,
     worsening problem.
  2. CATEGORY RISK WEIGHT — Road Damage / Drainage pose more physical
     danger than a Streetlight or Waste Management issue.
  3. AI SEVERITY — the average detected/estimated severity of complaints
     in the zone (from defect_detection's vision model or category priors).
  4. TREND (ACCELERATION) — a zone with recent complaints outpacing older
     ones suggests an actively worsening issue.
  5. REPORT COUNT — duplicate reports of the same defect (multiple
     citizens flagging the identical spot) push the zone's frequency
     signal up, since it's evidence more people are affected.
"""

import pandas as pd

from modules.store import load_all

CATEGORY_RISK_WEIGHT = {
    "Road Damage": 0.95,
    "Drainage / Waterlogging": 0.90,
    "Streetlight / Electrical": 0.55,
    "Waste Management": 0.40,
}
DEFAULT_CATEGORY_WEIGHT = 0.5

GRID_SIZE = 0.003  # ~300m


def load_complaints_df() -> pd.DataFrame:
    rows = load_all()
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)
    df["severity_score"] = pd.to_numeric(df["severity_score"], errors="coerce").fillna(0)
    df["report_count"] = pd.to_numeric(df["report_count"], errors="coerce").fillna(1).astype(int)
    df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    df = df.dropna(subset=["date_time"])
    return df


def assign_zones(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["zone_lat"] = (df["latitude"] / GRID_SIZE).round() * GRID_SIZE
    df["zone_lon"] = (df["longitude"] / GRID_SIZE).round() * GRID_SIZE
    df["zone_id"] = df["zone_lat"].astype(str) + "_" + df["zone_lon"].astype(str)
    return df


def compute_zone_risk(df: pd.DataFrame, recent_days: int = 14) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = assign_zones(df)
    latest_date = df["date_time"].max()
    recent_cutoff = latest_date - pd.Timedelta(days=recent_days)

    zone_rows = []
    for zone_id, zone_df in df.groupby("zone_id"):
        # "effective" count folds in duplicate reports (report_count) so a
        # single defect that many citizens independently flagged counts
        # for more than a single lone report.
        effective_count = int(zone_df["report_count"].sum())
        complaint_count = len(zone_df)

        category_weights = zone_df["complaint_category"].map(
            lambda c: CATEGORY_RISK_WEIGHT.get(c, DEFAULT_CATEGORY_WEIGHT)
        )
        avg_category_weight = category_weights.mean()
        avg_ai_severity = zone_df["severity_score"].mean() / 100  # normalize 0-1

        recent_count = (zone_df["date_time"] >= recent_cutoff).sum()
        older_count = complaint_count - recent_count
        if older_count == 0:
            trend_multiplier = 1.3 if recent_count > 0 else 1.0
        else:
            trend_multiplier = min(1.0 + (recent_count / older_count) * 0.3, 1.5)

        frequency_score = min(effective_count / 8, 1.0)

        raw_score = (
            frequency_score * 0.35 + avg_category_weight * 0.35 + avg_ai_severity * 0.30
        ) * trend_multiplier * 100
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
        road_type = zone_df["road_type"].mode().iloc[0] if "road_type" in zone_df else "State/Municipal"
        road_name = zone_df["road_name"].mode().iloc[0] if "road_name" in zone_df else ""

        zone_rows.append({
            "zone_id": zone_id,
            "latitude": round(zone_df["zone_lat"].iloc[0], 5),
            "longitude": round(zone_df["zone_lon"].iloc[0], 5),
            "complaint_count": int(complaint_count),
            "report_count": effective_count,
            "recent_complaint_count": int(recent_count),
            "dominant_category": dominant_category,
            "avg_ai_severity": round(avg_ai_severity * 100, 1),
            "road_type": road_type,
            "road_name": road_name,
            "risk_score": risk_score,
            "risk_level": risk_level,
        })

    result_df = pd.DataFrame(zone_rows).sort_values("risk_score", ascending=False).reset_index(drop=True)
    result_df.insert(0, "priority_rank", result_df.index + 1)
    return result_df


def predict_risk(top_n: int = 20) -> list:
    df = load_complaints_df()
    zone_risk_df = compute_zone_risk(df)
    if zone_risk_df.empty:
        return []
    return zone_risk_df.head(top_n).to_dict(orient="records")
