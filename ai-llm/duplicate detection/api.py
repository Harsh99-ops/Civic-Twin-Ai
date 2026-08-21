"""
CIVIC-TWIN AI — Duplicate Detection API
============================================
HOW TO RUN:
    uvicorn api:app --port 8003

ENDPOINTS:
    POST /complaints        — register a new complaint into the store
    POST /check-duplicate   — check if text is a likely duplicate
    GET  /complaints        — list all stored complaints (for debugging)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from duplicate_detector import ComplaintStore

app = FastAPI(title="CIVIC-TWIN AI — Duplicate Detection Service")

# One shared store for the life of this server process.
store = ComplaintStore()


class ComplaintInput(BaseModel):
    text: str
    lat: Optional[float] = None
    lon: Optional[float] = None


@app.get("/")
def health_check():
    return {"status": "ok", "service": "civic-twin-duplicate-detection", "complaints_stored": len(store.complaints)}


@app.post("/complaints")
def add_complaint(complaint: ComplaintInput):
    """Register a new complaint into the store (call this for every NEW complaint that passes the duplicate check)."""
    try:
        result = store.add(complaint.text, complaint.lat, complaint.lon)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add complaint: {str(e)}")


@app.post("/check-duplicate")
def check_duplicate(complaint: ComplaintInput):
    """Check if this complaint text is a likely duplicate of an existing one."""
    try:
        result = store.check_duplicate(complaint.text, complaint.lat, complaint.lon)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Duplicate check failed: {str(e)}")


@app.get("/complaints")
def list_complaints():
    """List all complaints currently in the store (debugging helper)."""
    return [{"id": c["id"], "text": c["text"], "lat": c["lat"], "lon": c["lon"]} for c in store.complaints]

"""
CIVIC-TWIN AI — Duplicate Complaint Detection
=================================================
Detects when a new complaint is likely reporting the SAME issue as an
existing complaint, even if worded completely differently.

