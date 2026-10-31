"""Offline regression checks for CSV importer syntax and source validation."""
import unittest
from stage_torvik_csv import parse_csv

class ImporterTests(unittest.TestCase):
    def test_missing_fields_rejected(self):
        with self.assertRaises(ValueError):
            parse_csv("team,adjoe,adjde\nA,110,99\n")
    def test_html_rejected(self):
        with self.assertRaises(ValueError):
            parse_csv("<html>Access denied</html>")
    def test_invalid_numeric_rejected(self):
        header = "team,adjoe,adjde,adjt\n"
        rows = "".join(f"School {i},110,99,67\n" for i in range(300))
        self.assertEqual(len(parse_csv(header+rows)), 300)
        with self.assertRaises(ValueError):
            parse_csv(header+rows.replace("School 0,110,99,67", "School 0,999,99,67"))
if __name__ == "__main__":
    unittest.main()
