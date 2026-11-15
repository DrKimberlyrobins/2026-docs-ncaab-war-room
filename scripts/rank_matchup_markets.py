"""Replay jointly observed basketball score errors against verified Kambi lines."""
from collections import defaultdict
import json
from math import floor, sqrt

from closing_value import implied
from first_half import moment

MIN_OBSERVATIONS = 100
VERSION = 'empirical-score-residuals-v1'


def wilson_lower(wins, decisions):
    rate = wins / decisions
    z = 1.96
    factor = z * z / decisions
    return (rate + factor / 2 - z * sqrt((rate * (1 - rate) + factor / 4) / decisions)) / (1 + factor)


def difference(kind, outcome, away, home, game):
    line = outcome['line']
    if kind == 'total' and outcome.get('side') in ('over', 'under'):
        return (away + home - line) * (1 if outcome['side'] == 'over' else -1)
    if kind == 'spread':
        if outcome.get('teamId') == game['homeId']:
            return home - away + line
        if outcome.get('teamId') == game['awayId']:
            return away - home + line
    raise ValueError('Unsupported market outcome')


def markets(snapshot, quote, errors):
    cutoff = moment(snapshot['savedAt'])
    if not quote or quote.get('error') or quote.get('state') != 'NOT_STARTED':
        return []
    observed = moment(quote['fetchedAt'])
    if not observed <= cutoff < min(moment(quote['start']), moment(snapshot['scheduledTipoff'])):
        return []
    if (cutoff - observed).total_seconds() > 3600:
        return []
    game = snapshot['matchup']
    rows = []
    for period, key in (('half', 'firstHalf'), ('full', 'model')):
        score = game.get(key)
        if not score:
            continue
        for kind in ('spread', 'total'):
            offer = quote.get('periods', {}).get(period, {}).get(kind, {})
            for outcome in offer.get('outcomes', []):
                try:
                    delta = difference(kind, outcome, score['away'], score['home'], game)
                    breakeven = implied(outcome['price'])
                except (KeyError, ValueError):
                    continue
                row = {
                    'period': period, 'kind': kind, 'line': outcome['line'], 'price': outcome['price'],
                    'outcomeId': outcome.get('id'), 'offerId': offer.get('id'),
                    'teamId': outcome.get('teamId'), 'side': outcome.get('side'),
                    'pointDifference': delta, 'breakEven': breakeven, 'probability': None,
                    'expectedValue': None, 'qualified': False, 'quoteFetchedAt': quote['fetchedAt'],
                    'score': {side: score[side] for side in ('away', 'home')},
                    'sampleSize': len(errors[period]),
                }
                wins = losses = 0
                for error in errors[period]:
                    away = max(0, floor(score['away'] + error['away'] + .5))
                    home = max(0, floor(score['home'] + error['home'] + .5))
                    scenario = difference(kind, outcome, away, home, game)
                    wins += scenario > 0
                    losses += scenario < 0
                n = len(errors[period])
                settled = wins + losses
                if settled >= MIN_OBSERVATIONS:
                    row.update(probability=wins / n, pushProbability=(n-settled) / n,
                               expectedValue=(wins / breakeven - settled) / n,
                               qualified=wilson_lower(wins, settled) > breakeven)
                rows.append(row)
    return sorted(rows, key=lambda x: (not x['qualified'], -(x['expectedValue'] or 0)))


def settle(rows, snapshot, actual):
    """Attach actual outcomes without changing the frozen prices or probabilities."""
    for row in rows:
        score = actual.get(row['period'])
        if score:
            delta = difference(row['kind'], row, score['away'], score['home'], snapshot['matchup'])
            yield {**row, 'result': 'WIN' if delta > 0 else 'LOSS' if delta < 0 else 'PUSH'}


def replay(records, report, histories):
    """One candidate per game at its first usable quote after the frozen forecast."""
    from grade_frozen_scores import pregame, residuals

    results = {}
    for record in records:
        snapshot = record['snapshot']
        actual = record.get('result')
        if not actual or not pregame(snapshot):
            continue
        date = snapshot['gameDate']
        observations = histories.get(date, {}).get(snapshot['id'], [])
        for quote in observations:
            observed = moment(quote['fetchedAt'])
            if not moment(snapshot['savedAt']) <= observed < moment(snapshot['scheduledTipoff']):
                continue
            cutoff = {**snapshot, 'savedAt': quote['fetchedAt']}
            rows = markets(cutoff, quote, residuals(report, cutoff))
            evaluated = list(settle(rows, snapshot, actual))
            if not evaluated:
                continue
            day = results.setdefault(date, {'quotedGames': 0, 'marketOutcomes': 0,
                                          'estimates': 0, 'squaredError': 0., 'netUnits': 0.,
                                          'WIN': 0, 'LOSS': 0, 'PUSH': 0})
            day['quotedGames'] += 1
            day['marketOutcomes'] += len(evaluated)
            for row in evaluated:
                if row['probability'] is not None:
                    day['estimates'] += 1
                    day['squaredError'] += (row['probability'] - (row['result'] == 'WIN')) ** 2
            best = next((row for row in evaluated if row['qualified']), None)
            if best:
                outcome = best['result']
                day[outcome] += 1
                if outcome == 'WIN':
                    day['netUnits'] += 1 / best['breakEven'] - 1
                elif outcome == 'LOSS':
                    day['netUnits'] -= 1
            break
    for day in results.values():
        square_error = day.pop('squaredError')
        day['brier'] = square_error / day['estimates'] if day['estimates'] else None
        day['netUnits'] = round(day['netUnits'], 3)
    return results


def load_history(path):
    dates = {}
    for folder in sorted(path.glob('*/')):
        games = defaultdict(list)
        for file in sorted(folder.glob('*Z.json')):
            payload = json.loads(file.read_text())
            for game_id, quote in payload['games'].items():
                games[game_id].append(quote)
        dates[folder.name] = games
    return dates
