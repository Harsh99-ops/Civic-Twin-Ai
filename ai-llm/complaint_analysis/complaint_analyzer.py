"""
CIVIC-TWIN AI — Smart Complaint Analysis
============================================
Reads a citizen's free-text complaint and uses an LLM (Gemini) to extract
structured information: issue type, urgency, sentiment, mentioned location,
and a short summary.

WHY AN LLM INSTEAD OF TRADITIONAL NLP:
Citizens write complaints in all kinds of ways — different phrasing, mixed
Hindi/English, typos, rambling. An LLM handles this messiness far better
than rule-based keyword matching, without needing a labeled training set
(unlike Module 1's computer vision model).

SETUP:
1. Get a free Gemini API key: https://aistudio.google.com/app/apikey
2. Set it as an environment variable before running:
   In Colab:   import os; os.environ['GEMINI_API_KEY'] = 'your-key-here'
   Locally:    export GEMINI_API_KEY=your-key-here
"""

import os
import json
import re
from google import genai
from google.genai import types

# ---- Configure Gemini with your API key ----
API_KEY = os.environ.get("GEMINI_API_KEY")
_client = genai.Client(api_key=API_KEY) if API_KEY else None

MODEL_NAME = "gemini-3.6-flash"  # current stable Flash model — fast + cheap, good for structured extraction

# The prompt is the "brain" of this module — it tells the LLM exactly what
# to extract and in what format. Keeping the output format strict (JSON only)
# makes it easy for your backend to parse reliably.
SYSTEM_PROMPT = """You are an AI assistant for a civic issue reporting platform called CIVIC-TWIN AI.
You will be given a citizen's complaint about a road/civic issue (pothole, garbage, streetlight, drainage, waterlogging, etc.), possibly written in a mix of English and Hindi/Hinglish.

Analyze the complaint and respond with ONLY a valid JSON object (no markdown, no explanation, no code fences) in exactly this shape:

{
  "issue_type": "Pothole" | "Garbage" | "Streetlight" | "Drainage" | "Waterlogging" | "Road Damage" | "Other",
  "urgency": "Low" | "Medium" | "High" | "Critical",
  "sentiment": "Neutral" | "Frustrated" | "Angry" | "Distressed",
  "location_mentioned": "<exact location text found in the complaint, or null if none>",
  "summary": "<one clear sentence summarizing the issue>",
  "confidence": <number between 0 and 1 representing how confident you are in this classification>
}

Guidelines for urgency:
- "Critical": immediate safety risk (e.g. accidents happening, exposed wires, deep open holes)
- "High": clear hazard but not actively causing accidents right now
- "Medium": genuine issue but low immediate risk
- "Low": minor/cosmetic issue

Respond with ONLY the JSON object, nothing else."""


def analyze_complaint(complaint_text: str) -> dict:
    """
    Send a citizen complaint to the LLM and get back structured analysis.

    Args:
        complaint_text: the raw complaint text as submitted by the citizen.

    Returns:
        dict matching the JSON contract described in SYSTEM_PROMPT, plus
        the original text for reference.
    """
    if not _client:
        raise ValueError(
            "GEMINI_API_KEY is not set. Get a free key at "
            "https://aistudio.google.com/app/apikey and set it as an "
            "environment variable before calling this function."
        )

    if not complaint_text or not complaint_text.strip():
        raise ValueError("complaint_text cannot be empty")

    response = _client.models.generate_content(
        model=MODEL_NAME,
        contents=complaint_text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    raw_output = response.text.strip()

    # LLMs sometimes wrap JSON in markdown code fences even when told not to.
    # Strip those defensively so parsing doesn't break.
    cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", raw_output, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # If the model didn't return clean JSON, fail gracefully with a
        # clear error rather than crashing the whole request.
        raise ValueError(f"Model did not return valid JSON. Raw output: {raw_output}")

    # Attach the original complaint text so downstream systems (duplicate
    # detection, dashboards) always have it alongside the analysis.
    parsed["original_text"] = complaint_text

    return parsed


if __name__ == "__main__":
    # Quick manual test — run this file directly to try it out.
    test_complaint = (
        "Bahut bada gaddha hai Sector 62 metro station ke paas, "
        "raat mein bahut khatarnak hai, gaadi wale accident ho sakte hain"
    )
    result = analyze_complaint(test_complaint)
    print(json.dumps(result, indent=2, ensure_ascii=False))
