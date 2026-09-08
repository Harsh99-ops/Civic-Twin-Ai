"""
CIVIC-TWIN AI — Route Defect Check
======================================
Backs the chat assistant's core question: "I'm travelling from A to B —
is there anything reported on the way?"

A and B can each be a Noida sector name ("Sector 62") or raw
"lat,lon" coordinates. We treat the route as a straight line between the
two points (a reasonable approximation at city scale — this isn't a real
routing engine) and flag any stored complaint within ROUTE_BUFFER_KM of
that line.
"""

import re

from modules.store import load_all
from modules.sectors import resolve_sector
from modules.geo_utils import point_to_segment_km

ROUTE_BUFFER_KM = 0.35  # ~350m either side of the straight-line path

COORD_RE = re.compile(r"^\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*$")


def resolve_place(text: str):
    """Resolve a place string to (lat, lon, display_name), or None."""
    text = text.strip()
    m = COORD_RE.match(text)
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
        return lat, lon, f"({lat:.4f}, {lon:.4f})"
    coords = resolve_sector(text)
    if coords:
        return coords[0], coords[1], text.strip().title()
    return None


def check_route(origin: str, destination: str) -> dict:
    """
    Returns a dict describing whether any reported issues lie on the
    straight-line path between origin and destination.
    """
    o = resolve_place(origin)
    d = resolve_place(destination)

    if o is None or d is None:
        unresolved = origin if o is None else destination
        return {
            "resolved": False,
            "error": (
                f"I don't recognize \"{unresolved}\". Try a Noida sector name "
                "(e.g. \"Sector 62\") or coordinates like \"28.62,77.37\"."
            ),
        }

    lat1, lon1, name1 = o
    lat2, lon2, name2 = d

    rows = load_all()
    matches = []
    for r in rows:
        if r.get("status") == "Resolved":
            continue
        try:
            lat, lon = float(r["latitude"]), float(r["longitude"])
        except (ValueError, TypeError):
            continue
        dist = point_to_segment_km(lat, lon, lat1, lon1, lat2, lon2)
        if dist <= ROUTE_BUFFER_KM:
            matches.append({**r, "distance_from_route_m": round(dist * 1000, 1)})

    matches.sort(key=lambda m: (-{"Critical": 3, "High": 2, "Medium": 1, "Low": 0}.get(m["severity"], 0),
                                 m["distance_from_route_m"]))

    return {
        "resolved": True,
        "origin": {"name": name1, "lat": lat1, "lon": lon1},
        "destination": {"name": name2, "lat": lat2, "lon": lon2},
        "issues_found": len(matches),
        "matches": matches[:8],
    }
