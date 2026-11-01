"""Stage public Bart Torvik season CSV for reviewed identity matching.

Does not publish unverified ratings or bypass existing mapping validation.
"""
import csv
import io
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://barttorvik.com/{season}_team_results.csv"

def parse_csv(raw):
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        raise ValueError("Missing CSV header")
    def normalized(name):
        return "".join(c for c in name.casefold() if c.isalnum())
    columns = {normalized(k): k for k in reader.fieldnames if k}
    if len(columns) < 4:
        raise ValueError("Invalid or duplicate normalized CSV headers")
    required = {"team", "adjoe", "adjde", "adjt"}
    if not required <= columns.keys():
        raise ValueError("Missing expected CSV fields: " + ", ".join(sorted(required - columns.keys())))
    teams = []
    seen = set()
    for row in reader:
        name = (row[columns["team"]] or "").strip()
        if not name or name in seen:
            raise ValueError("Missing or duplicate Torvik team name")
        seen.add(name)
        vals = [float(row[columns[k]]) for k in ("adjoe", "adjde", "adjt")]
        if not (50 <= vals[0] <= 160 and 50 <= vals[1] <= 160 and 45 <= vals[2] <= 90):
            raise ValueError(f"Ratings outside simulator bounds for {name}")
        if not all(map(math.isfinite, vals)):
            raise ValueError("Nonfinite Torvik efficiency or tempo")
        teams.append(dict(team=name, adj_o=vals[0], adj_d=vals[1], adj_t=vals[2]))
    if len(teams) < 300:
        raise ValueError(f"Too few teams in source: {len(teams)}")
    return teams

def stage(season):
    url = SOURCE.format(season=season)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; DocsNCAABResearch/1.0)"})
    with urllib.request.urlopen(req, timeout=45) as response:
        raw = response.read(5_000_001)
        if len(raw) > 5_000_000:
            raise ValueError("CSV exceeded size limit")
        content_type = response.headers.get("Content-Type", "")
    teams = parse_csv(raw.decode("utf-8-sig"))
    out = {"status": "UNMATCHED_DO_NOT_SIMULATE", "source": url,
           "fetchedAt": datetime.now(timezone.utc).isoformat(),
           "season": season, "teams": teams}
    path = ROOT / "data/staging/torvik-ratings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Staged {len(teams)} teams for {season}; source Content-Type: {content_type}")
    print("Ratings not activated until reviewed ESPN mapping passes validation")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=(datetime.now(timezone.utc).year + (datetime.now(timezone.utc).month >= 7)))
    args = parser.parse_args()
    stage(args.season)
