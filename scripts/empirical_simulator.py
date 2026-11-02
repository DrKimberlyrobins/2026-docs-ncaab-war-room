"""Ten-thousand-run empirical score bootstrap from completed ESPN games.

No KenPom/Torvik ratings are assumed. Uses only the pre-tipoff score samples
provided by prepare.py. Estimates are descriptive, not calibrated probabilities.
"""
import random
from datetime import datetime, timezone

def simulate_scores(away_games, home_games, *, n=10000, seed=0):
    if len(away_games) < 3 or len(home_games) < 3:
        raise ValueError("At least three completed games per team required")
    for rows in (away_games, home_games):
        if any(not isinstance(r.get("pf"), (int, float)) or
               not isinstance(r.get("pa"), (int, float)) for r in rows):
            raise ValueError("Missing actual score")
    rng = random.Random(seed)
    scores = []
    for _ in range(n):
        a_off = rng.choice(away_games)["pf"]
        a_def = rng.choice(away_games)["pa"]
        h_off = rng.choice(home_games)["pf"]
        h_def = rng.choice(home_games)["pa"]
        a = max(0, round((a_off + h_def) / 2))
        h = max(0, round((h_off + a_def) / 2))
        scores.append((a, h))
    aa = sorted(a for a, _ in scores)
    hh = sorted(h for _, h in scores)
    tt = sorted(a+h for a, h in scores)
    mm = sorted(h-a for a, h in scores)
    def bounds(v):
        return [v[int(.1*(n-1))], v[int(.9*(n-1))]]
    return {
        "model_version": "espn-score-bootstrap-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "runs": n, "seed": seed,
        "method": "Bootstrap completed ESPN scores: (sampled team points scored + sampled opponent points allowed)/2.",
        "data_basis": {"away_games": len(away_games), "home_games": len(home_games)},
        "mean_score": {"away": sum(aa)/n, "home": sum(hh)/n},
        "mean_total": sum(tt)/n, "mean_home_margin": sum(mm)/n,
        "home_win_fraction": sum(h>a for a,h in scores)/n,
        "tie_fraction": sum(h==a for a,h in scores)/n,
        "interval_80": {"away": bounds(aa), "home": bounds(hh),
                        "total": bounds(tt), "home_margin": bounds(mm)},
        "warning": "Empirical score bootstrap, not possession-adjusted, strength-of-schedule-adjusted, or calibrated. Not a verified betting probability."
    }
