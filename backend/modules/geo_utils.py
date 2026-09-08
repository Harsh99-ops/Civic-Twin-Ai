"""Shared geo-distance helpers used by duplicate_check, road_classifier,
and route_check so the math lives in exactly one place."""

import math


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def point_to_segment_km(lat, lon, lat1, lon1, lat2, lon2):
    """Approximate distance from a point to a line segment, in km, using
    an equirectangular flattening (fine at city scale)."""
    lat0 = math.radians((lat1 + lat2) / 2)
    kx = 111.32 * math.cos(lat0)
    ky = 110.57

    px, py = lon * kx, lat * ky
    x1, y1 = lon1 * kx, lat1 * ky
    x2, y2 = lon2 * kx, lat2 * ky

    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return haversine_km(lat, lon, lat1, lon1)

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = x1 + t * dx, y1 + t * dy
    return math.hypot(px - cx, py - cy)
