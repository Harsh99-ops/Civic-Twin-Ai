"""
CIVIC-TWIN AI — Sector Coordinate Lookup
=============================================
Maps common Noida sector names to approximate lat/lon, so the chat
assistant can answer "is there anything reported between Sector X and
Sector Y" without the user needing to know raw coordinates.

Coordinates below are approximate sector centroids compiled from public
geocoding sources — good enough for a ~city-block-scale route check, not
survey-accurate. Extend this table with more sectors as needed; the
lookup is intentionally just a plain dict so it's easy to edit.
"""

NOIDA_SECTORS = {
    "sector 1": (28.5859, 77.3096),
    "sector 2": (28.5851, 77.3153),
    "sector 3": (28.5885, 77.3121),
    "sector 4": (28.5837, 77.3230),
    "sector 5": (28.5799, 77.3160),
    "sector 6": (28.5814, 77.3236),
    "sector 8": (28.5793, 77.3252),
    "sector 12": (28.5895, 77.3271),
    "sector 15": (28.5843, 77.3306),
    "sector 16": (28.5793, 77.3272),
    "sector 18": (28.5708, 77.3272),
    "sector 19": (28.5765, 77.3247),
    "sector 20": (28.5757, 77.3183),
    "sector 22": (28.5852, 77.3196),
    "sector 26": (28.5761, 77.3311),
    "sector 27": (28.5751, 77.3281),
    "sector 29": (28.5825, 77.3364),
    "sector 33": (28.5980, 77.3140),
    "sector 34": (28.5951, 77.3162),
    "sector 37": (28.5825, 77.3441),
    "sector 41": (28.5628, 77.3305),
    "sector 44": (28.5586, 77.3277),
    "sector 50": (28.5735, 77.3477),
    "sector 51": (28.5799, 77.3489),
    "sector 52": (28.5771, 77.3502),
    "sector 53": (28.5850, 77.3459),
    "sector 61": (28.6103, 77.3617),
    "sector 62": (28.6200, 77.3700),
    "sector 63": (28.6285, 77.3769),
    "sector 66": (28.6055, 77.3761),
    "sector 71": (28.5928, 77.3541),
    "sector 76": (28.5661, 77.3573),
    "sector 78": (28.5614, 77.3847),
    "sector 100": (28.5487, 77.3648),
    "sector 104": (28.5401, 77.3736),
    "sector 110": (28.5348, 77.3841),
    "sector 122": (28.5648, 77.3949),
    "sector 125": (28.5455, 77.3927),
    "sector 126": (28.5395, 77.3947),
    "sector 128": (28.5303, 77.3801),
    "sector 135": (28.5188, 77.3653),
    "sector 137": (28.5000, 77.3948),
    "sector 142": (28.4975, 77.3760),
    "sector 143": (28.4922, 77.3820),
    "sector 150": (28.4700, 77.4200),
    "greater noida sector 1": (28.5720, 77.4329),
}


def resolve_sector(name: str):
    """Case/whitespace-insensitive lookup. Accepts 'Sector 62', 'sector62',
    'sec 62', etc. Returns (lat, lon) or None if unrecognized."""
    key = name.strip().lower().replace("sec ", "sector ").replace("sec.", "sector")
    key = key.replace("sector-", "sector ").replace("sector", "sector ")
    key = " ".join(key.split())  # collapse repeated spaces
    return NOIDA_SECTORS.get(key)
