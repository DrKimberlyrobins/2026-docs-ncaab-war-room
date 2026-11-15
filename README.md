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


## Permanent mathematical model specification (draft v1; not yet activated)

**Purpose:** Preserve the mathematics, assumptions and evidence requirements across seasons. This specification is a proposed replacement engine; the current production calculator may use different formulas. Do not present these equations as validated predictions until implemented, unit-tested, backtested and calibrated.

**Inputs:** For each team and date, adjusted offensive efficiency AdjO (points per 100 possessions), adjusted defensive efficiency AdjD (points allowed per 100 possessions), adjusted tempo AdjT (possessions per 40 minutes), dated national efficiency baseline L (points per 100 possessions), home/away designation, rating source, rating vintage and actual retrieval timestamp. Only use inputs available strictly before scheduled tipoff for frozen forecasts. Never fill missing KenPom values with fabricated numbers.

**Initial full-game model (neutral court, uncalibrated):**
- possessions = (AdjT_away + AdjT_home) / 2.
- matchup_PPP_away = (AdjO_away * AdjD_home) / (100 * L).
- matchup_PPP_home = (AdjO_home * AdjD_away) / (100 * L).
- projected_away = possessions * matchup_PPP_away.
- projected_home = possessions * matchup_PPP_home.
- projected_total = projected_away + projected_home.
- projected_home_margin = projected_home - projected_away.
- Projected team totals are the individual projected scores.
- Home-court, schedule, lineup and injury adjustments are explicitly **not** included in this initial neutral-court version. Any future adjustment must have its own version, data provenance, and held-out validation. Do not silently apply an arbitrary points bonus.

**First-half model:** Do not use a fixed 50% split. Use each team's observed regulation first-half scored/allowed share and (when reliably available) half-specific possession rates, with a predeclared minimum sample and explicit season label. A candidate first-half estimate may apply a documented, opponent-matched half-share to the full-game expected score. Calibrate and backtest against actual 1H outcomes separately. Exclude overtime from regulation first-half evidence. Derive second-half estimates consistently so projected 1H + projected 2H = projected regulation total, or clearly label differences in model definitions.

**Market comparison:** Market inputs from Kambi and Kalshi are comparison data, never projection inputs. Preserve provider, market, selection, period, quoted threshold, price, fees when applicable, source update time, collection time, tipoff time and matching confidence. For totals, projected_total - market_total; for home spread, compare projected_home_margin to the market-implied home margin with a consistent sign convention. A numerical point difference is not automatically a profitable bet or a calibrated probability.

**Immutable pregame receipt:** Save game ID, both team IDs, source versions, source timestamps, calculation timestamp, tipoff, every raw model input, all intermediate computations (possessions, each PPP, first-half timing factors), model version, forecast outputs, matched market quotes and market timestamps. Store receipts in a shared append-only archive rather than only browser storage. Never replace an old receipt after a model revision. Grade against final regulation and full-game scores separately; record MAE, bias, coverage, and out-of-sample performance by season and market.

**Versioning:** Any formula or assumption change creates a new model version. Old predictions must remain reproducible from their original inputs. Do not claim this draft is operational until the connected ratings source, persistence pipeline and tests prove it.


## Complete-game intelligence scope (Nov 2026 requirement)

This War Room must not prioritize first-half markets at the expense of full-game coverage. For **every automatically preloaded matchup**, display a consistent, inspectable research report:

1. **Full game:** projected away/home regulation scores, projected winner and margin, market spreads (both sides), total, and both full-game team totals.
2. **First half:** projected away/home 1H scores, 1H margin, 1H total, and each team's 1H team total.
3. **Second half:** projected away/home 2H scores, 2H margin, 2H total, and both 2H team totals. Reconcile 1H + 2H to regulation full-game estimates; clearly separate 2H live/in-game forecasts from pregame forecasts.
4. **Efficiency and matchup evidence:** each team's dated AdjO, AdjD, AdjT, strength-of-schedule context if available, expected possessions, matchup PPP, scoring and allowed profiles, home/away, rest, and data completeness. Missing information stays visibly missing.
5. **Market intelligence:** comparable Kambi and Kalshi market snapshots by exact game, period, side, line, price and timestamp. Compute point differences with explicit sign conventions and separate probabilities/EV only when calibrated and fee-aware.
6. **Evidence and audit:** source provenance, as-of timestamps, model version, intermediate calculations, sample sizes, frozen pregame receipts, results, and historical out-of-sample grading by market and period.

**Daily navigation:** Previous, Today, Upcoming, and Saved must work from automatically collected date-indexed slates without user imports. Maintain the light-background colorful design. Preserve historical data and collector integrations. A scope specification is not proof these capabilities are already implemented or validated.
