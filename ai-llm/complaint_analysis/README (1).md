# CIVIC-TWIN AI — Smart Complaint Analysis Module

This module reads a citizen's complaint text and uses an LLM (Google
Gemini) to extract structured data: what kind of issue it is, how urgent,
the emotional tone, any location mentioned, and a clean summary.

No training, no dataset, no GPU needed — this is much simpler than
Module 1 (defect detection).

---

## Step 1: Get a free Gemini API key

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with a Google account
3. Click "Create API Key" — copy it somewhere safe (you'll need it below)
4. Free tier is generous enough for hackathon development and demo use

---

## Step 2: Set up your environment

### In Google Colab
```python
!pip install google-generativeai fastapi uvicorn pydantic

import os
os.environ['GEMINI_API_KEY'] = 'paste-your-key-here'
```

### On your own machine
```bash
pip install -r requirements.txt
export GEMINI_API_KEY=paste-your-key-here      # Mac/Linux
set GEMINI_API_KEY=paste-your-key-here          # Windows cmd
```

---

## Step 3: Test it

```bash
python complaint_analyzer.py
```

This runs a built-in test complaint and prints structured JSON like:
```json
{
  "issue_type": "Pothole",
  "urgency": "Critical",
  "sentiment": "Distressed",
  "location_mentioned": "Sector 62 metro station",
  "summary": "A large, dangerous pothole near Sector 62 metro station is causing accident risk, especially at night.",
  "confidence": 0.92,
  "original_text": "Bahut bada gaddha hai Sector 62 metro station ke paas..."
}
```

Notice it correctly handled a complaint written in Hinglish (mixed
Hindi/English) — this is something a traditional keyword-matching system
would really struggle with, but an LLM handles naturally.

Try editing the `test_complaint` text at the bottom of
`complaint_analyzer.py` with your own examples to see how it responds.

---

## Step 4: Run it as an API for your backend team

```bash
uvicorn api:app --port 8002
```

Your backend can now POST complaint text and get analysis back:
```
POST http://localhost:8002/analyze
Content-Type: application/json

{"complaint_text": "Streetlight not working on MG Road for a week"}
```

---

## What's next

This is Module 2 of 5. Once this is solid, remaining modules are:
- **Duplicate Complaint Detection** — using text embeddings to catch
  multiple citizens reporting the same issue
- **Risk Prediction Engine**
- **Maintenance Prioritization / Budget Optimization**

## Troubleshooting

- **"GEMINI_API_KEY is not set"** → make sure you ran the `os.environ[...]`
  line BEFORE running/importing complaint_analyzer.py, in the same session.
- **"Model did not return valid JSON"** → rare, but can happen if Gemini's
  response gets cut off. Try again, or simplify the complaint text.
- **Rate limit errors** → free tier has request limits; wait a minute and
  retry, or check your usage at https://aistudio.google.com
