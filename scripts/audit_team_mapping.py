"""Generate a non-authoritative matching audit; never silently assign ESPN IDs.

Reads ESPN's cached directory and a staged T-Rank export. Exact normalized
names become candidates, not approved mappings. Everything else is reported
as unmatched for source-backed reconciliation.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def normalized(name):
    return re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()

def audit(espn, staged):
    teams = espn["data"]["sports"][0]["leagues"][0]["teams"]
    source_names = [row["team"] for row in staged["teams"]]
    by_name = {}
    for name in source_names:
        by_name.setdefault(normalized(name), []).append(name)
    candidates, unmatched, ambiguous = [], [], []
    for item in teams:
        team = item["team"]
        choices = by_name.get(normalized(team["displayName"]), [])
        record = {"espnId": str(team["id"]), "espnName": team["displayName"]}
        if len(choices) == 1:
            candidates.append({**record, "sourceName": choices[0],
                               "status": "CANDIDATE_REVIEW_REQUIRED"})
        elif len(choices) > 1:
            ambiguous.append({**record, "sourceNames": choices})
        else:
            unmatched.append(record)
    return {"status": "AUDIT_ONLY_NOT_APPROVED", "exactCandidates": candidates,
            "unmatchedESPN": unmatched, "ambiguous": ambiguous,
            "sourceTeamCount": len(source_names), "espnTeamCount": len(teams)}

def main():
    espn = json.loads((ROOT / "data/teams.json").read_text())
    staged = json.loads((ROOT / "data/staging/torvik-ratings.json").read_text())
    report = audit(espn, staged)
    dest = ROOT / "data/staging/team-mapping-audit.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2) + "\n")
    print("Exact candidates:", len(report["exactCandidates"]),
          "Unmatched ESPN:", len(report["unmatchedESPN"]),
          "Ambiguous:", len(report["ambiguous"]))
    print("AUDIT ONLY: no ratings.json or reviewed mapping generated")

if __name__ == "__main__":
    main()
