"""Report why the live 10,000-run simulator is or is not connected.

Does not fetch, invent, or approve ratings. Exit 0 so evidence refresh can
continue while a missing ratings feed is prominently reported.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

def check():
    staged = ROOT / "data/staging/torvik-ratings.json"
    mapping = ROOT / "data/torvik-espn-reviewed.json"
    published = ROOT / "data/ratings.json"
    print("NCAAB RATINGS PIPELINE STATUS")
    for label, path in (("T-Rank staged source", staged),
                        ("Reviewed ESPN team mapping", mapping),
                        ("Simulator ratings", published)):
        print(f"{label}: {'PRESENT' if path.is_file() else 'MISSING'}")
    if not published.is_file():
        print("SIMULATOR BLOCKED: no verified ratings file; baseline is NOT a Monte Carlo prediction")
        return
    try:
        payload = json.loads(published.read_text())
        teams = payload["teams"]
        stamp = datetime.fromisoformat(payload["fetchedAt"].replace("Z", "+00:00"))
        if not isinstance(teams, dict) or len(teams) < 300:
            raise ValueError("fewer than 300 rated teams")
        if not payload.get("source") or stamp.tzinfo is None:
            raise ValueError("source or timezone missing")
        age = (datetime.now(timezone.utc) - stamp).total_seconds() / 3600
        print(f"Ratings: {len(teams)} teams; age {age:.1f} hours")
        if age > 72 or age < 0:
            print("SIMULATOR BLOCKED: ratings timestamp outside allowed window")
        else:
            print("Ratings file present; each matchup still requires both team IDs and pregame cutoff.")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("SIMULATOR BLOCKED: invalid ratings file:", exc)

if __name__ == "__main__":
    check()
