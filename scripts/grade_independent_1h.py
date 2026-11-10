"""Grade only verifiably pre-tipoff first-half projections.

Read saved calculator snapshots and ESPN completed box-score evidence.
Never treat a post-tipoff regenerated projection as a pregame forecast.
"""
import json
import math
from datetime import datetime
from pathlib import Path


def stamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone required")
    return result


def first_period(team):
    scores = team.get("linescores") or []
    if not scores:
        return None
    value = scores[0]
    if isinstance(value, dict):
        value = value.get("value", value.get("displayValue"))
    try:
        number = float(value)
        return number if math.isfinite(number) and number >= 0 else None
    except (ValueError, TypeError):
        return None


def grade(matchup, completed_event):
    """Return a grade or None; caller must retain immutable source snapshot."""
    if str(matchup.get("id")) != str(completed_event.get("id")):
        return None
    if stamp(matchup["ratingsFetchedAt"]) >= stamp(matchup["date"]):
        return None
    competition = (completed_event.get("competitions") or [{}])[0]
    if not competition.get("status", {}).get("type", {}).get("completed"):
        return None
    teams = competition.get("competitors") or []
    away = next((t for t in teams if t.get("homeAway") == "away"), None)
    home = next((t for t in teams if t.get("homeAway") == "home"), None)
    if not away or not home:
        return None
    if str(away.get("id")) != str(matchup.get("awayId")) or str(home.get("id")) != str(matchup.get("homeId")):
        return None
    actual_away, actual_home = first_period(away), first_period(home)
    if actual_away is None or actual_home is None:
        return None
    actual_margin = actual_home - actual_away
    output = {"gameId": str(matchup["id"]), "date": matchup["date"],
              "awayName": matchup["awayName"], "homeName": matchup["homeName"],
              "actualAway1H": actual_away, "actualHome1H": actual_home,
              "actualMargin1H": actual_margin, "actualTotal1H": actual_away + actual_home,
              "models": {}}
    for name, key in (("independent", "independentFirstHalf"), ("historical", "firstHalf")):
        model = matchup.get(key)
        if not model:
            continue
        output["models"][name] = {
            "version": model.get("modelVersion"),
            "projectedAway": model["away"], "projectedHome": model["home"],
            "projectedMargin": model["homeMargin"], "projectedTotal": model["total"],
            "awayError": model["away"] - actual_away,
            "homeError": model["home"] - actual_home,
            "marginError": model["homeMargin"] - actual_margin,
            "totalError": model["total"] - actual_away - actual_home,
        }
    return output if output["models"] else None


def summarize(grades):
    results = {}
    for name in ("independent", "historical"):
        rows = [g["models"][name] for g in grades if name in g["models"]]
        if not rows:
            results[name] = {"games": 0, "marginMAE": None, "totalMAE": None, "marginBias": None}
            continue
        n = len(rows)
        results[name] = {"games": n,
                         "marginMAE": sum(abs(x["marginError"]) for x in rows) / n,
                         "totalMAE": sum(abs(x["totalError"]) for x in rows) / n,
                         "marginBias": sum(x["marginError"] for x in rows) / n}
    return results
