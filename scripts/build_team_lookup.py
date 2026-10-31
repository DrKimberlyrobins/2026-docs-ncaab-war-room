"""Build the ESPN-ID master lookup and an explicit T-Rank reconciliation queue.

No name similarity is treated as verification. Reviewed T-Rank names are
retained only if their ESPN IDs still exist. A mismatch blocks publication.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def build_master(espn, reviewed=None):
    reviewed = reviewed or {}
    if not isinstance(reviewed, dict):
        raise ValueError("Reviewed mapping must be an object")
    rows = []
    seen_ids = set()
    for sport in espn["data"]["sports"]:
        for league in sport.get("leagues", []):
            for entry in league.get("teams", []):
                team = entry["team"]
                tid = str(team["id"])
                if tid in seen_ids:
                    raise ValueError(f"Duplicate ESPN team ID: {tid}")
                seen_ids.add(tid)
                rows.append({"espnId": tid, "espnName": team["displayName"],
                             "abbreviation": team.get("abbreviation", ""),
                             "torvikName": reviewed.get(tid),
                             "ratingIdentityStatus": "REVIEWED" if tid in reviewed else "UNMATCHED"})
    if not rows:
        raise ValueError("No ESPN teams available")
    unknown = set(reviewed) - seen_ids
    if unknown:
        raise ValueError(f"Reviewed IDs absent from ESPN directory: {sorted(unknown)}")
    if len(set(reviewed.values())) != len(reviewed):
        raise ValueError("Multiple ESPN teams share one reviewed source identity")
    rows.sort(key=lambda r: (r["espnName"].casefold(), r["espnId"]))
    return {"status": "IDENTITY_LOOKUP_ONLY_NOT_RATINGS", "createdAt": datetime.now(timezone.utc).isoformat(),
            "espnTeamCount": len(rows), "reviewedCount": len(reviewed),
            "teams": rows}

def main():
    espn = json.loads((ROOT / "data/teams.json").read_text())
    approved = ROOT / "data/torvik-espn-reviewed.json"
    reviewed = json.loads(approved.read_text()) if approved.exists() else {}
    result = build_master(espn, reviewed)
    target = ROOT / "data/team-lookup.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Master lookup: {result['espnTeamCount']} ESPN teams; {result['reviewedCount']} reviewed T-Rank matches")
    print("Unmatched teams cannot be used as verified ratings.")

if __name__ == "__main__":
    main()
