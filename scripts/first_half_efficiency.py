"""Independent first-half possession/efficiency baseline.

No sportsbook inputs. No fabricated first-10-minute forecasts or probabilities.
Caller must supply verified, point-in-time ratings and calibrated parameters.
"""
import math
from datetime import datetime


VERSION = "independent-1h-efficiency-v1"


def finite(value, label):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label} is required")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be numeric") from None
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp required")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid timestamp") from None
    if stamp.tzinfo is None:
        raise ValueError("Timezone required")
    return stamp


def project(away, home, *, national_efficiency, ratings_at, tipoff_at,
            neutral=False, home_advantage_full_game=0.0,
            tempo_method="geometric", first_half_pace_factor=0.5):
    """Return independently estimated halftime scores.

    Ratings: offense/defense points per 100 possessions; tempo per 40 min.
    Home adjustment is supplied in full-game points, split across periods
    and equally between teams; default zero until calibrated.
    A 0.5 pace factor represents 20/40 minutes, NOT half a betting spread.
    """
    if instant(ratings_at) >= instant(tipoff_at):
        raise ValueError("Ratings timestamp is not pre-tipoff")
    values = {}
    for name, team in (("away", away), ("home", home)):
        values[name] = {}
        for key in ("offense", "defense", "tempo"):
            n = finite(team.get(key), f"{name}.{key}")
            lo, hi = (45, 90) if key == "tempo" else (50, 160)
            if not lo <= n <= hi:
                raise ValueError(f"{name}.{key} outside supported bounds")
            values[name][key] = n
    base = finite(national_efficiency, "national_efficiency")
    if not 50 <= base <= 160:
        raise ValueError("National baseline outside supported bounds")
    pace_factor = finite(first_half_pace_factor, "first_half_pace_factor")
    if not 0 < pace_factor <= 1:
        raise ValueError("Invalid pace factor")
    home_advantage = finite(home_advantage_full_game, "home_advantage_full_game")
    if abs(home_advantage) > 20:
        raise ValueError("Home advantage outside supported bounds")
    if tempo_method == "geometric":
        tempo = math.sqrt(values["away"]["tempo"] * values["home"]["tempo"])
    else:
        raise ValueError("Unvalidated tempo method")
    possessions = tempo * pace_factor
    away_eff = values["away"]["offense"] * values["home"]["defense"] / base
    home_eff = values["home"]["offense"] * values["away"]["defense"] / base
    # Full-game adjustment distributed by elapsed fraction; centered on both teams.
    margin_adjustment = 0 if neutral else home_advantage * pace_factor
    away_points = possessions * away_eff / 100 - margin_adjustment / 2
    home_points = possessions * home_eff / 100 + margin_adjustment / 2
    if min(away_points, home_points) < 0:
        raise ValueError("Negative expected score")
    return {
        "modelVersion": VERSION,
        "away": away_points, "home": home_points,
        "homeMargin": home_points - away_points,
        "total": home_points + away_points,
        "firstHalfPossessions": possessions,
        "awayEfficiency": away_eff, "homeEfficiency": home_eff,
        "ratingsAt": ratings_at, "tipoffAt": tipoff_at,
        "assumptions": {
            "nationalEfficiency": base, "tempoMethod": tempo_method,
            "firstHalfPaceFactor": pace_factor,
            "homeAdvantageFullGame": home_advantage, "neutral": neutral,
            "earlyPaceCorrectionCalibrated": False,
            "uncertaintyCalibrated": False,
        },
        "firstTenMinutes": None,
        "coverProbability": None,
        "status": "BASELINE_UNCALIBRATED",
    }
