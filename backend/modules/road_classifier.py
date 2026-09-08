"""
CIVIC-TWIN AI — Road Authority Classifier
=============================================
Given a lat/lon in the Delhi-NCR region, decide whether the nearest road
is under NHAI (National Highways Authority of India) or a State/Municipal
authority (PWD, YEIDA, MCD, GMDA etc).

WHY THIS IS A HEURISTIC, NOT A REAL GIS LOOKUP:
A production system would query real road-network shapefiles (e.g. from
the NHAI GIS portal or OpenStreetMap's `ref=NH*` tags via the Overpass
API) and snap each complaint to the nearest tagged way. That needs a
network call / a large geodata file we don't have bundled here.

Instead, this approximates the small number of major NHAI corridors that
run through Delhi-NCR as simple polylines, and classifies a point as
"NHAI" if it falls within NHAI_BUFFER_KM of one of them. Everything else
is assumed to be a State/Municipal road, which is a reasonable default
since NHAI's network is a thin, sparse set of corridors compared to the
dense city road grid around them.

Replace the coordinate lists below with real geometry if you have access
to it — the classify_road() interface will stay the same.
"""

from modules.geo_utils import point_to_segment_km

NHAI_BUFFER_KM = 1.0  # how close a point must be to a corridor to count as "on" it

# Rough polylines (lat, lon) for major National Highway corridors through
# Delhi-NCR. Coordinates are approximate waypoints, good enough to
# classify nearby complaints for a demo — not survey-accurate.
NHAI_CORRIDORS = [
    {
        "name": "NH-9 (Delhi–Meerut Expressway)",
        "points": [(28.6692, 77.4538), (28.6430, 77.4120), (28.6129, 77.3910), (28.5921, 77.3560)],
    },
    {
        "name": "NH-48 (Delhi–Gurugram–Jaipur Expressway)",
        "points": [(28.5245, 77.1855), (28.4744, 77.0993), (28.4089, 77.0378), (28.3670, 76.9670)],
    },
    {
        "name": "NH-44 (GT Karnal Road / Panipat–Delhi)",
        "points": [(28.7192, 77.1025), (28.6820, 77.1440), (28.6448, 77.1650), (28.6139, 77.2090)],
    },
    {
        "name": "NH-19 (Delhi–Agra / Mathura Road)",
        "points": [(28.5580, 77.2790), (28.4920, 77.2990), (28.4020, 77.3160), (28.3200, 77.3350)],
    },
]

# Named State / Development-Authority expressways — used only to enrich
# the "road_name" shown in the UI when a point clearly sits on one of
# these, even though they're classified as State roads either way.
STATE_CORRIDORS = [
    {
        "name": "Noida–Greater Noida Expressway (State / YEIDA)",
        "points": [(28.5730, 77.3260), (28.5230, 77.3830), (28.4700, 77.4390), (28.4650, 77.5030)],
    },
    {
        "name": "DND Flyway (State / NOIDA Authority)",
        "points": [(28.6300, 77.2830), (28.5940, 77.3050), (28.5680, 77.3160)],
    },
    {
        "name": "Yamuna Expressway (State / YEIDA)",
        "points": [(28.4650, 77.5030), (28.3670, 77.5860), (28.2500, 77.6900)],
    },
    {
        "name": "MG Road, Gurugram (State / GMDA)",
        "points": [(28.4790, 77.0720), (28.4600, 77.0870), (28.4420, 77.0990)],
    },
    {
        "name": "Ring Road, Delhi (State / MCD-PWD)",
        "points": [(28.6100, 77.2500), (28.5800, 77.2350), (28.5600, 77.2450), (28.5900, 77.2650)],
    },
]

DEFAULT_ROAD_NAME = "Local / Municipal Road"


def _nearest_corridor(lat, lon, corridors):
    best_name, best_dist = None, float("inf")
    for corridor in corridors:
        pts = corridor["points"]
        for i in range(len(pts) - 1):
            (la1, lo1), (la2, lo2) = pts[i], pts[i + 1]
            d = point_to_segment_km(lat, lon, la1, lo1, la2, lo2)
            if d < best_dist:
                best_dist = d
                best_name = corridor["name"]
    return best_name, best_dist


def classify_road(lat: float, lon: float) -> dict:
    """
    Classify the road authority nearest to a given point.

    Returns:
        dict with 'road_type' ("NHAI" or "State/Municipal"), 'road_name',
        and 'distance_km' to the matched corridor (None if defaulted).
    """
    nhai_name, nhai_dist = _nearest_corridor(lat, lon, NHAI_CORRIDORS)
    if nhai_dist <= NHAI_BUFFER_KM:
        return {"road_type": "NHAI", "road_name": nhai_name, "distance_km": round(nhai_dist, 3)}

    state_name, state_dist = _nearest_corridor(lat, lon, STATE_CORRIDORS)
    if state_dist <= NHAI_BUFFER_KM:
        return {"road_type": "State/Municipal", "road_name": state_name, "distance_km": round(state_dist, 3)}

    return {"road_type": "State/Municipal", "road_name": DEFAULT_ROAD_NAME, "distance_km": None}
