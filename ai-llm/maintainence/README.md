# CIVIC-TWIN AI — Maintenance Prioritization & Budget Optimization

The final module: takes risk-scored zones (from Module 4) and a limited
repair budget, and decides exactly which problems get fixed first.

This is the module that turns "here's a list of risky potholes" into
"here's an actual, defensible repair plan a municipal officer could
approve tomorrow."

---

## IMPORTANT: this needs risk_engine.py

This module reuses the risk-scoring logic from Module 4. Copy
`risk_engine.py` (from the risk_prediction module) into this same
folder before running anything here.

---

## Step 1: Setup

```bash
pip install -r requirements.txt
```

Make sure you have in the same folder:
- `risk_engine.py` (copied from Module 4)
- `noida_complaints_300.csv` (your complaint data)
- `budget_optimizer.py` (this module)

---

## Step 2: Test it

```bash
python budget_optimizer.py
```

This runs with a test budget of ₹2,00,000 and prints something like:
```
Budget: ₹200,000
Spent: ₹185,000
Remaining: ₹15,000
Zones funded: 8 / 22
Risk addressed: 61.3%

FUNDED (in priority order):
  [Critical] Drainage / Waterlogging       cost=₹ 54,000  risk=82.3
  [High    ] Road Damage                   cost=₹ 16,200  risk=61.5
  ...

UNFUNDED (budget ran out): 14 zones
```

Try changing `TEST_BUDGET` at the bottom of `budget_optimizer.py` to see
how the funded list changes with more or less money — this is a great
thing to demo live to judges ("watch what happens if the city had
double the budget").

---

## Step 3: How the prioritization works

1. Estimate a repair cost for each zone, based on issue type (drainage
   repairs cost more than streetlight fixes) and scale (more complaints
   in a zone → assumed larger problem → somewhat higher cost)
2. Calculate "value per rupee" = risk score ÷ estimated cost — this finds
   the most efficient fixes, not just the most expensive-looking ones
3. Fund zones in order of best value-per-rupee until the budget runs out

This means a cheap-to-fix but genuinely dangerous zone will always beat
an expensive zone with only moderate risk — which is the right call for
limited public money.

You can tune `BASE_REPAIR_COST` in `budget_optimizer.py` with more
realistic numbers if your team has access to real municipal repair cost
data.

---

## Step 4: Run as an API

```bash
uvicorn api:app --port 8005
```

```
GET /prioritize?budget=200000&top_n=50
```

---

## You've now built all 5 AI/LLM modules

1. Defect Detection (computer vision)
2. Smart Complaint Analysis (LLM)
3. Duplicate Complaint Detection (embeddings)
4. Risk Prediction Engine (rule-based scoring)
5. Maintenance Prioritization & Budget Optimization (this one)

For your demo: the strongest story is showing the full pipeline
end-to-end — a photo comes in, gets analyzed, checked for duplicates,
folded into risk scoring, and finally shows up in a prioritized, budget-
aware repair plan. That's a genuinely complete system, not just five
disconnected scripts.
