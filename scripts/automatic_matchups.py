"""Prepare device-independent matchup scores from public KenPom ratings.

One public ratings request per refresh; no login, cookies or bypass logic.
Only derived matchup results are published, not the ratings table.
"""
import json
import re
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo
from kenpom_calculator import calculate, finite
from first_half import attach

ROOT = Path(__file__).resolve().parents[1]
KENPOM = 'https://kenpom.com/'
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball'

class RatingsTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.headings = []
        self.heading = None
    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row = []
        elif tag == 'td' and self.row is not None: self.cell = []
        elif tag == 'h2': self.heading = []
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
        if self.heading is not None: self.heading.append(data)
    def handle_endtag(self, tag):
        if tag == 'td' and self.cell is not None:
            self.row.append(''.join(self.cell).strip()); self.cell = None
        elif tag == 'tr' and self.row is not None:
            if self.row: self.rows.append(self.row)
            self.row = None
        elif tag == 'h2' and self.heading is not None:
            self.headings.append(''.join(self.heading).strip()); self.heading = None

def parse_ratings(html, season):
    parser = RatingsTable(); parser.feed(html)
    if not any(re.search(r'\b' + str(season) + r'\b.*Pomeroy College Basketball Ratings', h) for h in parser.headings):
        raise ValueError('KenPom ratings heading does not match requested season')
    teams = {}
    ranks = set()
    for cells in parser.rows:
        if len(cells) != 21 or not cells[0].isdigit(): continue
        rank = int(cells[0]); name = cells[1]
        if name in teams or rank in ranks: raise ValueError('Duplicate source team or rank')
        off, defense, tempo = (finite(cells[i]) for i in (5, 7, 9))
        if not (50 <= off <= 160 and 50 <= defense <= 160 and 45 <= tempo <= 90):
            raise ValueError('Source rating outside supported bounds')
        if not all(cells[i].isdigit() for i in (6, 8, 10)):
            raise ValueError('KenPom rank columns changed; parser review required')
        teams[name] = dict(offense=off, defense=defense, tempo=tempo)
        ranks.add(rank)
    if len(teams) < 300 or ranks != set(range(1, len(teams)+1)):
        raise ValueError('Incomplete public KenPom ratings table')
    return teams

