# KenPom matchup calculator

Open `calculator/` from the War Room navigation. The manual calculator works immediately. Automated calculations use KenPom's official API, with both ratings and FanMatch team names coming from the same provider; no ESPN name guessing is involved.

## Activate live data

1. Obtain a KenPom API bearer key with ratings and FanMatch access. A website subscription or successful website login does not by itself prove API access. Official documentation: https://kenpom.com/api-documentation.php . Ask KenPom about API access if your account does not provide a key; no access price or entitlement is assumed here.
2. In this repository open Settings → Secrets and variables → Actions → New repository secret. Name it `KENPOM_API_KEY`, and place the API key in its value. Do not put passwords, API keys or cookies in code, page inputs, issues, or chat.
3. Open Actions → Refresh KenPom matchup calculator → Run workflow. Scheduled refreshes run every three hours at minute 7 UTC. The selected game date is calculated in America/Chicago.
4. Verify `data/kenpom/health.json` reports READY and the calculator displays the source retrieval timestamp. An empty FanMatch list is displayed as a source response, not a coverage guarantee.

The key is used only by Actions in the Authorization header. The site never receives it. The script fetches `/api.php?endpoint=ratings&y=2027` and `/api.php?endpoint=fanmatch&d=YYYY-MM-DD`. The ending season year is used. FanMatch documents current and past dates only, so this job publishes today's slate; retained dates remain browsable.

## Formula and national averages

`config/kenpom-calculator.json` supplies explicitly dated national efficiency and tempo averages from Doc's November 1, 2026 screenshots: 106.0 and 71.5. They are not claimed to update from the API. Update that configuration when the averages change. The documented API does not expose a national-average endpoint. Do not substitute an unweighted mean of team ratings and call it KenPom's national average.

Possessions = away AdjTempo + home AdjTempo − national tempo.
Away efficiency = away AdjOE + home AdjDE − national efficiency; reverse teams for home.
Projected points = efficiency × possessions / 100.
Home advantage is configurable and currently zero for all games; home court is not modeled. This preserves the exact baseline discussed with Doc. No claim of calibration, injury adjustment, first-half accuracy, or win probability is made. KenPom's own predicted scores and possessions are displayed separately, not fed into our formula.

Successful retrievals retain immutable timestamped calculation snapshots under `data/kenpom/snapshots/`. Daily display files are refreshed. These are retrieval snapshots, not certified pre-tipoff receipts; the FanMatch response does not supply tipoff times. No after-the-fact snapshot should be graded as an original pregame forecast.

Failures preserve the last successful daily data and publish a separate health status. Missing team ratings or unexpected response shapes remain explicit. No screenshots are treated as a live feed.
