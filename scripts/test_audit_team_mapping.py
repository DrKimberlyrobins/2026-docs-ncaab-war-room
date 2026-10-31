"""Ensure team identity audit cannot accidentally approve ratings."""
import unittest
from audit_team_mapping import audit

def sample():
    espn = {"data": {"sports": [{"leagues": [{"teams": [
        {"team": {"id": "1", "displayName": "Alpha University"}},
        {"team": {"id": "2", "displayName": "Beta College"}},
        {"team": {"id": "3", "displayName": "Gamma State"}},
    ]}]}]}}
    staged = {"teams": [{"team": "Alpha University"},
                        {"team": "Beta-College"},
                        {"team": "Other University"}]}
    return espn, staged

class AuditTests(unittest.TestCase):
    def test_only_exact_normalized_candidates(self):
        result = audit(*sample())
        self.assertEqual(result["status"], "AUDIT_ONLY_NOT_APPROVED")
        self.assertEqual({x["espnId"] for x in result["exactCandidates"]}, {"1", "2"})
        self.assertEqual([x["espnId"] for x in result["unmatchedESPN"]], ["3"])
        self.assertNotIn("teams", result)

    def test_duplicate_normalized_source_is_ambiguous(self):
        espn, staged = sample()
        staged["teams"].append({"team": "ALPHA-UNIVERSITY"})
        result = audit(espn, staged)
        self.assertEqual([x["espnId"] for x in result["ambiguous"]], ["1"])
        self.assertNotIn("1", {x["espnId"] for x in result["exactCandidates"]})

if __name__ == "__main__":
    unittest.main()