def normalized(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    value = re.sub(r'[^a-z0-9 ]', '', value)
    # Only the final St./State suffix is equivalent; Saint names are preserved.
    value = re.sub(r'\bst$', 'state', value.strip())
    return re.sub(r'\s+', '', value)

def match_team(team, directory, ratings, reviewed):
    tid = str(team.get('id', ''))
    if tid in reviewed:
        name = reviewed[tid]
        if name not in ratings: raise ValueError('Reviewed source identity absent: ' + name)
        return name
    full = directory.get(tid, {})
    names = {normalized(x.get(k, '')) for x in (team, full)
             for k in ('location', 'shortDisplayName', 'displayName') if x.get(k)}
    matches = [name for name in ratings if normalized(name) in names]
    if len(matches) != 1: return None
    return matches[0]

def build(events, directory, ratings, config, reviewed):
    output = []
    for event in events:
        comp = (event.get('competitions') or [{}])[0]
        a = next((x for x in comp.get('competitors', []) if x.get('homeAway') == 'away'), None)
        h = next((x for x in comp.get('competitors', []) if x.get('homeAway') == 'home'), None)
        item = {'id': str(event['id']), 'date': event.get('date'),
                'awayName': (a or {}).get('team', {}).get('displayName', 'Away team unavailable'),
                'homeName': (h or {}).get('team', {}).get('displayName', 'Home team unavailable'),
                'awayId': str((a or {}).get('team', {}).get('id', '')),
                'homeId': str((h or {}).get('team', {}).get('id', '')),
                'location': 'Neutral' if comp.get('neutralSite') else 'Home',
                'model': None}
        if not a or not h:
            item['error'] = 'Schedule missing team identity'
        else:
            an = match_team(a['team'], directory, ratings, reviewed)
            hn = match_team(h['team'], directory, ratings, reviewed)
            item['matchedTeams'] = {'away': an, 'home': hn}
            if an and hn:
                item['model'] = calculate(ratings[an], ratings[hn], config, item['location'])
            else:
                missing = [item['awayName'] if not an else '', item['homeName'] if not hn else '']
                item['error'] = 'Source identity or D-I rating unavailable: ' + ', '.join(filter(None, missing))
        output.append(item)
    return output

def fetch(url, text=False):
    req = urllib.request.Request(url, headers={'User-Agent': 'Docs-NCAAB-Research/1.0', 'Accept': 'text/html' if text else 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as response:
        raw = response.read(10_000_001)
        if len(raw) > 10_000_000: raise ValueError('Source exceeds size limit')
    return raw.decode('utf-8') if text else json.loads(raw)

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)

def main():
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo('America/Chicago')).date()
    season = today.year + (today.month >= 7)
    health = ROOT / 'data/calculator/health.json'
    try:
        config = json.loads((ROOT / 'config/kenpom-calculator.json').read_text())
        if config['season'] != season: raise ValueError('Configured season needs administrative review')
        ratings = parse_ratings(fetch(KENPOM, text=True), season)
        fetched = datetime.now(timezone.utc).isoformat()
        source = fetch(ESPN + '/teams?groups=50&limit=1000')
        directory = {str(entry['team']['id']): entry['team'] for sport in source['sports']
                     for league in sport['leagues'] for entry in league['teams']}
        reviewed_path = ROOT / 'config/kenpom-team-aliases.json'
        reviewed = json.loads(reviewed_path.read_text()) if reviewed_path.exists() else {}
        if len(set(reviewed.values())) != len(reviewed): raise ValueError('Duplicate reviewed team mapping')
        days = []; failures = []
        for offset in range(5):
            day = today + timedelta(days=offset)
            url = ESPN + '/scoreboard?groups=50&limit=1000&dates=' + day.strftime('%Y%m%d')
            try:
                slate = fetch(url)
                if not isinstance(slate.get('events'), list): raise ValueError('Schedule events missing')
                stamp = datetime.now(timezone.utc).isoformat()
                matchups = build(slate['events'], directory, ratings, config, reviewed)
                for matchup, event in zip(matchups, slate['events']):
                    attach(matchup, event, season, stamp)
                payload = {'date': day.isoformat(), 'preparedAt': stamp,
                           'ratingsFetchedAt': fetched, 'ratingSource': KENPOM,
                           'scheduleSource': url, 'scheduleFetchedAt': stamp,
                           'season': season, 'ratedTeams': len(ratings), 'config': config,
                           'calculatedGames': sum(m['model'] is not None for m in matchups),
                           'firstHalfGames': sum(m.get('firstHalf') is not None for m in matchups),
                           'matchups': matchups, 'evidenceLabel': 'Calculated at retrieval time; not certified pre-tipoff evidence'}
                write(ROOT / f'data/calculator/daily/{day}.json', payload)
                days.append({'date': str(day), 'games': len(matchups), 'calculated': payload['calculatedGames'], 'firstHalf': payload['firstHalfGames']})
            except Exception as exc:
                failures.append({'date': str(day), 'error': str(exc)})
        write(health, {'status': 'SOURCE_ERROR' if failures else 'READY',
                       'checkedAt': datetime.now(timezone.utc).isoformat(),
                       'ratingsFetchedAt': fetched, 'ratedTeams': len(ratings), 'days': days, 'failures': failures})
        print(json.dumps({'days': days, 'failures': failures}))
        if failures: raise SystemExit(1)
    except SystemExit: raise
    except Exception as exc:
        write(health, {'status': 'SOURCE_ERROR', 'checkedAt': now.isoformat(), 'message': str(exc)})
        raise SystemExit('Automatic source refresh failed; previous successful results preserved: ' + str(exc))

if __name__ == '__main__': main()
