import unittest

from grade_frozen_scores import residuals
from rank_matchup_markets import markets, settle


class MarketResearchTests(unittest.TestCase):
    def setUp(self):
        self.game = {'awayId': 'a', 'homeId': 'h',
                     'model': {'away': 70, 'home': 80}}
        self.snap = {'savedAt': '2026-11-14T15:00:00Z',
                     'scheduledTipoff': '2026-11-14T18:00:00Z',
                     'gameDate': '2026-11-14', 'matchup': self.game}
        self.quote = {'state': 'NOT_STARTED', 'fetchedAt': self.snap['savedAt'],
                      'start': self.snap['scheduledTipoff'],
                      'periods': {'full': {'total': {'outcomes': [
                          {'side': 'over', 'line': 150, 'price': -110}
                      ]}}}}

    def test_integer_line_pushes_and_ev_at_offered_price(self):
        errors = [{'away': 1, 'home': 0}] * 70 + [{'away': -1, 'home': 0}] * 40
        errors += [{'away': 0, 'home': 0}] * 10
        row, = markets(self.snap, self.quote, {'half': [], 'full': errors})
        self.assertAlmostEqual(row['probability'], 70 / 120)
        self.assertAlmostEqual(row['pushProbability'], 10 / 120)
        self.assertAlmostEqual(row['expectedValue'], (70 * 100 / 110 - 40) / 120)
        grade, = settle([row], self.snap, {'full': {'away': 71, 'home': 79}})
        self.assertEqual(grade['result'], 'PUSH')

    def test_no_live_stale_or_undersampled_estimates(self):
        row, = markets(self.snap, self.quote, {'full': []})
        self.assertIsNone(row['probability'])
        self.assertFalse(row['qualified'])
        self.quote['fetchedAt'] = '2026-11-14T13:00:00Z'
        self.assertEqual(markets(self.snap, self.quote, {}), [])

    def test_replay_excludes_same_date_and_future_result_retrieval(self):
        report = {'dates': {
            '2026-11-13': {'forecastErrors': {
                'valid': {'resultFetchedAt': '2026-11-14T14:00:00Z', 'full': {'away': 1, 'home': 0}},
                'late': {'resultFetchedAt': '2026-11-14T15:01:00Z', 'full': {'away': 2, 'home': 0}},
            }},
            '2026-11-14': {'forecastErrors': {
                'same': {'resultFetchedAt': '2026-11-14T13:00:00Z', 'full': {'away': 3, 'home': 0}},
            }},
        }}
        self.assertEqual(residuals(report, self.snap)['full'], [{'away': 1, 'home': 0}])
