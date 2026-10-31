"""Validate staged ratings without guessing ESPN identifiers.

Only a reviewed mapping of ESPN team IDs to source team names can produce
data/ratings.json. No fuzzy or automatic name guessing is permitted.
"""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

def build(staged, mapping, *, now=None):
    if staged.get("status") != "UNMATCHED_DO_NOT_SIMULATE":
        raise ValueError("Unexpected staging status")
    source_rows = staged.get("teams")
    if not isinstance(source_rows, list):
        raise ValueError("Expected team ratings list")
    names = {}
    for row in source_rows:
        name = str(row.get("team", "")).strip()
        if not name or name in names:
            raise ValueError("Missing or duplicate source team")
        vals = [float(row[k]) for k in ("adj_o", "adj_d", "adj_t")]
        if not all(math.isfinite(v) for v in vals):
            raise ValueError("Nonfinite source rating")
        if not (50 <= vals[0] <= 160 and 50 <= vals[1] <= 160 and 45 <= vals[2] <= 90):
            raise ValueError("Source ratings outside validated model bounds")
        names[name] = dict(zip(("adj_off", "adj_def", "adj_tempo"), vals))
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Reviewed ESPN ID mapping required")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Source teams cannot map to multiple ESPN IDs")
    unknown = set(mapping.values()) - set(names)
    if unknown:
        raise ValueError(f"Unrecognized source team names: {len(unknown)}")
    if len(mapping) < 300:
        raise ValueError("Insufficient verified team mappings")
    stamp = staged.get("fetchedAt")
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Source timestamp lacks timezone")
    now = now or datetime.now(timezone.utc)
    if parsed > now:
        raise ValueError("Future source timestamp")
    return {"source": staged["source"], "fetchedAt": stamp,
            "teams": {str(k): names[v] for k, v in mapping.items()}}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", default="data/staging/torvik-ratings.json")
    parser.add_argument("--mapping", default="data/torvik-espn-reviewed.json")
    parser.add_argument("--output", default="data/ratings.json")
    args = parser.parse_args()
    staged = json.loads(Path(args.staged).read_text())
    mapping = json.loads(Path(args.mapping).read_text())
    result = build(staged, mapping)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print("Validated", len(result["teams"]), "ESPN team IDs")

if __name__ == "__main__":
    main()
