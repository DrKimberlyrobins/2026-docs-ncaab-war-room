"""Collect exact-match, pregame Kalshi asks for research and audit."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import json
from math import floor
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from first_half import moment
from kambi_markets import norm
from rank_matchup_markets import MIN_OBSERVATIONS

BASE = 'https://external-api.kalshi.com/trade-api/v2'
FEE_SOURCE = 'https://kalshi.com/docs/kalshi-fee-schedule.pdf'
SERIES = {
    'KXNCAAMBSPREAD': ('full', 'spread', 'Spread'),
    'KXNCAAMBTOTAL': ('full', 'total', 'Point Total'),
    'KXNCAAMB1HSPREAD': ('half', 'spread', '1st Half Spread'),
    'KXNCAAMB1HTOTAL': ('half', 'total', '1st Half Total'),
    'KXNCAAMBTEAMTOTAL': ('full', 'teamTotal', 'Team Total'),
    'KXNCAAMB1HTEAMTOTAL': ('half', 'teamTotal', '1st Half Team Total'),
}


def fetch(path, **params):
    url = BASE + path + ('?' + urlencode(params) if params else '')
    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'Docs-NCAAB-Research/1.0'})
    with urlopen(request, timeout=12) as response:
        raw = response.read(12_000_001)
        if len(raw) > 12_000_000:
            raise ValueError('Kalshi response exceeds size limit')
    return json.loads(raw)


def collect_series(series):
    cursor = ''
    for _ in range(8):
        payload = fetch('/events', status='open', with_nested_markets='true',
                        series_ticker=series, limit=50, cursor=cursor)
        yield from payload['events']
        cursor = payload.get('cursor')
        if not cursor:
            return
    raise ValueError('Kalshi event cursor limit reached')


def game_aliases(game):
    rated = game.get('matchedTeams') or {}
    return {
        side: {norm(name) for name in (rated.get(side), game.get(side + 'Name')) if name}
        for side in ('away', 'home')
    }


def match_event(event, snapshots, spec, observed):
    title = event.get('title', '')
    match = re.fullmatch(r'(.+) vs (.+): ' + re.escape(spec[2]), title)
    ticker = re.fullmatch(re.escape(event.get('series_ticker', '')) + r'-(\d{2}[A-Z]{3}\d{2})[A-Z0-9]+',
                          event.get('event_ticker', ''))
    if not (match and ticker) or event.get('product_metadata', {}).get('competition') != 'College Basketball (M)':
        return None
    game_date = datetime.strptime(ticker[1], '%y%b%d').date().isoformat()
    names = tuple(map(norm, match.groups()))
    choices = []
    for snapshot in snapshots:
        if snapshot['gameDate'] != game_date or not moment(snapshot['savedAt']) <= observed < moment(snapshot['scheduledTipoff']):
            continue
        aliases = game_aliases(snapshot['matchup'])
        for first, second in (('away', 'home'), ('home', 'away')):
            if names[0] in aliases[first] and names[1] in aliases[second]:
                choices.append((snapshot, dict(zip(names, (first, second)))))
    return choices[0] if len(choices) == 1 else None


def contract(market, event, snapshot, team_map, spec, observed):
    ticker = market.get('ticker', '')
    if (market.get('event_ticker') != event['event_ticker']
            or not ticker.startswith(event['event_ticker'] + '-')
            or market.get('status') != 'active' or market.get('strike_type') != 'greater'
            or not moment(market['open_time']) <= observed < moment(market['close_time'])):
        return []
    if market.get('fee_type_override') or market.get('fee_multiplier_override') not in (None, 1):
        return []
    period, kind, _ = spec
    rules = market.get('rules_primary', '')
    if "men's college basketball game" not in rules.lower() or ('1st half' in rules.lower()) != (period == 'half'):
        return []
    pattern = {'total': r'Over ([\d.]+) points',
               'spread': r'(.+) wins by over ([\d.]+) points',
               'teamTotal': r'(.+) over ([\d.]+) points'}[kind]
    label = re.fullmatch(pattern, market.get('yes_sub_title', ''), flags=re.I)
    if not label:
        return []
    line = float(label.groups()[-1])
    if line <= 0 or line > 450 or line % 1 != .5 or line != market.get('floor_strike'):
        return []
    side = None if kind == 'total' else team_map.get(norm(label[1]))
    if kind != 'total' and side is None:
        return []
    result = []
    for answer in ('yes', 'no'):
        raw = market.get(answer + '_ask_dollars')
        if not raw:
            continue
        price = Decimal(raw)
        size = market.get(answer + '_ask_size_fp')
        # Kalshi's opposite bid implied by an ask must agree at the exact complement.
        opposite = 'no' if answer == 'yes' else 'yes'
        if size is None and market.get(opposite + '_bid_dollars'):
            if Decimal(market[opposite + '_bid_dollars']) + price == 1:
                size = market.get(opposite + '_bid_size_fp')
        if not 0 < price < 1 or size is None or Decimal(size) <= 0:
            continue
        # Round total debit up to a centicent per the published one-contract schedule.
        debit = (price + Decimal('.07') * price * (1-price)).quantize(
            Decimal('.0001'), rounding=ROUND_CEILING)
        result.append({
            'ticker': ticker, 'eventTicker': event['event_ticker'], 'period': period,
            'kind': kind, 'answer': answer, 'line': line, 'teamSide': side,
            'label': market['yes_sub_title'], 'ask': float(price), 'askSize': float(size),
            'fee': float(debit - price), 'breakEven': float(debit),
            'quoteFetchedAt': observed.isoformat(), 'rules': rules,
        })
    return result


def measure(row, away, home):
    if row['kind'] == 'total':
        return away + home
    if row['kind'] == 'spread':
        return home - away if row['teamSide'] == 'home' else away - home
    return home if row['teamSide'] == 'home' else away


def estimate(row, snapshot, errors):
    predicted = snapshot['matchup'].get('firstHalf' if row['period'] == 'half' else 'model')
    if not predicted:
        return None

    a, h = predicted['away'], predicted['home']
    sign = 1 if row['answer'] == 'yes' else -1
    probability = None
    if len(errors) >= MIN_OBSERVATIONS:
        yes = sum(measure(row, max(0, floor(a + e['away'] + .5)),
                          max(0, floor(h + e['home'] + .5))) > row['line'] for e in errors)
        probability = (yes if sign == 1 else len(errors) - yes) / len(errors)
    cost = row['breakEven']
    return {**row, 'prediction': measure(row, a, h),
            'pointDifference': sign * (measure(row, a, h) - row['line']),
            'probability': probability, 'sampleSize': len(errors),
            'expectedValue': (probability - cost) / cost if probability is not None else None,
            'projectedScore': {'away': a, 'home': h}}


def collect(snapshots, evidence, residuals):
    dated = defaultdict(dict)
    status = {}

    def get(series):
        try:
            rows = list(collect_series(series))
            observed = datetime.now(timezone.utc)
            if rows:
                fee = fetch('/series/' + series)['series']
                if fee.get('fee_multiplier') != 1 or fee.get('fee_type') not in ('quadratic','quadratic_with_maker_fees'):
                    raise ValueError('Unsupported series fee schedule')
            return series, rows, observed, None
        except (OSError, ValueError, KeyError) as exc:
            return series, [], datetime.now(timezone.utc), str(exc)

    with ThreadPoolExecutor(max_workers=len(SERIES)) as pool:
        for series, events, observed, error in pool.map(get, SERIES):
            status[series] = {'events': len(events), 'error': error, 'checkedAt': observed.isoformat()}
            spec = SERIES[series]
            for event in events:
                if event.get('series_ticker') != series:
                    continue
                try:
                    match = match_event(event, snapshots, spec, observed)
                except (TypeError, ValueError):
                    continue
                if not match:
                    continue
                snapshot, team_map = match
                cutoff = {**snapshot, 'savedAt': observed.isoformat()}
                cases = residuals(evidence, cutoff)[spec[0]]
                quotes = []
                for market in event.get('markets') or []:
                    try:
                        for row in contract(market, event, snapshot, team_map, spec, observed):
                            estimate_row = estimate(row, snapshot, cases)
                            if estimate_row is not None:
                                quotes.append(estimate_row)
                    except (InvalidOperation, TypeError, ValueError, KeyError):
                        continue
                if quotes:
                    game = dated[snapshot['gameDate']].setdefault(snapshot['id'], {
                        'tipoff': snapshot['scheduledTipoff'], 'markets': []})
                    game['markets'].extend(quotes)
    for games in dated.values():
        for game in games.values():
            game['markets'].sort(key=lambda row: -(row['expectedValue'] if row['expectedValue'] is not None else -2))
    return {'source': BASE, 'feeSource': FEE_SOURCE, 'status': status, 'dates': dict(dated)}
