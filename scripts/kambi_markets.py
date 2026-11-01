"""Independent Kambi market snapshots. Never imports or changes projection code."""
import json
import re
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://eu.offering-api.kambicdn.com/offering/v2018/pivusmsrl-bil'
PARAMS = '?lang=en_US&market=US-MS&client_id=200&channel_id=7'
DISCOVERY = BASE + '/listView/basketball/ncaab/all/all/matches.json' + PARAMS + '&useCombined=true&useCombinedLive=true'
# Observed criterion IDs and labels verified against event betOffers, Nov 1 2026.
CRITERIA = {
 '1001159512': ('full', 'spread', 'Point Spread'),
 '1001159732': ('full', 'moneyline', 'Moneyline'),
 '1001159509': ('full', 'total', 'Total Points - Including Overtime'),
 '1001159940': ('half', 'spread', 'Spread - 1st Half'),
 '1001159815': ('half', 'moneyline', 'Moneyline - 1st Half'),
 '1001159947': ('half', 'total', 'Total Points - 1st Half'),
}

def norm(x):
 x = unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode().lower()
 return re.sub(r'[^a-z0-9]', '', x)

def instant(s):
 return datetime.fromisoformat(s.replace('Z', '+00:00'))

def identities(game, directory):
 # Exact institutional or full names only; never substring/mascot matching.
 comp = game['competitions'][0]
 return {str(c['team']['id']): {norm(t[k]) for t in (c['team'], directory.get(str(c['team']['id']), {}))
         for k in ('location', 'displayName', 'shortDisplayName') if t.get(k)} for c in comp['competitors']}

def match_event(event, games, directory):
 if event.get('sport') != 'BASKETBALL' or event.get('group') != 'NCAAB': return None
 names = [norm(event.get(k, '')) for k in ('awayName', 'homeName')]
 if not all(names) or names[0] == names[1]: return None
 found = []
 for g in games:
  if abs((instant(g['date']) - instant(event['start'])).total_seconds()) > 900: continue
  ids = identities(g, directory)
  mapped = [[tid for tid, aliases in ids.items() if n in aliases] for n in names]
  if all(len(m) == 1 for m in mapped) and mapped[0] != mapped[1]:
   found.append((g, dict(zip(names, (m[0] for m in mapped)))))
 return found[0] if len(found) == 1 else None

def parse_offers(offers, event, team_map):
 candidates = {}
 for o in offers:
  spec = CRITERIA.get(str(o.get('criterion', {}).get('id')))
  if not spec or o.get('criterion', {}).get('label') != spec[2]: continue
  if str(o.get('eventId')) != str(event['id']): continue
  if 'OFFERED_PREMATCH' not in o.get('tags', []): continue
  period, kind, label = spec
  rows = o.get('outcomes', [])
  if len(rows) != 2 or any(x.get('status') != 'OPEN' for x in rows): continue
  parsed = []
  try:
   for x in rows:
    if str(x.get('betOfferId')) != str(o['id']): raise ValueError('ID mismatch')
    price = int(x['oddsAmerican'])
    if abs(price) < 100: raise ValueError('Invalid American price')
    row = {'id': str(x['id']), 'price': price, 'changedAt': x.get('changedDate')}
    if kind == 'total':
     side = x.get('label', '').lower()
     if side not in ('over', 'under'): raise ValueError('Unknown total side')
     row['side'] = side
    else:
     tid = team_map.get(norm(x.get('participant', '')))
     if not tid: raise ValueError('Unknown participant')
     row['teamId'] = tid
    if kind != 'moneyline':
     raw = x['line']
     if isinstance(raw, bool) or not isinstance(raw, int): raise ValueError('Invalid line')
     row['line'] = raw / 1000
     if abs(row['line']) > 400: raise ValueError('Line outside bounds')
    parsed.append(row)
   if kind == 'total':
    if {x['side'] for x in parsed} != {'over', 'under'} or parsed[0]['line'] != parsed[1]['line'] or parsed[0]['line'] <= 0: continue
   else:
    if len({x['teamId'] for x in parsed}) != 2: continue
    if kind == 'spread' and abs(sum(x['line'] for x in parsed)) > .001: continue
  except (KeyError, ValueError, TypeError): continue
  record = {'id': str(o['id']), 'criterionId': str(o['criterion']['id']), 'label': label,
            'period': period, 'kind': kind, 'outcomes': parsed,
            'main': bool(set(o.get('tags', [])) & {'MAIN', 'MAIN_LINE'})}
  candidates.setdefault((period, kind), []).append(record)
 result = {'full': {}, 'half': {}}
 for (period, kind), choices in candidates.items():
  main = [o for o in choices if o['main']]
  # One source-marked main line, or the single offered market. Never choose an alternate by price.
  selected = main if main else choices
  if len(selected) == 1: result[period][kind] = selected[0]
 return result

