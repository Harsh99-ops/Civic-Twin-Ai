"""
CIVIC-TWIN AI — Maintenance Prioritization API
====================================================
HOW TO RUN:
    uvicorn api:app --port 8005

ENDPOINTS:
    GET /prioritize?budget=200000&top_n=50
        — runs the full pipeline (load complaints -> risk score -> prioritize)
          using the default CSV, for a given budget.
"""

from fastapi import FastAPI, HTTPException
import os
from budget_optimizer import run_full_pipeline

app = FastAPI(title="CIVIC-TWIN AI — Maintenance Prioritization Service")

DEFAULT_CSV_PATH = os.environ.get("COMPLAINTS_CSV", "noida_complaints_300.csv")


@app.get("/")
def health_check():
    return {"status": "ok", "service": "civic-twin-budget-optimization"}


@app.get("/prioritize")
def prioritize(budget: float, top_n: int = 50):
    """
    Given a budget (in INR), return which zones get funded first and
    which don't, ranked by risk-reduction-per-rupee.
    """
    try:
        result = run_full_pipeline(DEFAULT_CSV_PATH, budget=budget, top_n_zones=top_n)
        return result
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Default complaints CSV not found at '{DEFAULT_CSV_PATH}'. "
                   f"Set the COMPLAINTS_CSV environment variable to the correct path."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prioritization failed: {str(e)}")
