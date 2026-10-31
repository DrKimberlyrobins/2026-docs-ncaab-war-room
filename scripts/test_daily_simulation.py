"""Daily simulation input contract regression tests."""
import unittest
from prepare import ratings_for

def game():
    return {'competitions':[{'competitors':[
        {'id':'1','homeAway':'away','team':{'displayName':'Away'}},
        {'id':'2','homeAway':'home','team':{'displayName':'Home'}}
    ]}]}

class DailyRatingsTests(unittest.TestCase):
    def test_missing_source_blocks(self):
        pair,reason=ratings_for(game(),None)
        self.assertIsNone(pair)
        self.assertIn('No verified',reason)
    def test_missing_team_blocks(self):
        pair,reason=ratings_for(game(),{'source':'test','fetchedAt':'2026-10-31','teams':{'1':{'adj_off':110,'adj_def':100,'adj_tempo':70}}})
        self.assertIsNone(pair)
        self.assertIn('missing',reason)
    def test_valid_pair(self):
        data={'source':'test fixture','fetchedAt':'2026-10-31','teams':{
            '1':{'adj_off':110,'adj_def':100,'adj_tempo':70},
            '2':{'adj_off':115,'adj_def':95,'adj_tempo':72}}}
        pair,reason=ratings_for(game(),data)
        self.assertIsNone(reason)
        self.assertEqual(pair[0].name,'Away')
        self.assertEqual(pair[1].adj_tempo,72)

if __name__=='__main__':
    unittest.main()
