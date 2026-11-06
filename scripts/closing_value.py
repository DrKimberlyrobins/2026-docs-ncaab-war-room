"""Evaluate a manually supplied, provenance-labeled pair of sportsbook quotes."""
import argparse
from datetime import datetime
import json
import math


IDENTITY = ('event', 'sportsbook', 'region', 'period', 'rules', 'kind',
            'market', 'selection', 'direction')


def instant(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('An explicit timezone is required')
    return parsed


def implied(price):
    if type(price) is not int or abs(price) < 100:
        raise ValueError('An American price is required')
    return 100 / (100 + price) if price > 0 else -price / (100 - price)


def compare(entry, close, start, *, max_age_seconds):
    """Return signed points and, at the identical threshold, price-aware CLV."""
    if any(not entry.get(key) or entry[key] != close.get(key) for key in IDENTITY):
        raise ValueError('Market identity, selection, or settlement rules differ')
    if not entry.get('source') or not close.get('source') or close.get('verifiedClose') is not True:
        raise ValueError('A sourced entry and independently verified close are required')
    entered, closed, started = map(instant, (entry['observedAt'], close['observedAt'], start))
    if not entered < closed < started:
        raise ValueError('Both quotes must be chronological and pregame')
    if not math.isfinite(max_age_seconds) or not 0 < (started - closed).total_seconds() <= max_age_seconds:
        raise ValueError('Closing observation is stale')

    kind, direction = entry['kind'], entry['direction']
    first, last = entry.get('line'), close.get('line')
    if kind == 'moneyline' and direction == 'side':
        if first is not None or last is not None:
            raise ValueError('Moneyline quotes cannot carry a threshold')
        points = None
    else:
        if any(type(line) not in (int, float) or not math.isfinite(line) for line in (first, last)):
            raise ValueError('A finite line is required')
        if kind == 'spread' and direction == 'side':
            points = first - last  # Spread as offered for the selected team.
        elif kind in ('total', 'prop') and direction in ('over', 'under'):
            points = (last - first) if direction == 'over' else (first - last)
        else:
            raise ValueError('Unsupported market or direction')
        if kind == 'prop' and first != last:
            raise ValueError('Player prop thresholds differ')

    entry_implied, close_implied = implied(entry['price']), implied(close['price'])
    opposite = close.get('oppositePrice')
    close_fair = close_implied / (close_implied + implied(opposite)) if opposite is not None else None
    return {
        'lineCLV': points,
        'priceCLVPercentagePoints': 100 * (close_implied - entry_implied) if first == last else None,
        'fairPriceCLVPercent': (
            100 * (close_fair / entry_implied - 1) if first == last and close_fair is not None else None
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('quote_pair', type=argparse.FileType('r'))
    parser.add_argument('--max-age-seconds', type=float, required=True)
    args = parser.parse_args()
    data = json.load(args.quote_pair)
    print(json.dumps(compare(data['entry'], data['close'], data['start'],
                             max_age_seconds=args.max_age_seconds), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
