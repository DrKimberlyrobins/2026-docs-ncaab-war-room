# Automatic daily matchup calculator

The calculator is now device-independent: it loads prepared results from `data/calculator/daily/YYYY-MM-DD.json`. Opening it on a new phone or computer requires no imported ratings, API key, localStorage, or manual input. The initial game date is today in America/Chicago.

## Automatic refresh

`Refresh automatic matchup calculator` runs every three hours at minute 7 UTC, after changes to its source/configuration, or through workflow_dispatch. `scripts/automatic_matchups.py` retrieves the public KenPom homepage once, validates the season and complete sequential team rankings, retrieves ESPN's team directory, and prepares today plus four upcoming dates. The resulting data commit triggers `Publish War Room`. Only derived matchup scores and source provenance are committed; the underlying KenPom ratings table is not published.

Team identities must match unique normalized institutional names or a reviewed ESPN-ID alias in `config/kenpom-team-aliases.json`. There is no fuzzy assignment. Games involving teams absent from KenPom's ratings remain visible with an explanation, including non-Division-I opponents. An empty scoreboard is labeled as a source response, not certified full coverage.

A failed retrieval preserves previous successful daily results and updates `data/calculator/health.json`. The page displays health, ratings retrieval time, and a warning when ratings are over 24 hours old. No login, cookies, API keys, or anti-bot bypasses are used. The old authenticated API script remains available for optional future use but does not power the automatic page.

## Model

Possessions = both adjusted tempos added − configured national tempo.
Matchup efficiency = team adjusted offense + opponent adjusted defense − configured national efficiency.
Points = possessions × matchup efficiency / 100.

National baselines remain the explicit dated November 1, 2026 screenshot values in `config/kenpom-calculator.json`: efficiency 106 and tempo 71.5. These are model configuration, not automatically retrieved national averages. Home advantage remains zero. Injuries, first-half forecasts and calibrated win probabilities are not modeled. Refresh-time calculations are not frozen pregame receipts and must not be graded as such.

## Publication

GitHub Pages Source must be GitHub Actions. `Publish War Room` packages the public site and serializes deployment without cancelling an active run. Imported browser ratings from the previous version are no longer used. The public page contains no paste box or editable rating forms.

## First-half calculator

Every prepared matchup now includes a `firstHalf` projection when both teams have at least three usable completed games. `scripts/first_half.py` reads actual first and second regulation period scores from the existing ESPN schedule/summary evidence cache, with games strictly before the earlier of retrieval time and the selected tipoff. It examines up to ten recent completed games per team. Exhibitions, unfinished games, missing halves and invalid period totals are excluded.

Each team's profile uses current-season evidence when three games are available; otherwise the prior season is explicitly labeled. First-half scoring share = total first-half points scored / total regulation points scored. Allowing share uses actual opponent points in the same manner. Overtime periods are excluded from both denominators. Away 1H points = current full-game away projection × average of away scoring share and home allowing share; reverse teams for home. Total and margin follow from the two projected scores. No fixed 50% substitute is used when evidence is missing. This timing model is unvalidated and does not establish current rotation continuity from prior-season samples.

The automatic calculator also refreshes after the ESPN evidence workflow completes, so newly cached halves feed the next calculation. Source sample sizes, seasons, actual 1H averages and evidence retrieval links appear inside each game's 1H evidence panel. Both 1H and full-game rows remain visible, with 1H first. No manual input is required.

## Independent Kambi markets

`scripts/kambi_markets.py` uses the same offering as the NFL collector: `pivusmsrl-bil`, region `US-MS`, Kambi Offering v2018. It discovers NCAAB events then fetches exact event bet offers. The Refresh Kambi markets workflow runs at minutes 3 and 33 each hour (GitHub scheduling may be delayed); its completion triggers Pages publication. No user entry or API key is required.

ESPN institutional identities and a 15-minute tip-time tolerance match both teams uniquely; neutral-court home/away reversals are supported. Ambiguous events are withheld. Criterion IDs AND observed labels whitelist full-game and first-half spreads, match totals, and moneylines. Team totals, props and alternate lines cannot substitute. Only OPEN outcomes with exact event/offer IDs are accepted; a unique source-marked main line is preferred. Kambi line units are divided by 1,000; American prices are preserved. No odds are inferred.

