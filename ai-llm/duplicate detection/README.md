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
