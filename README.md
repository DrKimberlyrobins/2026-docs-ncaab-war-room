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

## Kambi pregame quote history

New collector runs retain append-only observations under
`data/kambi/history/<Central game date>/<UTC collection run>.json`.
Each observation keeps the offering, region, market criterion, both quoted
prices, provider update time when supplied, and the actual retrieval time.
Only successful exact event matches with open pregame offers collected strictly
before both scheduled start times enter this history. Existing daily snapshots
and projections keep their original formats. The collection uses the existing
30-minute best-effort workflow.

These are observed quotes. The earliest observed quote is not a verified
opener. The latest observation alone does not establish a verified closing
price. No older rolling snapshot is backfilled into the forward history.

`python scripts/closing_value.py quotes.json --max-age-seconds 120` evaluates
a manually supplied pair with `entry`, `close` and `start` keys. Supply the
same event, sportsbook, region, period, rules, kind, market, selection and
direction on both quotes, with a source reference, American price, and
timezone-aware `observedAt`. Spreads use the selected team's signed line.
Totals and props use the quoted threshold. Moneylines omit the line. Mark
`close.verifiedClose` only when independently confirmed and supply
`close.oppositePrice` only for the exact opposite side at the same threshold.
The command reports no-vig closing value only when both comparable prices
exist. It does not infer a verified close from the rolling Kambi history.
