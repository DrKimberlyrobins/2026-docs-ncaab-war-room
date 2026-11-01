"""Fetch the official KenPom API and calculate every FanMatch matchup.

No passwords, browser cookies, scraping, or fuzzy team-name matching.
National averages are explicit dated configuration, not inferred live data.
"""
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
API = 'https://kenpom.com/api.php'


def rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get('data'), list):
        return payload['data']
    raise ValueError('Unexpected API response shape; expected records array')


def fetch(endpoint, key, **params):
    url = API + '?' + urllib.parse.urlencode({'endpoint': endpoint, **params})
    req = urllib.request.Request(url, headers={
        'Authorization': 'Bearer ' + key, 'Accept': 'application/json',
        'User-Agent': 'Docs-NCAAB-Calculator/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read(10_000_001)
            if len(raw) > 10_000_000:
                raise ValueError('API response exceeds size limit')
            result = rows(json.loads(raw))
    except urllib.error.HTTPError as exc:
        # Do not log response bodies or request headers containing credentials.
        raise ValueError(f'KenPom {endpoint}: HTTP {exc.code}') from None
    return result, {'url': url, 'fetchedAt': datetime.now(timezone.utc).isoformat()}


def finite(value):
    if isinstance(value, bool) or value is None or value == '':
        raise ValueError('Missing numeric input')
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Nonfinite numeric input')
    return result


def rating(row, season):
    if int(row['Season']) != season:
        raise ValueError('Ratings season mismatch')
    off, defense, tempo = (finite(row[k]) for k in ('AdjOE', 'AdjDE', 'AdjTempo'))
    if not (50 <= off <= 160 and 50 <= defense <= 160 and 45 <= tempo <= 90):
        raise ValueError('Rating outside supported bounds')
    return {'offense': off, 'defense': defense, 'tempo': tempo,
            'dataThrough': row.get('DataThrough')}


def calculate(away, home, config, location):
    avg_eff, avg_tempo = (finite(config[k]) for k in ('nationalEfficiency', 'nationalTempo'))
    if not (50 <= avg_eff <= 160 and 45 <= avg_tempo <= 90):
        raise ValueError('National averages outside supported bounds')
    if location not in ('Home', 'Neutral', 'Semi-Home'):
        raise ValueError('Unknown game location')
    possessions = away['tempo'] + home['tempo'] - avg_tempo
    ae = away['offense'] + home['defense'] - avg_eff
    he = home['offense'] + away['defense'] - avg_eff
    if possessions <= 0 or ae <= 0 or he <= 0:
        raise ValueError('Invalid calculated pace or efficiency')
    advantage = 0.0 if location == 'Neutral' else finite(config['homeAdvantagePoints'])
    # Split the margin adjustment equally, preserving the projected total.
    a = possessions * ae / 100 - advantage / 2
    h = possessions * he / 100 + advantage / 2
    return {'away': a, 'home': h, 'total': a + h, 'homeMargin': h - a,
            'possessions': possessions, 'awayEfficiency': ae, 'homeEfficiency': he,
            'homeAdvantagePoints': advantage}


def build(ratings, games, config, date):
    season = int(config['season'])
    by_name = {}
    for row in ratings:
        name = row.get('TeamName')
        if not isinstance(name, str) or not name.strip() or name in by_name:
            raise ValueError('Missing or duplicate KenPom team name')
        by_name[name] = rating(row, season)
    if len(by_name) < 300:
        raise ValueError('Incomplete ratings response: fewer than 300 teams')
    output, ids = [], set()
    for game in games:
        gid = str(game['GameID'])
        if gid in ids:
            raise ValueError('Duplicate game ID')
        ids.add(gid)
        if game['DateOfGame'] != date or int(game['Season']) != season:
            raise ValueError('FanMatch date or season mismatch')
        item = {'id': gid, 'awayName': game['Visitor'], 'homeName': game['Home'],
                'location': game.get('Location'), 'kenpomProjection': {
                    'away': game.get('VisitorPred'), 'home': game.get('HomePred'),
                    'possessions': game.get('PredTempo')}, 'model': None}
        try:
            away, home = by_name[game['Visitor']], by_name[game['Home']]
            item.update(awayRatings=away, homeRatings=home,
                        model=calculate(away, home, config, game.get('Location')))
        except (KeyError, ValueError) as exc:
            item['error'] = str(exc)
        output.append(item)
    return {'date': date, 'season': season, 'config': config,
            'ratedTeams': len(by_name), 'matchups': output,
            'calculatedGames': sum(x['model'] is not None for x in output)}


def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def main():
    now = datetime.now(timezone.utc)
    date = now.astimezone(ZoneInfo('America/Chicago')).date().isoformat()
    health = ROOT / 'data/kenpom/health.json'
    key = os.environ.get('KENPOM_API_KEY', '').strip()
    if not key:
        write(health, {'status': 'API_KEY_REQUIRED', 'checkedAt': now.isoformat(),
                      'message': 'Add the KENPOM_API_KEY GitHub Actions repository secret.'})
        print('KenPom connection awaiting KENPOM_API_KEY repository secret.')
        return
    try:
        config = json.loads((ROOT / 'config/kenpom-calculator.json').read_text())
        season = int(date[:4]) + (int(date[5:7]) >= 7)
        if config['season'] != season:
            raise ValueError('Update national averages and configured season before refreshing')
        ratings, rs = fetch('ratings', key, y=season)
        games, gs = fetch('fanmatch', key, d=date)
        payload = build(ratings, games, config, date)
        payload.update(preparedAt=datetime.now(timezone.utc).isoformat(), sources=[rs, gs],
                       status='READY' if payload['calculatedGames'] == len(games) else 'PARTIAL',
                       evidenceLabel='Retrieval snapshot; not certified as pre-tipoff evidence')
        # Each successful refresh is retained; do not replace historical evidence.
        archive = ROOT / 'data/kenpom/snapshots' / date / (now.strftime('%H%M%S%f') + '.json')
        write(archive, payload)
        write(ROOT / f'data/kenpom/daily/{date}.json', payload)
        write(health, {'status': payload['status'], 'checkedAt': payload['preparedAt'],
                       'date': date, 'games': len(games), 'calculated': payload['calculatedGames']})
        print(f"KenPom: {payload['calculatedGames']}/{len(games)} matchups calculated for {date}")
        if payload['status'] == 'PARTIAL':
            raise ValueError('Some matchups could not be calculated; inspect daily output')
    except Exception as exc:
        write(health, {'status': 'SOURCE_ERROR', 'checkedAt': now.isoformat(),
                      'message': str(exc), 'date': date})
        raise SystemExit('KenPom refresh failed; previous successful data retained. ' + str(exc))


if __name__ == '__main__':
    main()
