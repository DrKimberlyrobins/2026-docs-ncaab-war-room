import unittest

from closing_value import compare


class ClosingValueTests(unittest.TestCase):
    def quote(self, kind='total', direction='over', line=56.5):
        return dict(event='game', sportsbook='book', region='US-MS', period='full',
                    rules='overtime-included', kind=kind, market='main', selection='pick',
                    direction=direction, line=line, price=-110, source='source record',
                    observedAt='2026-11-06T20:00:00Z')

    def check(self, entry, **overrides):
        close = {**entry, 'observedAt': '2026-11-06T20:59:00Z', 'verifiedClose': True, **overrides}
        return compare(entry, close, '2026-11-06T21:00:00Z', max_age_seconds=120)

    def test_total_and_spread_signs(self):
        self.assertEqual(self.check(self.quote(), line=59.5)['lineCLV'], 3)
        self.assertEqual(self.check(self.quote(direction='under'), line=53.5)['lineCLV'], 3)
        self.assertEqual(self.check(self.quote('spread', 'side', 5.5), line=4.5)['lineCLV'], 1)
        self.assertEqual(self.check(self.quote('spread', 'side', -4.5), line=-5.5)['lineCLV'], 1)
        self.assertIsNone(self.check(self.quote(), line=59.5)['priceCLVPercentagePoints'])

    def test_price_only_and_moneyline(self):
        result = self.check({**self.quote(), 'price': 100}, price=-120, oppositePrice=100)
        self.assertGreater(result['priceCLVPercentagePoints'], 0)
        self.assertGreater(result['fairPriceCLVPercent'], 0)
        result = self.check(self.quote('moneyline', 'side', None), price=-125)
        self.assertIsNone(result['lineCLV'])
        self.assertGreater(result['priceCLVPercentagePoints'], 0)

    def test_prop_requires_same_threshold(self):
        quote = self.quote('prop', 'under', 18.5)
        self.assertEqual(self.check(quote, price=-105)['lineCLV'], 0)
        with self.assertRaises(ValueError):
            self.check(quote, line=17.5)

    def test_missing_mismatched_stale_and_post_start_closes(self):
        for change in (dict(sportsbook='another'), dict(rules='regulation'), dict(price=None),
                       dict(verifiedClose=False), dict(source=''),
                       dict(observedAt='2026-11-06T20:50:00Z'),
                       dict(observedAt='2026-11-06T21:00:00Z')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check(self.quote(), **change)
