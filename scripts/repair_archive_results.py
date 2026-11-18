"""Backfill final scores for saved pregame receipts without changing forecasts.

Run from repository root: python scripts/repair_archive_results.py
Only ESPN completed game summaries with matching event IDs are accepted.
"""
import json
import math
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
INDEX = ROOT / "data/archive/index.json"
REPORT = ROOT / "data/archive/repair-report.json"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Docs-NCAAB-Research/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)

def score(value):
    if isinstance(value, dict):
        value = value.get("value", value.get("displayValue"))
    try:
        n = float(value)
        return int(n) if math.isfinite(n) and n >= 0 and n.is_integer() else None
    except (TypeError, ValueError):
        return None

def period(away, home):
    return {"away": away, "home": home, "total": away + home, "homeMargin": home - away}

def extract(data, event_id):
    header = data.get("header", {})
    competition = next((c for c in header.get("competitions", [])
                        if str(c.get("id")) == str(event_id)), None)
    if competition is None:
        return None
    status = competition.get("status", {})
    if not status.get("type", {}).get("completed"):
        return None
    teams = competition.get("competitors", [])
    away = next((t for t in teams if t.get("homeAway") == "away"), None)
    home = next((t for t in teams if t.get("homeAway") == "home"), None)
    if not away or not home:
        return None
    a, h = score(away.get("score")), score(home.get("score"))
    if a is None or h is None:
        return None
    result = {"full": period(a, h)}
    al, hl = away.get("linescores") or [], home.get("linescores") or []
    if al and hl:
        ah, hh = score(al[0]), score(hl[0])
        if ah is not None and hh is not None:
            result["half"] = period(ah, hh)
    return result

def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def main():
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()
    counts = {"checked": 0, "repaired": 0, "alreadyFinal": 0, "pending": 0, "errors": 0}
    by_date = {}
    changed_index = False
    for item in index.get("games", []):
        path = ROOT / "data/archive/games" / (str(item["id"]) + ".json")
        if not path.is_file():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if str(record.get("snapshot", {}).get("id")) != str(item["id"]):
            counts["errors"] += 1
            continue
        existing = record.get("result") or {}
        if existing.get("full"):
            counts["alreadyFinal"] += 1
            if not item.get("final"):
                item["final"] = True
                changed_index = True
            continue
        counts["checked"] += 1
        url = BASE + "/summary?event=" + str(item["id"])
        try:
            data = fetch(url)
            result = extract(data, item["id"])
            if result is None:
                counts["pending"] += 1
                continue
            record["result"] = {
                "fetchedAt": now, "sourceUrl": url,
                **result, "status": "Final"
            }
            save(path, record)
            item["final"] = True
            changed_index = True
            counts["repaired"] += 1
            by_date[item.get("date", "unknown")] = by_date.get(item.get("date", "unknown"), 0) + 1
        except Exception as exc:
            counts["errors"] += 1
            print("RESULT ERROR", item["id"], str(exc))
        time.sleep(0.1)
    if changed_index:
        index["updatedAt"] = now
        save(INDEX, index)

    # Recalculate metrics strictly from immutable saved model values and verified final scores.
    grades = {}
    for item in index.get("games", []):
        path = ROOT / "data/archive/games" / (str(item["id"]) + ".json")
        if not path.is_file():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if item.get("scheduleCheck", {}).get("exclude") if isinstance(item.get("scheduleCheck"), dict) else False:
            continue
        model = record.get("snapshot", {}).get("matchup", {}).get("model") or {}
        actual = (record.get("result") or {}).get("full") or {}
        if not all(isinstance(model.get(k), (int, float)) and isinstance(actual.get(k), (int, float))
                   for k in ("homeMargin", "total")):
            continue
        date = item.get("date", "unknown")
        entry = grades.setdefault(date, {"graded": 0, "winnerCorrect": 0, "ties": 0,
                                         "marginAbsErrorSum": 0.0, "totalAbsErrorSum": 0.0})
        entry["graded"] += 1
        pm, am = model["homeMargin"], actual["homeMargin"]
        if pm == 0 or am == 0:
            entry["ties"] += 1
        elif (pm > 0) == (am > 0):
            entry["winnerCorrect"] += 1
        entry["marginAbsErrorSum"] += abs(pm - am)
        entry["totalAbsErrorSum"] += abs(model["total"] - actual["total"])
    for entry in grades.values():
        n = entry["graded"]
        decided = n - entry["ties"]
        entry["winnerAccuracy"] = round(entry["winnerCorrect"] / decided, 4) if decided else None
        entry["marginMAE"] = round(entry.pop("marginAbsErrorSum") / n, 3)
        entry["totalMAE"] = round(entry.pop("totalAbsErrorSum") / n, 3)
    save(REPORT, {"generatedAt": now, "repair": counts, "newFinalsByDate": by_date,
                  "modelGrading": grades, "note": "Original pregame forecasts were not modified. Ties and zero projected margins excluded from winner accuracy."})
    print(json.dumps({"repair": counts, "nov17": grades.get("2026-11-17")}, indent=2))
    if counts["errors"]:
        raise SystemExit("Some result fetches failed; rerun to retry without overwriting existing results.")

if __name__ == "__main__":
    main()
