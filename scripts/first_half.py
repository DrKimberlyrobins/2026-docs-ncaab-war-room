"""First-half timing profiles from actual completed ESPN period scores.

Anchor to the current full-game matchup projection, then apply each team's
observed first-half scoring share and its opponent's first-half allowed share.
Never substitute a fixed 50% share for missing half data. Overtime is excluded
from profile denominators. Prior-season fallback is explicit for each team.
"""
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_GAMES = 3
MAX_GAMES = 10


def moment(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result


def number(value):
    if isinstance(value, dict):
        value = value.get('value', value.get('displayValue'))
    try:
        n = float(value)
        return n if math.isfinite(n) and n >= 0 else None
    except (TypeError, ValueError):
        return None


def read(path):
    try:
        return json.loads((ROOT / path).read_text())
    except (OSError, ValueError):
        return None


def pair(comp, team_id):
    me = next((t for t in comp.get('competitors', []) if str(t.get('id')) == str(team_id)), None)
    opponent = next((t for t in comp.get('competitors', []) if str(t.get('id')) != str(team_id)), None)
    if not me or not opponent:
        return None
    values = []
    for t in (me, opponent):
        periods = t.get('linescores') or []
        if len(periods) < 2:
            return None
        first, second = number(periods[0]), number(periods[1])
        if first is None or second is None or first + second <= 0:
            return None
        final = number(t.get('score'))
        if final is not None and first + second > final:
            return None
        values.append((first, second))
    return values


def season_profile(team_id, season, cutoff):
    schedule = read(Path(f'data/schedules/{season}/{team_id}.json'))
    if not schedule:
        return None
    limit = moment(cutoff)
    candidates = []
    for event in schedule.get('data', {}).get('events', []):
        try:
            date = moment(event['date'])
        except (ValueError, KeyError, TypeError):
            continue
        if not f'{season-1}-07-01' <= event['date'] < f'{season}-07-01' or date >= limit:
            continue
        comp = (event.get('competitions') or [{}])[0]
        if not comp.get('status', {}).get('type', {}).get('completed'):
            continue
        if event.get('seasonType', {}).get('type') == 1 or comp.get('type', {}).get('slug') == 'exhibition':
            continue
        candidates.append((event, comp))
    candidates.sort(key=lambda x: moment(x[0]['date']), reverse=True)
    samples, sources = [], {}
    for event, comp in candidates[:MAX_GAMES]:
        halves = pair(comp, team_id)
        evidence = schedule
        if halves is None:
            summary = read(Path(f"data/summaries/{event['id']}.json"))
            sc = ((summary or {}).get('data', {}).get('header', {}).get('competitions') or [{}])[0]
            if sc.get('status', {}).get('type', {}).get('completed'):
                halves = pair(sc, team_id)
                evidence = summary
        if halves is None:
            continue
        (sf, ss), (af, ass) = halves
        samples.append({'id': str(event['id']), 'date': event['date'],
                        'firstScored': sf, 'secondScored': ss,
                        'firstAllowed': af, 'secondAllowed': ass})
        if evidence.get('url'):
            sources[evidence['url']] = {'url': evidence['url'], 'fetchedAt': evidence.get('fetchedAt')}
    if len(samples) < MIN_GAMES:
        return None
    n = len(samples)
    scored = sum(s['firstScored'] + s['secondScored'] for s in samples)
    allowed = sum(s['firstAllowed'] + s['secondAllowed'] for s in samples)
    return {'season': season, 'games': n,
            'scoringShare': sum(s['firstScored'] for s in samples) / scored,
            'allowingShare': sum(s['firstAllowed'] for s in samples) / allowed,
            'firstScoredAverage': sum(s['firstScored'] for s in samples) / n,
            'firstAllowedAverage': sum(s['firstAllowed'] for s in samples) / n,
            'samples': samples, 'sources': list(sources.values())}


def profile(team_id, season, cutoff):
    for candidate in (season, season - 1):
        result = season_profile(str(team_id), candidate, cutoff)
        if result:
            result['priorSeason'] = candidate != season
            return result
    return None


def project(full, away_profile, home_profile):
    if not full or not away_profile or not home_profile:
        return None
    away_share = (away_profile['scoringShare'] + home_profile['allowingShare']) / 2
    home_share = (home_profile['scoringShare'] + away_profile['allowingShare']) / 2
    away, home = full['away'] * away_share, full['home'] * home_share
    return {'away': away, 'home': home, 'total': away + home, 'homeMargin': home - away,
            'awayScoringShare': away_share, 'homeScoringShare': home_share,
            'modelVersion': 'first-half-timing-v1',
            'method': 'Current full-game projection × average of own observed 1H scoring share and opponent observed 1H allowing share',
            'awayProfile': away_profile, 'homeProfile': home_profile}


def attach(matchup, event, season, prepared_at):
    comp = (event.get('competitions') or [{}])[0]
    away = next((t for t in comp.get('competitors', []) if t.get('homeAway') == 'away'), None)
    home = next((t for t in comp.get('competitors', []) if t.get('homeAway') == 'home'), None)
    matchup['firstHalf'] = None
    if not matchup.get('model'):
        matchup['firstHalfStatus'] = 'Full-game matchup ratings unavailable.'
        return
    if not away or not home:
        matchup['firstHalfStatus'] = 'Schedule team identity missing.'
        return
    cutoff = min(moment(prepared_at), moment(event['date'])).isoformat()
    ap = profile(away['id'], season, cutoff)
    hp = profile(home['id'], season, cutoff)
    matchup['firstHalf'] = project(matchup['model'], ap, hp)
    matchup['firstHalfStatus'] = ('Ready from actual half scores; prior-season timing profiles are labeled.'
        if matchup['firstHalf'] else 'Requires at least three completed games with both regulation halves for each team; no fixed 50% substitute used.')
