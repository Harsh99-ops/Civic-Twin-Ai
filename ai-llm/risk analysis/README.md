# CIVIC-TWIN AI — Risk Prediction Engine

Predicts which locations are at high risk of developing severe civic
issues, based on patterns in your complaint data (frequency, issue type,
and whether complaints are accelerating recently).

---

## Why this isn't a "trained ML model"

A real trained prediction model needs historical examples where we KNOW
the outcome — e.g. "this pothole was reported and 2 months later caused
an accident." That kind of labeled data doesn't exist for a hackathon
(or realistically, for most real cities either — it would take years of
tracking to build).

Instead, this uses clear, explainable rules based on genuine risk
signals. This is actually a strength for your demo: when a judge asks
"how does this predict risk?", you can explain the exact logic, instead
of pointing at a black box.

---

## Step 1: Get your data ready

This expects a CSV with these columns (matches your noida_complaints_300.csv):
```
complaint_id, latitude, longitude, complaint_category, date_time
```

Put `noida_complaints_300.csv` in the same folder as `risk_engine.py`,
or update the path when calling `predict_risk()`.

---

## Step 2: Install and test

```bash
pip install -r requirements.txt
python risk_engine.py
```

This prints the top 10 highest-risk zones found in your data, something like:
```
Top 10 highest-risk zones:

  [Critical] score= 82.3  (28.577, 77.391)  6 complaints, mostly Drainage / Waterlogging
  [High    ] score= 61.5  (28.590, 77.368)  4 complaints, mostly Streetlight / Electrical
  ...
```

---

## Step 3: How the scoring works

Each geographic "zone" (complaints within ~300m of each other) gets scored on:

1. **Frequency** — more complaints in one zone = stronger evidence of a
   real problem (capped so it doesn't spiral unrealistically high)
2. **Category risk weight** — Road Damage and Drainage/Waterlogging score
   higher than Streetlight or Waste Management, since they pose more
   physical danger
3. **Trend/acceleration** — if a zone's complaints are increasingly recent
   (vs. spread evenly over time), that boosts its score — an accelerating
   problem is more urgent than a steady trickle

All three combine into a 0-100 score, then a Low/Medium/High/Critical label.

You can tune `CATEGORY_RISK_WEIGHT` and `GRID_SIZE` in `risk_engine.py`
based on what makes sense for your actual data and city.

---

## Step 4: Run as an API

```bash
uvicorn api:app --port 8004
```

```
GET /risk-zones?top_n=20
```
Returns the highest-risk zones using the default CSV.

```
POST /risk-zones/upload
```
Upload a fresh CSV (e.g. your backend's live complaint export) and get
risk zones computed on the spot.

---

## What's next

This is Module 4 of 5. Last one: **Maintenance Prioritization / Budget
Optimization** — takes these risk scores and decides what actually gets
fixed first given a limited budget.
