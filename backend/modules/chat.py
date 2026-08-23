"""
CIVIC-TWIN AI — Chat Assistant
==================================
A small, deterministic (no LLM call) message handler for the "CivicTwin
Assistant" chat widget. Its one real job: answer "am I going to hit any
reported issues between A and B?" — everything else is light chit-chat /
guidance back toward that question.

Parsing strategy: look for "from X to Y" / "between X and Y" patterns.
X and Y can be Noida sector names or raw "lat,lon" coordinates (handled
by route_check.resolve_place). No ML/LLM needed for this — it's a
narrow, well-defined slot-filling task.
"""

import re

from modules.route_check import check_route

FROM_TO_RE = re.compile(r"from\s+(.+?)\s+to\s+(.+)", re.IGNORECASE)
BETWEEN_RE = re.compile(r"between\s+(.+?)\s+and\s+(.+)", re.IGNORECASE)
ARROW_RE = re.compile(r"(.+?)\s*(?:->|→|to)\s*(.+)")

GREETING_WORDS = {"hi", "hello", "hey", "hii", "hola", "namaste"}


def _clean(text: str) -> str:
    return text.strip().strip(".,!? ").strip()


def _extract_route(message: str):
    for pattern in (FROM_TO_RE, BETWEEN_RE):
        m = pattern.search(message)
        if m:
            return _clean(m.group(1)), _clean(m.group(2))
    # Fall back to a bare "X to Y" / "X -> Y" if nothing else matched and
    # the message doesn't look like plain chit-chat.
    m = ARROW_RE.search(message)
    if m and len(message.split()) <= 8:
        a, b = _clean(m.group(1)), _clean(m.group(2))
        if a and b:
            return a, b
    return None


def handle_chat_message(message: str) -> dict:
    text = message.strip()
    lowered = text.lower()

    if not text:
        return {"reply": "Ask me something like \"from Sector 62 to Sector 18\" and I'll check for reported road issues along the way."}

    if lowered in GREETING_WORDS or lowered.rstrip("!") in GREETING_WORDS:
        return {
            "reply": "Hi! I'm the CivicTwin Assistant. Tell me where you're travelling — "
                     "e.g. \"from Sector 62 to Sector 18\" — and I'll check for any reported "
                     "road damage or waterlogging along the way. You can also report a new issue "
                     "from the Report Issue page.",
        }

    route = _extract_route(text)
    if route is None:
        return {
            "reply": "I can check a route for you — try something like \"from Sector 62 to Sector 18\" "
                     "or \"between 28.62,77.37 and 28.57,77.33\".",
        }

    origin, destination = route
    result = check_route(origin, destination)

    if not result["resolved"]:
        return {"reply": result["error"]}

    o, d = result["origin"], result["destination"]
    if result["issues_found"] == 0:
        reply = f"Good news — no reported issues between {o['name']} and {d['name']}. The route looks clear."
    else:
        top = result["matches"][0]
        plural = "s" if result["issues_found"] != 1 else ""
        reply = (
            f"⚠️ {result['issues_found']} reported issue{plural} between {o['name']} and {d['name']}. "
            f"Worst: {top['severity']} severity {top['defect_type']} "
            f"({top['distance_from_route_m']}m from the route, flagged by {top['report_count']} citizen(s))."
        )

    return {"reply": reply, "route_result": result}
