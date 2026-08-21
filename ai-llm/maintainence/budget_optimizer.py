"""
CIVIC-TWIN AI — Maintenance Prioritization & Budget Optimization
=====================================================================
Takes risk-scored zones (from Module 4: risk_engine.py) and a limited
municipal budget, and decides WHICH zones actually get repair funding
first — maximizing risk reduction per rupee spent.

WHY GREEDY "BEST VALUE FIRST" INSTEAD OF SOMETHING FANCIER:
This is fundamentally a budget-constrained selection problem: many zones
need fixing, money is limited, and we want the most impact per rupee.
The greedy approach (fund highest risk-per-cost zones first, in order,
until money runs out) is simple, fast, and — importantly — easy to
explain and defend to a judge or municipal officer: "we fixed the
most dangerous, cheapest-to-address problems first." A more complex
optimal algorithm (dynamic programming / true 0-1 knapsack) could
squeeze out a slightly better combination in edge cases, but the
difference is rarely worth the loss of explainability for this use case.

This module NEEDS risk_engine.py (from Module 4) in the same folder,
since it reuses compute_zone_risk() to get risk-scored zones.
"""

import pandas as pd
from risk_engine import load_complaints, compute_zone_risk

# Estimated repair cost (in INR) per issue category. These are rough
# planning-level estimates — replace with real municipal cost data if
# your team has access to it. The relative ordering matters more than
# exact accuracy for a hackathon demo.
BASE_REPAIR_COST = {
    "Road Damage": 15000,
    "Drainage / Waterlogging": 50000,
    "Streetlight / Electrical": 5000,
    "Waste Management": 3000,
}
DEFAULT_REPAIR_COST = 10000  # for any category not listed above


def estimate_repair_cost(dominant_category: str, complaint_count: int) -> float:
    """
    Estimate repair cost for a zone based on its issue type and how many
    complaints it has (more complaints ≈ larger/more severe problem area,
    so cost scales up a bit, capped so it doesn't spiral unrealistically).
    """
    base_cost = BASE_REPAIR_COST.get(dominant_category, DEFAULT_REPAIR_COST)
    # Each additional complaint beyond the first adds 8% to cost, capped at +80%
    scale_multiplier = 1 + min((complaint_count - 1) * 0.08, 0.8)
    return round(base_cost * scale_multiplier, 0)


def prioritize_maintenance(zones_df: pd.DataFrame, budget: float) -> dict:
    """
    Given risk-scored zones and a total budget, decide which zones get
    funded, using a greedy best-value-per-rupee approach.

    Args:
        zones_df: DataFrame from risk_engine.compute_zone_risk() — must
                   have risk_score, dominant_category, complaint_count columns.
        budget: total money available (in INR) for this round of repairs.

    Returns:
        dict with funded zones, unfunded zones, and summary statistics.
    """
    df = zones_df.copy()
    df["estimated_cost"] = df.apply(
        lambda row: estimate_repair_cost(row["dominant_category"], row["complaint_count"]),
        axis=1,
    )
    # Value = risk addressed per rupee spent. This is the core ranking metric —
    # a zone with a high risk score but low cost is the most "efficient" fix.
    df["value_per_rupee"] = df["risk_score"] / df["estimated_cost"]
    df = df.sort_values("value_per_rupee", ascending=False).reset_index(drop=True)

    funded = []
    unfunded = []
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

    return {
        "funded_zones": funded,
        "unfunded_zones": unfunded,
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


def run_full_pipeline(csv_path: str, budget: float, top_n_zones: int = 50) -> dict:
    """
    Full pipeline: load complaints -> compute risk -> prioritize within budget.
    This is the convenience function most people will actually call.
    """
    df = load_complaints(csv_path)
    zones_df = compute_zone_risk(df).head(top_n_zones)
    return prioritize_maintenance(zones_df, budget)


if __name__ == "__main__":
    # Quick manual test — adjust the budget to see how many zones get funded
    TEST_BUDGET = 200000  # ₹2 lakh, just for demonstration

    result = run_full_pipeline("noida_complaints_300.csv", budget=TEST_BUDGET)

    print(f"Budget: ₹{TEST_BUDGET:,}")
    print(f"Spent: ₹{result['summary']['total_spent']:,.0f}")
    print(f"Remaining: ₹{result['summary']['remaining_budget']:,.0f}")
    print(f"Zones funded: {result['summary']['zones_funded']} / "
          f"{result['summary']['zones_funded'] + result['summary']['zones_unfunded']}")
    print(f"Risk addressed: {result['summary']['risk_addressed_percent']}%\n")

    print("FUNDED (in priority order):")
    for zone in result["funded_zones"]:
        print(f"  [{zone['risk_level']:8s}] {zone['dominant_category']:25s} "
              f"cost=₹{zone['estimated_cost']:>8,.0f}  risk={zone['risk_score']}")

    print(f"\nUNFUNDED (budget ran out): {len(result['unfunded_zones'])} zones")
