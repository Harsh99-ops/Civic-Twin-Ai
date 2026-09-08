"""
CIVIC-TWIN AI — LLM Chat Assistant
======================================
Replaces the earlier regex-based parser with a real Claude API call.
The model gets a small set of tools that query the SAME live data shown
on the GIS map (route checks, filtered complaint search, city-wide
stats, risk zones) and grounds every answer in what those tools
actually return — it never invents complaint counts or locations.

This is the only part of CIVIC-TWIN AI that calls out to an LLM; the
GIS map / report / risk / budget pipeline stays fully deterministic.

REQUIRES: ANTHROPIC_API_KEY set in the environment. See README.
"""

import json
import os

import anthropic

from modules.route_check import check_route
from modules.store import search_complaints
from modules.stats import compute_stats
from modules.risk_engine import predict_risk

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
MAX_TOOL_ROUNDS = 4

SYSTEM_PROMPT = """You are the CivicTwin Assistant, embedded in the CivicTwin AI civic-infrastructure \
dashboard for Delhi-NCR (Noida/Ghaziabad/Gurugram/Delhi).

You have tools that query the SAME live complaint database driving the GIS map on screen. Always call \
a tool to get real data before answering any question about routes, defects, complaint counts, or risk \
areas — never invent complaint IDs, counts, severities, or locations. If a tool returns zero results, \
say so plainly; that's a real, useful answer ("route looks clear" / "nothing reported").

Typical questions you should handle by calling tools:
- "I'm going from X to Y, any issues?" -> check_route
- "Are there potholes in Sector 62?" / "waterlogging near X" -> search_complaints (with `near`)
- "How many complaints are there overall / by category?" -> get_stats
- "Which areas need the most urgent repair?" -> get_risk_zones

Locations are usually Noida sector names ("Sector 62") or raw "lat,lon" coordinates. Sector name \
resolution only covers a fixed set of well-known sectors — if a tool reports it doesn't recognize a \
place, ask the user for coordinates or a nearby known sector instead of guessing.

Keep replies short and conversational (2-4 sentences), plain language, no markdown tables. If asked \
something unrelated to civic infrastructure/roads/complaints, briefly redirect back to what you can help \
with. You are not a general-purpose assistant — stay scoped to this app's data."""

TOOLS = [
    {
        "name": "check_route",
        "description": (
            "Check whether any reported civic issues (potholes, waterlogging, streetlight faults, "
            "waste) lie on the straight-line path between two places. Use whenever the user asks about "
            "travelling, commuting, or moving from one place to another."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Start point: a Noida sector name ('Sector 62') or 'lat,lon'."},
                "destination": {"type": "string", "description": "End point: same format as origin."},
            },
            "required": ["origin", "destination"],
        },
    },
    {
        "name": "search_complaints",
        "description": (
            "Search the live complaint database by category, road authority, minimum severity, and/or "
            "proximity to a place. Use for questions like 'are there potholes in Sector 62' or "
            "'critical waterlogging issues on NHAI roads'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["Road Damage", "Drainage / Waterlogging", "Streetlight / Electrical", "Waste Management"],
                },
                "road_type": {"type": "string", "enum": ["NHAI", "State/Municipal"]},
                "min_severity": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]},
                "near": {"type": "string", "description": "A place (sector name or 'lat,lon') to search around."},
                "radius_km": {"type": "number", "description": "Radius in km around 'near'. Default 1.5."},
            },
        },
    },
    {
        "name": "get_stats",
        "description": "City-wide aggregate counts: total complaints, and breakdowns by category, severity, and road authority.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_risk_zones",
        "description": "Top highest-risk zones from the risk engine, ranked by risk score. Use for 'which areas are most urgent' style questions.",
        "input_schema": {
            "type": "object",
            "properties": {"top_n": {"type": "integer", "description": "How many zones to return, default 5"}},
        },
    },
]

TRIM_FIELDS = [
    "complaint_id", "latitude", "longitude", "complaint_category", "defect_type",
    "severity", "severity_score", "road_type", "road_name", "date_time",
    "report_count", "distance_km", "distance_from_route_m",
]


def _trim(rows):
    return [{k: r[k] for k in TRIM_FIELDS if k in r} for r in rows]


def _execute_tool(name: str, tool_input: dict) -> dict:
    if name == "check_route":
        result = check_route(tool_input["origin"], tool_input["destination"])
        if result.get("resolved") and "matches" in result:
            result = {**result, "matches": _trim(result["matches"])}
        return result

    if name == "search_complaints":
        near_lat = near_lon = None
        if tool_input.get("near"):
            from modules.route_check import resolve_place
            resolved = resolve_place(tool_input["near"])
            if resolved:
                near_lat, near_lon, _ = resolved
            else:
                return {"error": f"Unrecognized place: {tool_input['near']}"}
        rows = search_complaints(
            category=tool_input.get("category"),
            road_type=tool_input.get("road_type"),
            min_severity=tool_input.get("min_severity"),
            near_lat=near_lat,
            near_lon=near_lon,
            radius_km=tool_input.get("radius_km", 1.5),
        )
        return {"count": len(rows), "complaints": _trim(rows)}

    if name == "get_stats":
        return compute_stats()

    if name == "get_risk_zones":
        return {"zones": predict_risk(top_n=tool_input.get("top_n", 5))}

    return {"error": f"Unknown tool: {name}"}


def _client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def chat_with_llm(messages: list) -> dict:
    """
    messages: list of {"role": "user"|"assistant", "content": str} — full
    conversation history, most recent last.

    Returns {"reply": str} or {"reply": str, "error": True} if the API
    key is missing or the call fails.
    """
    client = _client()
    if client is None:
        return {
            "reply": (
                "The chat assistant needs an ANTHROPIC_API_KEY set on the backend to work. "
                "Set it in backend/.env or your shell environment and restart the server."
            ),
            "error": True,
        }

    convo = [{"role": m["role"], "content": m["content"]} for m in messages]

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=600,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=convo,
            )

            if response.stop_reason != "tool_use":
                text = "".join(block.text for block in response.content if block.type == "text")
                return {"reply": text.strip() or "I couldn't come up with a response — try rephrasing."}

            convo.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result = _execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })
            convo.append({"role": "user", "content": tool_results})

        return {"reply": "That took more steps than expected — try asking a simpler, more specific question."}

    except anthropic.AuthenticationError:
        return {"reply": "The backend's ANTHROPIC_API_KEY looks invalid. Check backend/.env.", "error": True}
    except Exception as e:  # noqa: BLE001 — surface any API error to the chat, don't crash the request
        return {"reply": f"Chat assistant error: {e}", "error": True}