HOW IT WORKS:
1. Convert complaint text into an "embedding" — a list of numbers that
   captures the MEANING of the text (using Gemini's embedding model).
2. Compare the new complaint's embedding to existing complaints' embeddings
   using cosine similarity (a number from -1 to 1, where 1 = identical
   meaning).
3. Optionally factor in location proximity too — two complaints about
   "a pothole" that are also 20 meters apart are much more likely to be
   duplicates than two similar complaints 5km apart.
4. If similarity is above a threshold, flag as a likely duplicate.

WHY THIS BEATS KEYWORD MATCHING:
"Big pothole near metro station" and "road cavity close to the metro"
share almost no exact words, but mean the same thing. Embeddings capture
that; keyword matching would completely miss it.

SETUP:
Same as complaint_analysis module — needs GEMINI_API_KEY set as an
environment variable before use.
"""

import os
import math
from google import genai
from google.genai import types
import numpy as np

API_KEY = os.environ.get("GEMINI_API_KEY")
_client = genai.Client(api_key=API_KEY) if API_KEY else None

EMBEDDING_MODEL = "gemini-embedding-001"

# How similar two complaints' meanings need to be (0 to 1) to count as
# a likely duplicate. 0.85 is a reasonably strict starting point —
# tune this based on real testing with your own complaint examples.
SIMILARITY_THRESHOLD = 0.85

# How close two complaints need to be geographically (in kilometers) to
# even be considered for duplicate matching. Complaints further apart than
# this are never flagged as duplicates, regardless of text similarity —
# a similar-sounding complaint on the other side of the city is a
# coincidence, not a duplicate.
MAX_DISTANCE_KM = 0.5  # 500 meters


def get_embedding(text: str) -> np.ndarray:
    """
    Convert text into an embedding vector using Gemini.

    Returns:
        A numpy array of numbers representing the text's meaning.
    """
    if not _client:
        raise ValueError(
            "GEMINI_API_KEY is not set. Set it as an environment variable "
            "before calling this function."
        )

    result = _client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
    )
    return np.array(result.embeddings[0].values)


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Measure how similar two embedding vectors are.
    Returns a value from -1 (opposite meaning) to 1 (identical meaning).
    """
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance in kilometers between two lat/lon points on Earth.
    Standard formula for geographic distance — used to check if two
    complaints are physically close enough to plausibly be duplicates.
    """
    R = 6371  # Earth's radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class ComplaintStore:
    """
    A simple in-memory store of existing complaints and their embeddings.

    NOTE FOR PRODUCTION: this resets every time the server restarts. In the
    real system, your backend teammate's database is the actual source of
    truth for complaints — this in-memory store is here so this AI module
    can be developed and tested independently. When wiring into the real
    backend, replace this with calls to their database instead.
    """

    def __init__(self):
        self.complaints = []  # list of dicts: id, text, embedding, lat, lon
        self._next_id = 1

    def add(self, text: str, lat: float = None, lon: float = None) -> dict:
        """Add a new complaint to the store and return its record."""
        embedding = get_embedding(text)
        record = {
            "id": self._next_id,
            "text": text,
            "embedding": embedding,
            "lat": lat,
            "lon": lon,
        }
        self.complaints.append(record)
        self._next_id += 1
        return {"id": record["id"], "text": record["text"], "lat": lat, "lon": lon}

    def check_duplicate(self, text: str, lat: float = None, lon: float = None) -> dict:
        """
        Check if a new complaint is a likely duplicate of an existing one.

        Returns:
            dict with is_duplicate, and if True, the matched complaint's
            id, text, and similarity score.
        """
        if not self.complaints:
            return {"is_duplicate": False, "matched_complaint": None, "similarity_score": None}

        new_embedding = get_embedding(text)

        best_match = None
        best_score = -1.0

        for existing in self.complaints:
            # If both complaints have location data, skip ones too far away —
            # saves us from flagging coincidental text similarity as a duplicate.
            if lat is not None and lon is not None and existing["lat"] is not None and existing["lon"] is not None:
                distance = haversine_distance_km(lat, lon, existing["lat"], existing["lon"])
                if distance > MAX_DISTANCE_KM:
                    continue

            score = cosine_similarity(new_embedding, existing["embedding"])
            if score > best_score:
                best_score = score
                best_match = existing

        if best_match and best_score >= SIMILARITY_THRESHOLD:
            return {
                "is_duplicate": True,
                "matched_complaint": {"id": best_match["id"], "text": best_match["text"]},
                "similarity_score": round(best_score, 4),
            }

        return {
            "is_duplicate": False,
            "matched_complaint": None,
            "similarity_score": round(best_score, 4) if best_match else None,
        }


if __name__ == "__main__":
    # Quick manual test
    store = ComplaintStore()
    store.add("Big pothole near Sector 62 metro station, very dangerous", lat=28.6280, lon=77.3649)
    store.add("Streetlight not working on MG Road for a week", lat=28.4780, lon=77.0722)

    # This should match complaint #1 despite completely different wording
    result = store.check_duplicate(
        "Road cavity close to the metro at Sector 62, cars are swerving",
        lat=28.6285, lon=77.3650,
    )
    print("Test 1 (should be duplicate):", result)

    # This should NOT match anything (different issue entirely)
    result2 = store.check_duplicate("Garbage not collected on Sunday", lat=28.5, lon=77.2)
    print("Test 2 (should NOT be duplicate):", result2)

# CIVIC-TWIN AI — Duplicate Complaint Detection Module

This module catches when multiple citizens report the SAME civic issue,
even if they describe it in totally different words.

---

## Step 1: Setup (same pattern as complaint analysis)

```python
!pip install google-genai fastapi uvicorn pydantic numpy

import os
os.environ['GEMINI_API_KEY'] = 'your-key-here'  # same key as Module 2
```

---

## Step 2: Test it directly

```bash
python duplicate_detector.py
```

This runs two built-in tests:
1. A complaint worded completely differently from an existing one about
   the SAME pothole — should be flagged as a duplicate.
2. An unrelated complaint (garbage collection) — should NOT match anything.

Expected output looks like:
```
Test 1 (should be duplicate): {'is_duplicate': True, 'matched_complaint': {'id': 1, 'text': 'Big pothole near Sector 62...'}, 'similarity_score': 0.91}
Test 2 (should NOT be duplicate): {'is_duplicate': False, 'matched_complaint': None, 'similarity_score': 0.31}
```

---

## Step 3: Understand how it fits into the full workflow

This is meant to run BEFORE a complaint gets added to your system:

```
New complaint comes in
        ↓
Call POST /check-duplicate
        ↓
   is_duplicate?
   ↙          ↘
 YES            NO
  ↓              ↓
Link to      Call POST /complaints
existing      (register as new)
complaint
```

Your backend should call `/check-duplicate` first. If it's NOT a
duplicate, backend then calls `/complaints` to register it (so future
complaints can be compared against it too).

---

## Step 4: Run as an API

```bash
uvicorn api:app --port 8003
```

Example requests:
```
POST /complaints
{"text": "Pothole near XYZ market", "lat": 28.61, "lon": 77.20}

POST /check-duplicate
{"text": "Big hole in road near XYZ market", "lat": 28.611, "lon": 77.201}
```

---

## Important: this uses an in-memory store

Right now, all complaints live in this server's memory — they vanish if
the server restarts. This is intentional for development: it lets you
build and test this module independently before your backend exists.

**When your backend is ready:** replace `ComplaintStore` with real calls
to their database, so complaints persist properly and match against ALL
historical complaints, not just ones added in the current session.

---

## Tuning tips

- `SIMILARITY_THRESHOLD` (in duplicate_detector.py, default 0.85) — raise
  it to be stricter (fewer false duplicate matches), lower it to catch
  more potential duplicates (but more false positives).
- `MAX_DISTANCE_KM` (default 0.5km) — how close two complaints must be
  geographically to even be compared. Adjust based on how dense your
  target city/area is.
- Test with real example complaints from your own city/dataset to see
  what threshold actually works well before the hackathon demo.

google-genai==1.15.0
fastapi==0.115.0
uvicorn==0.30.6
pydantic==2.9.2
numpy==1.26.4
