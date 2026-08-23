"""
CIVIC-TWIN AI — Maintenance Prioritization & Budget Optimization
=====================================================================
Takes risk-scored zones and a limited municipal budget, and decides
WHICH zones actually get repair funding first — maximizing risk
reduction per rupee spent (greedy best-value-first, same approach as
the original module: simple, fast, and easy to defend — "we fixed the
most dangerous, cheapest-to-address problems first").

Extended from the original to also report a cost breakdown by road
authority (NHAI vs State/Municipal), since who pays for a repair
depends on who owns the road.
"""

from modules.risk_engine import load_complaints_df, compute_zone_risk

BASE_REPAIR_COST = {
    "Road Damage": 15000,
    "Drainage / Waterlogging": 50000,
    "Streetlight / Electrical": 5000,
    "Waste Management": 3000,
}
DEFAULT_REPAIR_COST = 10000


def estimate_repair_cost(dominant_category: str, complaint_count: int) -> float:
    base_cost = BASE_REPAIR_COST.get(dominant_category, DEFAULT_REPAIR_COST)
    scale_multiplier = 1 + min((complaint_count - 1) * 0.08, 0.8)
    return round(base_cost * scale_multiplier, 0)


def prioritize_maintenance(zones_df, budget: float) -> dict:
    df = zones_df.copy()
    df["estimated_cost"] = df.apply(
        lambda row: estimate_repair_cost(row["dominant_category"], row["complaint_count"]),
        axis=1,
    )
    df["value_per_rupee"] = df["risk_score"] / df["estimated_cost"]
    df = df.sort_values("value_per_rupee", ascending=False).reset_index(drop=True)

    funded, unfunded = [], []
    remaining_budget = budget

    for _, zone in df.iterrows():
        cost = zone["estimated_cost"]
        if cost <= remaining_budget:
            funded.append(zone.to_dict())
            remaining_budget -= cost
        else:
            unfunded.append(zone.to_dict())

    total_spent = budget - remaining_budget
    total_risk_addressed = sum(z["risk_score"] for z in funded)
    total_risk_all_zones = df["risk_score"].sum()

    road_cost_breakdown = {}
    for _, zone in df.iterrows():
        rt = zone.get("road_type", "State/Municipal")
        road_cost_breakdown[rt] = road_cost_breakdown.get(rt, 0) + zone["estimated_cost"]

    return {
        "funded_zones": funded,
        "unfunded_zones": unfunded,
        "road_cost_breakdown": {k: round(v, 0) for k, v in road_cost_breakdown.items()},
        "summary": {
            "total_budget": budget,
            "total_spent": round(total_spent, 0),
            "remaining_budget": round(remaining_budget, 0),
            "zones_funded": len(funded),
            "zones_unfunded": len(unfunded),
            "risk_addressed_percent": round(
                (total_risk_addressed / total_risk_all_zones * 100) if total_risk_all_zones > 0 else 0, 1
            ),
        },
    }


def run_full_pipeline(budget: float, top_n_zones: int = 50) -> dict:
    df = load_complaints_df()
    zones_df = compute_zone_risk(df).head(top_n_zones)
    if zones_df.empty:
        return {
            "funded_zones": [], "unfunded_zones": [], "road_cost_breakdown": {},
            "summary": {"total_budget": budget, "total_spent": 0, "remaining_budget": budget,
                        "zones_funded": 0, "zones_unfunded": 0, "risk_addressed_percent": 0},
        }
    return prioritize_maintenance(zones_df, budget)
