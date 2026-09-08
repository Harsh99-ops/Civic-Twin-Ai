"""City-wide aggregate stats over the live complaint store."""

from modules.store import load_all


def compute_stats() -> dict:
    rows = load_all()
    total = len(rows)
    by_category = {}
    by_severity = {}
    by_road_type = {}
    for r in rows:
        by_category[r["complaint_category"]] = by_category.get(r["complaint_category"], 0) + 1
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + 1
        by_road_type[r["road_type"]] = by_road_type.get(r["road_type"], 0) + 1

    critical_high = sum(1 for r in rows if r["severity"] in ("Critical", "High"))

    return {
        "total_complaints": total,
        "critical_or_high": critical_high,
        "by_category": by_category,
        "by_severity": by_severity,
        "by_road_type": by_road_type,
    }
