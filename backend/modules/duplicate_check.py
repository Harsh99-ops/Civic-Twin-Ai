"""
CIVIC-TWIN AI — Duplicate Complaint Detection (geolocation-based)
======================================================================
The original module compared complaint TEXT with Gemini embeddings.
This pipeline never collects complaint text — citizens submit a photo,
GPS coordinates, and an issue category — so text similarity isn't
available (and doesn't need to be: two reports of a pothole at the same
spot are obviously the same pothole).

Instead, a new report is treated as a duplicate of an existing OPEN
complaint if it's the same category AND within DUPLICATE_RADIUS_KM of
it. This is simpler, needs no external API/key, and matches the actual
signal we have: two people photographing the same defect will always be
standing close to it.

When a duplicate is found, we don't create a second complaint — we
increment the existing one's `report_count` (how many citizens have
independently flagged it), which the risk engine uses as a genuine
signal that the problem is affecting more people and deserves higher
priority.
"""

import math

DUPLICATE_RADIUS_KM = 0.12  # ~120 meters


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_duplicate(records: list, lat: float, lon: float, category: str):
    """
    Look for an existing OPEN complaint of the same category within
    DUPLICATE_RADIUS_KM of (lat, lon).

    Args:
        records: list of complaint dicts (as stored in the CSV store),
                 each with latitude, longitude, complaint_category, status.
        lat, lon: coordinates of the incoming report.
        category: the incoming report's issue category.

    Returns:
        The matching record dict (mutated in place is NOT done here —
        caller is responsible for updating the store), or None.
    """
    best = None
    best_dist = float("inf")
    for rec in records:
        if rec.get("status") == "Resolved":
            continue
        if rec.get("complaint_category") != category:
            continue
        d = _haversine_km(lat, lon, float(rec["latitude"]), float(rec["longitude"]))
        if d <= DUPLICATE_RADIUS_KM and d < best_dist:
            best = rec
            best_dist = d
    return best, (None if best is None else round(best_dist * 1000, 1))
