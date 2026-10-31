# Daily 10,000-run simulation data contract

The daily preparation job runs the independent simulator for **future** games only when both teams have sourced adjusted ratings. It does not scrape KenPom or claim access to any paid provider.

Supply `data/ratings.json` using an authorized, documented source. Use ESPN numeric team IDs as keys:

```json
{
  "source": "NAME AND VERSION OF AUTHORIZED RATING PROVIDER",
  "fetchedAt": "2026-10-31T12:00:00+00:00",
  "teams": {
    "123": {"adj_off": 110.0, "adj_def": 102.0, "adj_tempo": 69.0}
  }
}
```

The numbers above are **illustrative schema values only**, not actual team ratings. Never publish them as game evidence. Adjusted offensive and defensive efficiency must be measured in points per 100 possessions; adjusted tempo is possessions per game. Source permission and mapping to ESPN team IDs must be checked before ingesting any real feed. Avoid publishing restricted subscription data in this public repository.

Run `python scripts/prepare.py` to create `data/daily/YYYY-MM-DD.json`. Each matchup includes `simulation` when inputs are available or `simulationStatus` explaining why it is unavailable. The dashboard displays simulation output and preserves the existing descriptive baseline separately. The simulator uses a provisional D-I baseline of 106, zero default home advantage and uncalibrated noise; its win fraction is **not** a validated betting probability.

Run `python -m unittest discover -s scripts -p 'test_*simulat*.py'` for the simulator and data-contract tests. Historical backtesting, calibration, data-provider integration, and Google Sheets synchronization remain outstanding.
