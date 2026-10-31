import unittest
from empirical_simulator import simulate_scores

class EmpiricalSimulationTests(unittest.TestCase):
    def test_reproducible_and_10000_runs(self):
        a=[{"pf":70,"pa":65},{"pf":81,"pa":72},{"pf":62,"pa":59}]
        h=[{"pf":75,"pa":68},{"pf":68,"pa":60},{"pf":79,"pa":77}]
        x=simulate_scores(a,h,seed=42)
        y=simulate_scores(a,h,seed=42)
        self.assertEqual(x["runs"],10000)
        self.assertEqual(x["mean_score"],y["mean_score"])
        self.assertEqual(x["interval_80"],y["interval_80"])
        self.assertEqual(x["data_basis"]["away_games"],3)
    def test_insufficient_games_rejected(self):
        with self.assertRaises(ValueError):
            simulate_scores([{"pf":70,"pa":60}], [{"pf":80,"pa":70}]*3)
if __name__=="__main__":
    unittest.main()
