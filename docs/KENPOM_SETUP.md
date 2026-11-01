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
