"""Produce deterministic *candidates* for ESPN/Torvik identities, never approvals."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def key(s):
    s = s.casefold().replace("&", "and")
    return re.sub(r"[^a-z0-9]", "", s)

def main():
    lookup = json.loads((ROOT / "data/team-lookup.json").read_text())
    stage = ROOT / "data/staging/torvik-ratings.json"
    if not stage.exists():
        print("No Torvik CSV staged; candidate matching unavailable.")
        return
    source = json.loads(stage.read_text())
    index = {}
    for item in source["teams"]:
        index.setdefault(key(item["team"]), []).append(item["team"])
    exact = {}
    unresolved = []
    for row in lookup["teams"]:
        names = index.get(key(row["espnName"]), [])
        if len(names) == 1:
            exact[row["espnId"]] = names[0]
        else:
            unresolved.append({"espnId": row["espnId"], "espnName": row["espnName"],
                               "reason": "AMBIGUOUS" if names else "NO_EXACT_NAME_MATCH"})
    output = {"status": "CANDIDATES_NOT_APPROVED", "source": source.get("source"),
              "fetchedAt": source.get("fetchedAt"), "exactCandidates": exact,
              "unresolved": unresolved, "exactCount": len(exact),
              "unresolvedCount": len(unresolved)}
    target = ROOT / "data/staging/torvik-identity-candidates.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Identity candidates: {len(exact)} exact, {len(unresolved)} unresolved; NOT APPROVED")

if __name__ == "__main__":
    main()