def fetch(url):
 req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'Docs-NCAAB-Research/1.0'})
 with urllib.request.urlopen(req, timeout=30) as r:
  raw = r.read(10_000_001)
  if len(raw) > 10_000_000: raise ValueError('Source too large')
  return json.loads(raw)

def write(path, value):
 path.parent.mkdir(parents=True, exist_ok=True)
 tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n');tmp.replace(path)

def main():
 stamp = datetime.now(timezone.utc).isoformat()
 today = instant(stamp).astimezone(ZoneInfo('America/Chicago')).date()
 folder = ROOT / 'data/kambi'
 try:
  directory_data = fetch('https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams?groups=50&limit=1000')
  directory = {str(e['team']['id']): e['team'] for s in directory_data['sports'] for l in s['leagues'] for e in l['teams']}
  slates = {}
  for i in range(5):
   day = str(today + timedelta(days=i))
   # Schedule IDs and identity fields, independent of rating availability.
   slates[day] = fetch('https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?groups=50&limit=1000&dates='+day.replace('-', ''))['events']
  data = fetch(DISCOVERY)
  if not isinstance(data.get('events'), list): raise ValueError('Kambi events missing')
  all_games = [g for games in slates.values() for g in games]
  by_game = {}; errors = []; unmatched = []
  for wrapper in data['events']:
   event = wrapper.get('event', {})
   match = match_event(event, all_games, directory)
   if not match: unmatched.append(str(event.get('id'))); continue
   g, mapping = match
   sides = {c['homeAway']: str(c['team']['id']) for c in g['competitions'][0]['competitors']}
   record = {'eventId': str(event['id']), 'name': event['name'], 'start': event['start'],
             'awayId': sides['away'], 'homeId': sides['home'],
             'state': event.get('state'), 'fetchedAt': stamp, 'periods': {'half': {}, 'full': {}}}
   if str(g['id']) in by_game:
    by_game[str(g['id'])] = {'error': 'Ambiguous Kambi events for this matchup', 'fetchedAt': stamp}; continue
   if event.get('state') == 'NOT_STARTED':
    url = BASE + '/betoffer/event/' + str(event['id']) + '.json' + PARAMS + '&includeParticipants=true'
    record['sourceUrl'] = url
    try:
     detail = fetch(url)
     if not isinstance(detail.get('betOffers'), list): raise ValueError('Event betOffers missing')
     record['fetchedAt'] = datetime.now(timezone.utc).isoformat()
     record['periods'] = parse_offers(detail['betOffers'], event, mapping)
    except Exception as exc:
     record['error'] = 'Event market retrieval failed: ' + str(exc);errors.append(record['eventId'])
   else: record['error'] = 'Pregame market unavailable: event is ' + str(event.get('state'))
   by_game[str(g['id'])] = record
  for day, games in slates.items():
   write(folder / (day+'.json'), {'date': day, 'fetchedAt': stamp, 'source': 'Kambi',
    'offering': 'pivusmsrl-bil', 'market': 'US-MS', 'discoveryUrl': DISCOVERY,
    'games': {str(g['id']): by_game.get(str(g['id']), {'error': 'NO EXACT KAMBI EVENT MATCH', 'fetchedAt': stamp}) for g in games}})
  write(folder/'health.json', {'status': 'PARTIAL' if errors else 'READY', 'checkedAt': datetime.now(timezone.utc).isoformat(),
    'eventsDiscovered': len(data['events']), 'matchedGames': len(by_game), 'eventErrors': errors, 'unmatchedEventIds': unmatched})
  print(json.dumps({'events': len(data['events']), 'matched':len(by_game), 'errors': errors}))
 except Exception as exc:
  write(folder/'health.json', {'status':'SOURCE_ERROR', 'checkedAt': datetime.now(timezone.utc).isoformat(), 'message': str(exc)})
  raise SystemExit('Kambi refresh failed; prior snapshots retained: '+str(exc))

if __name__ == '__main__': main()
