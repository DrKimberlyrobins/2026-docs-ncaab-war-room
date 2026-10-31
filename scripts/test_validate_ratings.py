"""Regression checks for the staged ratings safety gate."""
import unittest
from datetime import datetime, timezone
from validate_ratings import build

STAMP = "2026-10-31T12:00:00Z"
NOW = datetime(2026, 10, 31, 13, tzinfo=timezone.utc)

def fixtures():
    teams = [{"team": f"School {i}", "adj_o": 105, "adj_d": 102, "adj_t": 68}
             for i in range(300)]
    return ({"status": "UNMATCHED_DO_NOT_SIMULATE", "source": "test",
             "fetchedAt": STAMP, "teams": teams},
            {str(i + 1): f"School {i}" for i in range(300)})

class ValidationTests(unittest.TestCase):
    def test_exact_verified_mapping(self):
        staged, mapping = fixtures()
        result = build(staged, mapping, now=NOW)
        self.assertEqual(len(result["teams"]), 300)
        self.assertEqual(result["teams"]["1"]["adj_tempo"], 68)

    def test_unmatched_team_rejected(self):
        staged, mapping = fixtures()
        mapping["1"] = "Unknown"
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            build(staged, mapping, now=NOW)

    def test_duplicate_mapping_rejected(self):
        staged, mapping = fixtures()
        mapping["2"] = mapping["1"]
        with self.assertRaisesRegex(ValueError, "multiple"):
            build(staged, mapping, now=NOW)

    def test_too_few_mappings_rejected(self):
        staged, mapping = fixtures()
        del mapping["300"]
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            build(staged, mapping, now=NOW)

    def test_nonfinite_rating_rejected(self):
        staged, mapping = fixtures()
        staged["teams"][0]["adj_o"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            build(staged, mapping, now=NOW)

    def test_future_timestamp_rejected(self):
        staged, mapping = fixtures()
        staged["fetchedAt"] = "2026-11-01T12:00:00Z"
        with self.assertRaisesRegex(ValueError, "Future"):
            build(staged, mapping, now=NOW)

if __name__ == "__main__":
    unittest.main()
