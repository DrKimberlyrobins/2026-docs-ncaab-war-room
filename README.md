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

## Daily matchup preparation
Every event returned for a selected date appears on its own card with precomputed full-game and first-half baselines, season labels, source retrieval times and preparation counts. The scheduled GitHub workflow prepares all upcoming source slates every three hours. The dashboard reads snapshot data from the repository directly, so data-only commits do not depend on a Pages rebuild. For dates without a prepared snapshot, the browser prepares all returned matchups in a bounded queue. Current-season samples are preferred; explicitly labeled prior-season references are used when fewer than three current-season games are available. Missing sources remain listed, with unavailable fields. These baselines remain unvalidated.

`python scripts/check-daily.py` checks season selection, event retention, and future/live exclusions.

## Canonical membership
The All Teams directory uses the NCAA's sport-specific 2026–27 Division I men's basketball membership roster: 365 unique institution IDs. Membership count and duplicates are checked during refresh. ESPN's 362-team discovery response is not used as the canonical directory. Scoreboard event counts describe games on selected dates, not total membership.
