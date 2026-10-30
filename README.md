# DOC'S NCAAB WAR ROOM

GitHub Pages research dashboard for 2026–27 men's college basketball.

- Date-based ESPN Division I scoreboards, Central times, search and team directory.
- Current/prior season inspection, last ten completed games strictly before the analysis cutoff, scored/allowed and available actual first-half scoring.
- Transparent, uncalibrated scoring baseline; three observed games required per team. No fabricated probabilities, confidence badges or qualifications.
- ESPN game reports and actual player box scores. Missing injury/lineup information remains unavailable.
- Browser-persistent pregame snapshots, JSON export, postgame score-error grading. First snapshot cannot be overwritten in the UI.
- GitHub Actions refreshes team and slate snapshots every three hours; successful files survive partial outages. Actions must be enabled. Scheduled runs can be delayed by GitHub.

## Run
Serve this directory using `python -m http.server 8000`. Open http://localhost:8000. No dependencies or secrets needed. Live ESPN access is required for team schedules/game summaries; scoreboard and directory have timestamped repository fallbacks. Upcoming matchup schedules and the latest three completed game half scores also have repository fallbacks. Browser CORS/source outages can still block uncached analysis.

## Verification
`node --check app.js`
`node scripts/check-model.cjs`
`python -m py_compile scripts/refresh.py`

## Outstanding before calling this a complete forecasting system
NCAA membership reconciliation; possession-based opponent-adjusted efficiency; schedule-strength adjustment; current roster/availability and expected-minute inputs; historical pregame backtest with calibration and held-out evaluation; reliable sportsbook period/player lines; shared server-side immutable forecast archive. This release provides research and a descriptive baseline, not a validated betting model. Browser receipts are local, not account-synced or tamper-proof. No 1Q markets: NCAA men's basketball plays halves.
