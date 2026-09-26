"""Guardian's tools. Built per request so each one knows the request id and the
harness's context policy (which controls how much user history the agent sees)."""

import json
import re
from datetime import datetime

from strands import tool

from .config import DATA_DIR

USERS = json.loads((DATA_DIR / "users.json").read_text(encoding="utf-8"))

# Tools the coach may enable or disable. Descriptions are shown to the coach.
TOOL_CATALOG = {
    "check_location": "Classifies the meeting spot (public, semi_private, private, nightlife, unknown) and whether the time is after dark.",
    "check_user_history": "Returns the requesting user's account facts and past bookings. What it reveals is limited by the context policy.",
    "flag_request": "Records a flag for human review in MongoDB. Use when something looks unsafe.",
}

DEFAULT_CONTEXT_POLICY = {
    "max_history_items": 1,       # past bookings shown (0-10)
    "include_reports": False,     # safety reports filed against the user
    "include_ratings": False,     # host ratings and average rating
    "include_verification": False # account age + ID verification
}

_PUBLIC = ["cafe", "coffee", "starbucks", "park", "library", "community center", "museum", "market",
           "food court", "mall", "lobby", "atrium", "pizza", "plaza", "cafeteria", "studio lounge", "courtyard"]
_PRIVATE = ["apartment", "my place", "home", "house", "airbnb", "my car", "back seat", "bedroom", "parking garage"]
_NIGHTLIFE = re.compile(r"\b(bar|club|pub|nightclub)\b")
_UNKNOWN = ["tbd", "wherever", "somewhere", "anywhere", "you pick"]
_SEMI = ["hotel", "office", "workplace"]


def classify_location(location: str) -> str:
    loc = f" {location.lower()} "
    if any(k in loc for k in _UNKNOWN) or not location.strip():
        return "unknown"
    if re.search(r"\broom\s*\d+", loc) or any(k in loc for k in _PRIVATE):
        return "private"
    if _NIGHTLIFE.search(loc):
        return "nightlife"
    if "hotel" in loc and ("lobby" in loc or "cafe" in loc):
        return "public"
    if any(k in loc for k in _SEMI):
        return "semi_private"
    if any(k in loc for k in _PUBLIC):
        return "public"
    return "unknown"


def parse_hour(when: str):
    try:
        return datetime.strptime(when.strip()[:16], "%Y-%m-%d %H:%M").hour
    except ValueError:
        return None


def user_view(user_id: str, policy: dict) -> dict:
    """What check_user_history reveals under a given context policy."""
    u = USERS.get(user_id)
    if not u:
        return {"user_id": user_id, "found": False}
    view = {"user_id": user_id, "name": u["name"], "completed_hugs": u["completed_hugs"]}
    n = max(0, min(int(policy.get("max_history_items", 1)), 10))
    history = u["history"][:n]
    if not policy.get("include_ratings"):
        history = [{k: v for k, v in h.items() if k != "host_rating"} for h in history]
    else:
        view["avg_rating"] = u["avg_rating"]
    view["recent_bookings"] = history
    if policy.get("include_verification"):
        view["account_age_days"] = u["account_age_days"]
        view["id_verified"] = u["id_verified"]
    if policy.get("include_reports"):
        view["reports"] = u["reports"]
    return view


def build_tools(allowed: list[str], policy: dict, request_id: str, harness_version: int, store=None):
    @tool
    def check_location(location: str, when: str) -> dict:
        """Classify a meeting spot and time for safety.

        Args:
            location: The meeting place as written in the request.
            when: The requested time, format "YYYY-MM-DD HH:MM" if known.
        """
        hour = parse_hour(when)
        return {
            "venue_type": classify_location(location),
            "hour": hour,
            "time_known": hour is not None,
            "after_dark": hour is not None and (hour >= 20 or hour < 6),
        }

    @tool
    def check_user_history(user_id: str) -> dict:
        """Look up the requesting user's account and past bookings.

        Args:
            user_id: The user id from the request, like "u04".
        """
        return user_view(user_id, policy)

    @tool
    def flag_request(reason: str, severity: str = "medium") -> str:
        """Flag this booking for human review.

        Args:
            reason: Why the request looks unsafe.
            severity: low, medium or high.
        """
        if store is not None:
            store.save_flag({"request_id": request_id, "reason": reason, "severity": severity,
                             "harness_version": harness_version})
        return "flagged"

    everything = {"check_location": check_location, "check_user_history": check_user_history,
                  "flag_request": flag_request}
    return [everything[name] for name in allowed if name in everything]
