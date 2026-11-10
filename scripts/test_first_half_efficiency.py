import unittest
from first_half_efficiency import project

STAMP = "2026-11-09T12:00:00+00:00"
TIP = "2026-11-09T23:00:00+00:00"
A = {"offense": 110, "defense": 100, "tempo": 70}
H = {"offense": 120, "defense": 90, "tempo": 72}


def run(**kwargs):
    return project(A, H, national_efficiency=100, ratings_at=STAMP,
                   tipoff_at=TIP, **kwargs)


class EfficiencyTests(unittest.TestCase):
    def test_possession_and_scores(self):
        p = run()
        possession = (70 * 72) ** .5 / 2
        self.assertAlmostEqual(p["firstHalfPossessions"], possession)
        self.assertAlmostEqual(p["away"], possession * .99)
        self.assertAlmostEqual(p["home"], possession * 1.2)
        self.assertAlmostEqual(p["total"], p["away"] + p["home"])
        self.assertAlmostEqual(p["homeMargin"], p["home"] - p["away"])

    def test_home_advantage_affects_margin_not_total(self):
        base = run()
        adjusted = run(home_advantage_full_game=4)
        self.assertAlmostEqual(adjusted["homeMargin"] - base["homeMargin"], 2)
        self.assertAlmostEqual(adjusted["total"], base["total"])
        self.assertAlmostEqual(run(neutral=True, home_advantage_full_game=4)["homeMargin"],
                               base["homeMargin"])

    def test_no_future_rating_leakage(self):
        with self.assertRaises(ValueError):
            project(A, H, national_efficiency=100, ratings_at=TIP, tipoff_at=TIP)
        with self.assertRaises(ValueError):
            project(A, H, national_efficiency=100,
                    ratings_at="2026-11-10T00:00:00Z", tipoff_at=TIP)

    def test_missing_or_invalid_inputs(self):
        with self.assertRaises(ValueError):
            project(dict(A, offense=None), H, national_efficiency=100,
                    ratings_at=STAMP, tipoff_at=TIP)
        with self.assertRaises(ValueError):
            run(first_half_pace_factor=float("nan"))
        with self.assertRaises(ValueError):
            run(tempo_method="unknown")

    def test_no_invented_probabilities(self):
        p = run()
        self.assertIsNone(p["coverProbability"])
        self.assertIsNone(p["firstTenMinutes"])
        self.assertEqual(p["status"], "BASELINE_UNCALIBRATED")


if __name__ == "__main__":
    unittest.main()
