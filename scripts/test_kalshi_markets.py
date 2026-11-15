from datetime import datetime, timezone
import unittest

from kalshi_markets import SERIES, contract, estimate, match_event


class KalshiTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 15, 15, tzinfo=timezone.utc)
        self.snapshot = {'gameDate': '2026-11-15', 'scheduledTipoff': '2026-11-15T18:00:00Z',
                         'savedAt': '2026-11-15T13:00:00Z', 'matchup': {
                             'awayName': 'Louisville Cardinals', 'homeName': 'Memphis Tigers',
                             'matchedTeams': {'away': 'Louisville', 'home': 'Memphis'},
                             'model': {'away': 72, 'home': 69}}}
        self.series = 'KXNCAAMBTEAMTOTAL'
        self.event = {'title': 'Memphis vs Louisville: Team Total', 'series_ticker': self.series,
                      'event_ticker': self.series + '-26NOV15MEMLOU',
                      'product_metadata': {'competition': 'College Basketball (M)'}}
        ticker = self.event['event_ticker']
        self.market = {'event_ticker': ticker, 'ticker': ticker + '-LOU72',
                       'open_time': '2026-11-15T11:00:00Z', 'close_time': '2026-11-16T11:00:00Z',
                       'status': 'active', 'strike_type': 'greater', 'floor_strike': 71.5,
                       'rules_primary': "If Louisville scores more than 71.5 points in the Memphis vs Louisville men's college basketball game originally scheduled for Nov 15, 2026, then the market resolves to Yes.",
                       'yes_sub_title': 'Louisville over 71.5 points', 'yes_ask_dollars': '.60',
                       'yes_ask_size_fp': '12', 'no_ask_dollars': '.40', 'yes_bid_dollars': '.60',
                       'yes_bid_size_fp': '9'}

    def test_reverse_title_still_maps_to_the_correct_team(self):
        spec = SERIES[self.series]
        snapshot, names = match_event(self.event, [self.snapshot], spec, self.now)
        yes, no = contract(self.market, self.event, snapshot, names, spec, self.now)
        self.assertEqual(yes['teamSide'], 'away')
        self.assertEqual(yes['breakEven'], .6168)
        self.assertEqual(no['askSize'], 9)
        errors = [{'away': 3, 'home': 0}] * 70 + [{'away': -3, 'home': 0}] * 30
        self.assertEqual(estimate(yes, snapshot, errors)['probability'], .7)
        self.assertAlmostEqual(estimate(no, snapshot, errors)['expectedValue'], (.3-.4168)/.4168)

    def test_ambiguous_matches_and_post_tipoff_quotes_fail(self):
        spec = SERIES[self.series]
        self.assertIsNone(match_event(self.event, [self.snapshot, self.snapshot], spec, self.now))
        late = self.now.replace(hour=19)
        self.assertIsNone(match_event(self.event, [self.snapshot], spec, late))
        self.market['floor_strike'] = 71
        self.assertEqual(contract(self.market, self.event, self.snapshot, {'louisville':'away'}, spec, self.now), [])
