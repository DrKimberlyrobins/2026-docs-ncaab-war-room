import unittest
from kenpom_calculator import build, calculate, rows

CONFIG = dict(season=2027, nationalEfficiency=106, nationalTempo=71.5, homeAdvantagePoints=0)
A = dict(offense=110.6, defense=99.8, tempo=69.8)
B = dict(offense=119, defense=98.3, tempo=70.4)

class CalculatorTests(unittest.TestCase):
    def test_screenshot_matchup(self):
        m = calculate(A, B, CONFIG, 'Neutral')
        self.assertAlmostEqual(m['possessions'], 68.7)
        self.assertAlmostEqual(m['away'], 70.6923)
        self.assertAlmostEqual(m['home'], 77.4936)
        self.assertAlmostEqual(m['total'], 148.1859)
        self.assertAlmostEqual(m['homeMargin'], 6.8013)

    def test_neutral_ignores_home_advantage(self):
        cfg = dict(CONFIG, homeAdvantagePoints=3)
        self.assertEqual(calculate(A, B, cfg, 'Neutral'), calculate(A, B, CONFIG, 'Neutral'))
        neutral, home = calculate(A, B, cfg, 'Neutral'), calculate(A, B, cfg, 'Home')
        self.assertAlmostEqual(neutral['total'], home['total'])
        self.assertAlmostEqual(home['homeMargin'] - neutral['homeMargin'], 3)

    def fixture(self):
        ratings = [dict(TeamName='Team '+str(i), Season=2027, AdjOE=110, AdjDE=100, AdjTempo=70) for i in range(300)]
        games = [dict(GameID=1, DateOfGame='2026-11-01', Season=2027,
                      Visitor='Team 0', Home='Team 1', Location='Neutral')]
        return ratings, games

    def test_missing_team_is_retained(self):
        r, g = self.fixture()
        g[0]['Visitor'] = 'Missing'
        p = build(r, g, CONFIG, '2026-11-01')
        self.assertEqual(len(p['matchups']), 1)
        self.assertIsNone(p['matchups'][0]['model'])
        self.assertEqual(p['calculatedGames'], 0)

    def test_wrong_season_and_date_rejected(self):
        r, g = self.fixture()
        r[0]['Season'] = 2026
        with self.assertRaisesRegex(ValueError, 'season'):
            build(r, g, CONFIG, '2026-11-01')
        r, g = self.fixture()
        with self.assertRaisesRegex(ValueError, 'date'):
            build(r, g, CONFIG, '2026-11-02')

    def test_duplicates_and_nan_rejected(self):
        r, g = self.fixture()
        r[1]['TeamName'] = r[0]['TeamName']
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            build(r, g, CONFIG, '2026-11-01')
        r, g = self.fixture()
        r[0]['AdjOE'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            build(r, g, CONFIG, '2026-11-01')

    def test_response_envelope(self):
        self.assertEqual(rows([]), [])
        self.assertEqual(rows({'data': []}), [])
        with self.assertRaises(ValueError):
            rows({'error': 'Unauthorized'})

if __name__ == '__main__':
    unittest.main()
