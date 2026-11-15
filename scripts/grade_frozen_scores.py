"""Score the existing War Room from immutable forecasts and sourced actuals."""
from collections import defaultdict
from math import isclose

from first_half import moment

FIELDS = ('away', 'home', 'total', 'homeMargin')
PERIODS = {'half': 'firstHalf', 'full': 'model'}


def coherent(scores):
    return (scores and isclose(scores['total'], scores['away'] + scores['home'], abs_tol=.01)
            and isclose(scores['homeMargin'], scores['home'] - scores['away'], abs_tol=.01))


def pregame(snapshot):
    tipoff = moment(snapshot['scheduledTipoff'])
    prepared = moment(snapshot['preparedAt'])
    game = snapshot['matchup']
    if not (moment(snapshot['ratingsFetchedAt']) <= prepared <= moment(snapshot['savedAt']) < tipoff):
        return False
    if moment(game['date']) != tipoff or str(game['id']) != str(snapshot['id']):
        return False
    if not game.get('homeId') or not game.get('awayId') or game['homeId'] == game['awayId']:
        return False
    half = game.get('firstHalf') or {}
    for side in ('away', 'home'):
        profile = half.get(side + 'Profile') or {}
        if any(moment(sample['date']) >= prepared for sample in profile.get('samples', [])):
            return False
        if any(not source.get('fetchedAt') or moment(source['fetchedAt']) > prepared
               for source in profile.get('sources', [])):
            return False
    return True


def summarize(cases):
    return {
        'games': len(cases),
        'mae': {field: round(sum(abs(c[field]) for c in cases) / len(cases), 3)
                for field in FIELDS} if cases else {},
        'projectedWinnerCorrect': sum(c['winnerCorrect'] for c in cases),
        'winnerEligibleGames': sum(c['winnerEligible'] for c in cases),
    }


def grade(records):
    all_cases = defaultdict(list)
    dates = {}
    for record in records:
        snapshot = record['snapshot']
        day = dates.setdefault(snapshot['gameDate'], {
            'receipts': 0, 'finals': 0, 'excludedReceipts': 0,
            'cases': defaultdict(list), 'forecastErrors': {},
        })
        day['receipts'] += 1
        actual = record.get('result')
        if actual:
            day['finals'] += 1
        if not pregame(snapshot):
            day['excludedReceipts'] += 1
            continue
        if not actual or actual.get('status') != 'Final':
            continue
        if moment(actual['fetchedAt']) < moment(snapshot['scheduledTipoff']):
            continue
        for period, field in PERIODS.items():
            predicted = snapshot['matchup'].get(field)
            outcome = actual.get(period)
            if not coherent(predicted) or not coherent(outcome):
                continue
            error = {f: outcome[f] - predicted[f] for f in FIELDS}
            game_errors = day['forecastErrors'].setdefault(snapshot['id'], {'resultFetchedAt': actual['fetchedAt']})
            game_errors[period] = {
                f: round(v, 3) for f, v in error.items()
            }
            margin, realized = predicted['homeMargin'], outcome['homeMargin']
            error.update(winnerCorrect=margin * realized > 0, winnerEligible=bool(margin and realized))
            day['cases'][period].append(error)
            all_cases[period].append(error)
    for day in dates.values():
        day['scores'] = {period: summarize(day['cases'][period]) for period in PERIODS}
        del day['cases']
    return {'version': 1, 'summary': {period: summarize(all_cases[period]) for period in PERIODS},
            'dates': dates}


def residuals(report, cutoff):
    """Only use earlier Central dates with finals retrieved before this forecast."""
    errors = {'half': [], 'full': []}
    for day, row in report['dates'].items():
        if day >= cutoff['gameDate']:
            continue
        for game in row['forecastErrors'].values():
            if moment(game['resultFetchedAt']) > moment(cutoff['savedAt']):
                continue
            for period in PERIODS:
                if period in game:
                    errors[period].append(game[period])
    return errors
