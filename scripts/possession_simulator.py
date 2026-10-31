"""Independent, reproducible NCAAB possession-based simulation.

Input efficiencies are points per 100 possessions. Ratings must be supplied
with provenance; no KenPom retrieval or license is implied by this module.
This is an experimental model, not a calibrated probability forecast.
"""
from __future__ import annotations
import argparse
import json
import math
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

MODEL_VERSION = "possessions-mc-v0.1"
D1_BASELINE = 106.0  # explicit configurable assumption, NOT a live D-I statistic

@dataclass(frozen=True)
class Team:
    name: str
    adj_off: float
    adj_def: float
    adj_tempo: float

def validate(team: Team) -> None:
    if not team.name.strip():
        raise ValueError("Team name required")
    if not all(math.isfinite(v) for v in (team.adj_off, team.adj_def, team.adj_tempo)):
        raise ValueError("Ratings must be finite")
    if not (50 <= team.adj_off <= 160 and 50 <= team.adj_def <= 160 and 45 <= team.adj_tempo <= 90):
        raise ValueError("Ratings outside reasonable bounds; verify source")

def simulate(away: Team, home: Team, *, n: int = 10000, seed: int = 20261101,
             baseline: float = D1_BASELINE, home_advantage: float = 0.0,
             pace_sd: float = 4.0, efficiency_sd: float = 10.0) -> dict:
    """Return model assumptions and simulated full-game scores.

    Matchup efficiency = team adjusted offense * opponent adjusted defense / D-I baseline.
    Shared game pace is sampled once per run. Offense-specific game variation
    is sampled separately. Gaussian score noise is a provisional approximation;
    replace only after held-out calibration.
    """
    validate(away); validate(home)
    if not (1 <= n <= 100000):
        raise ValueError("n must be between 1 and 100000")
    if not all(math.isfinite(x) for x in (baseline, home_advantage, pace_sd, efficiency_sd)):
        raise ValueError("Simulation parameters must be finite")
    if baseline <= 0 or pace_sd < 0 or efficiency_sd < 0:
        raise ValueError("Invalid simulation parameters")
    pace = (away.adj_tempo + home.adj_tempo) / 2
    away_eff = away.adj_off * home.adj_def / baseline
    home_eff = home.adj_off * away.adj_def / baseline
    rng = random.Random(seed)
    scores = []
    for _ in range(n):
        possessions = max(35.0, rng.gauss(pace, pace_sd))
        a_eff = max(0.0, rng.gauss(away_eff, efficiency_sd))
        h_eff = max(0.0, rng.gauss(home_eff, efficiency_sd))
        a = max(0, round(possessions * a_eff / 100))
        h = max(0, round(possessions * h_eff / 100 + home_advantage))
        scores.append((a, h))
    away_scores = sorted(a for a, _ in scores)
    home_scores = sorted(h for _, h in scores)
    totals = sorted(a + h for a, h in scores)
    margins = sorted(h - a for a, h in scores)
    def pct(v, q):
        return v[round((len(v)-1)*q)]
    def avg(v):
        return sum(v) / len(v)
    return {
        "model_version": MODEL_VERSION, "created_utc": datetime.now(timezone.utc).isoformat(),
        "away": asdict(away), "home": asdict(home), "runs": n, "seed": seed,
        "assumptions": {"d1_baseline": baseline, "home_advantage_points": home_advantage,
                        "pace_sd": pace_sd, "efficiency_sd": efficiency_sd,
                        "uncertainty_calibrated": False},
        "expected_possessions": pace,
        "expected_efficiency": {"away": away_eff, "home": home_eff},
        "mean_score": {"away": avg(away_scores), "home": avg(home_scores)},
        "mean_total": avg(totals), "mean_home_margin": avg(margins),
        "home_win_fraction": sum(h > a for a, h in scores) / n,
        "tie_fraction": sum(h == a for a, h in scores) / n,
        "interval_80": {"away": [pct(away_scores,.1), pct(away_scores,.9)],
                        "home": [pct(home_scores,.1), pct(home_scores,.9)],
                        "total": [pct(totals,.1), pct(totals,.9)],
                        "home_margin": [pct(margins,.1), pct(margins,.9)]},
        "warning": "Experimental, uncalibrated simulation; win fraction is not a validated betting probability."
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Experimental 10,000-run NCAAB simulator")
    p.add_argument("--input", required=True, help="JSON containing away and home team ratings")
    p.add_argument("--seed", type=int, default=20261101)
    p.add_argument("--runs", type=int, default=10000)
    args = p.parse_args()
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    print(json.dumps(simulate(Team(**data["away"]), Team(**data["home"]),
                              n=args.runs, seed=args.seed,
                              baseline=data.get("d1_baseline", D1_BASELINE),
                              home_advantage=data.get("home_advantage", 0.0)), indent=2))
