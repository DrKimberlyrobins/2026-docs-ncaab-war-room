import unittest
from unittest.mock import patch
import first_half as half


def fixture(season=2026):
    events=[]
    for i in range(3):
        events.append({'id':str(i),'date':f'{season}-02-0{i+1}T12:00:00Z','seasonType':{'type':2},
          'competitions':[{'status':{'type':{'completed':True}},'competitors':[
            {'id':'1','score':100,'linescores':[{'value':30},{'value':50},{'value':20}]},
            {'id':'2','score':90,'linescores':[{'value':40},{'value':40},{'value':10}]}]}]})
    return {'url':'https://example.test/schedule','fetchedAt':'2026-10-31T12:00:00Z','data':{'events':events}}

class FirstHalfTests(unittest.TestCase):
    def test_overtime_excluded_from_shares(self):
        with patch.object(half,'read',lambda path:fixture()):
            p=half.season_profile('1',2026,'2026-11-01T12:00:00Z')
        self.assertEqual(p['games'],3)
        self.assertEqual(p['scoringShare'],30/80)
        self.assertEqual(p['allowingShare'],40/80)

    def test_future_or_unfinished_does_not_enter_profile(self):
        f=fixture();f['data']['events'][0]['competitions'][0]['status']['type']['completed']=False
        with patch.object(half,'read',lambda path:f):
            self.assertIsNone(half.season_profile('1',2026,'2026-11-01T12:00:00Z'))
        with patch.object(half,'read',lambda path:fixture()):
            self.assertIsNone(half.season_profile('1',2026,'2026-02-03T12:00:00Z'))

    def test_missing_half_scores_not_fixed_fifty_percent(self):
        self.assertIsNone(half.project({'away':80,'home':80},None,None))
        f=fixture()
        for e in f['data']['events']:
            e['competitions'][0]['competitors'][0]['linescores']=[{'value':30}]
        with patch.object(half,'read',lambda path:f):
            self.assertIsNone(half.season_profile('1',2026,'2026-11-01T12:00:00Z'))

    def test_current_season_preferred_and_fallback_labeled(self):
        with patch.object(half,'read',lambda path:fixture(2027)):
            p=half.profile('1',2027,'2027-03-01T12:00:00Z')
        self.assertFalse(p['priorSeason'])
        with patch.object(half,'read',lambda path:fixture() if '2026/' in str(path) else None):
            p=half.profile('1',2027,'2026-11-01T12:00:00Z')
        self.assertTrue(p['priorSeason']);self.assertEqual(p['season'],2026)

    def test_opponent_timing_changes_matchup(self):
        a={'scoringShare':.4,'allowingShare':.5}
        h={'scoringShare':.45,'allowingShare':.48}
        p=half.project({'away':80,'home':90},a,h)
        self.assertAlmostEqual(p['away'],35.2)
        self.assertAlmostEqual(p['home'],42.75)
        self.assertAlmostEqual(p['total'],77.95)
        self.assertAlmostEqual(p['homeMargin'],7.55)

    def test_summary_recovers_real_halves(self):
        f=fixture()
        summary={'url':'https://example.test/summary','fetchedAt':'2026-10-31T12:00:00Z','data':{'header':{'competitions':[f['data']['events'][0]['competitions'][0]]}}}
        import copy
        f=copy.deepcopy(f)
        for e in f['data']['events']:
            for t in e['competitions'][0]['competitors']:t.pop('linescores')
        with patch.object(half,'read',lambda path:summary if 'summaries' in str(path) else f):
            p=half.season_profile('1',2026,'2026-11-01T12:00:00Z')
        self.assertEqual(p['firstScoredAverage'],30)
        self.assertEqual(p['sources'][0]['url'],'https://example.test/summary')

if __name__=='__main__':unittest.main()