The shared `kambi.js` comparison panel appears on the Game Room and calculator. It compares the projection already shown on that page: the Game Room's descriptive scoring baseline or the calculator's KenPom-based model. Those are distinct models. A spread difference is projected home margin + home handicap; a total difference is projected total − market total. This is a point difference, not expected value or a qualified wager. No model moneyline probability is available.

The collector writes only `data/kambi/` and never imports forecasting code. Previous snapshots survive source failures, with health and retrieval times displayed. Comparisons are withheld once the snapshot is over one hour old or scheduled tipoff has passed. Source-offered lines remain historical evidence. Missing first-half markets stay NO MARKET. NFL files are unchanged.

## Automatic pregame archive and postgame review

The calculator has Previous, Today, Upcoming, and Saved receipts navigation, also linked from the Game Room. Today opens the Central date; Upcoming starts tomorrow with the prepared four-day date range. Previous and Saved receipts browse a shared GitHub archive, filter by saved date/team, and open each game's comparison.

`Archive matchup receipts` runs after evidence, calculator, and Kambi updates and at minutes 12/42 each hour. It checks a live ESPN pregame state and future scheduled tipoff before exclusively creating `data/archive/games/{ESPN_ID}.json`. The original `snapshot` is never replaced: it retains KenPom-based full-game and 1H scores, settings, model metadata, timing samples/source receipts, the Game Room baseline, and fresh available Kambi offers. A stale ratings snapshot (over 24h) cannot be archived as a fresh forecast. Quotes over one hour old are omitted. A market that opens later is saved separately once, before tipoff, without replacing earlier prices or forecasts. An event without a saved pregame projection is never reconstructed as a pregame prediction after starting.

Actual completed ESPN results live in the separate `result` object, with source and retrieval time. Full game includes overtime; 1H uses actual period scores only. The review shows original vs. actual team scores, totals, margin, and signed forecast errors. Each saved market outcome is settled separately as WIN/LOSS/PUSH; this does not claim a user placed a wager. A 1H draw-no-bet moneyline tie pushes. Missing halftime evidence stays pending. Results are fetched only after the scheduled start and only accepted once the source says completed. Saved files and their GitHub history persist across dates and devices; existing browser-local War Room receipts are retained separately.

## Public pregame reports

`reports.js` adds a Pregame Reports panel to the Game Room, prepared matchup dialogs, and calculator. `Refresh pregame reports` checks connected public feeds at minutes 22/52 each hour. The initial local sources are VU Hoops, Philadelphia Sports Now, A Sea of Red, and Pantherstooth. ESPN's men's basketball news feed provides additional national/syndicated headlines matched by sport-specific team IDs. Dedicated local coverage is not yet connected for all 365 teams. The panel shows source type, named byline where supplied, publication date/time, original retrieval/review time, and links. Missing coverage never establishes health or availability.

The six initial reviewed articles in `config/reviewed-reports.json` cover both opening matchups, including Notre Dame and Liberty official releases. Summaries are deliberately dated, scoped to exact events, and expire. Reported injury uncertainty, writer expectations, writer analysis, and official team information have different labels. A preview's proposed starters are never treated as a confirmed lineup. New RSS/API items remain headline-only until reviewed; there is no automated claim that a headline establishes a player's status. Date-only publication metadata is displayed as date-only. Source failures retain previously fetched feed items with their original timestamps and visible error status. Only articles from the preceding 14 days and published before the matchup tipoff are eligible; unrelated sports and women's basketball are excluded. No account credentials or subscription bypass is used.

Reports never enter the score formula. The archive retains separate append-only report evidence before tipoff, including the actual save time. Existing frozen projections and Kambi quotes are unchanged. Archived reports are rendered from saved evidence rather than today's reporting feed. Newly reviewed updates can be retained as distinct evidence versions without replacing earlier information.
