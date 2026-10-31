import unittest
from possession_simulator import Team, simulate

class TestSimulator(unittest.TestCase):
    def test_reproducible(self):
        a = Team('A', 110, 100, 70)
        b = Team('B', 115, 95, 72)
        x = simulate(a, b, n=100, seed=42)
        y = simulate(a, b, n=100, seed=42)
        self.assertEqual(x['mean_score'], y['mean_score'])
        self.assertAlmostEqual(x['mean_total'], sum(x['mean_score'].values()))
        self.assertAlmostEqual(x['mean_home_margin'], x['mean_score']['home'] - x['mean_score']['away'])

if __name__ == '__main__':
    unittest.main()
