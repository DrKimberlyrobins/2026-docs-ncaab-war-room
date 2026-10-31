"""Guard daily coverage, season selection, missing evidence, and pregame cutoffs."""
import unittest
from unittest.mock import patch
import prepare

def schedule(team,year):
    return {'url':'https://example.test/schedule','fetchedAt':'2026-10-30T10:00:00Z','data':{'events':[{'id':f'{team}-{i}','date':f'{year}-02-{i+1:02d}T12:00:00Z','competitions':[{'status':{'type':{'completed':True}},'competitors':[{'id':team,'score':80,'linescores':[{'displayValue':'40'}],'team':{}},{'id':'opponent','score':60,'linescores':[{'value':30}],'team':{}}]}]} for i in range(4)]}}

class DailyChecks(unittest.TestCase):
    def test_current_season_wins_over_prior(self):
        def read(path):
            parts=str(path).split('/')
            return schedule(parts[-1][:-5],2026) if 'schedules/2026' in str(path) else None
        e={'id':'game','date':'2026-03-01T12:00:00Z','competitions':[{'competitors':[{'id':'a','homeAway':'away'},{'id':'h','homeAway':'home'}]}]}
        with patch.object(prepare,'read',read):p=prepare.prepare(e,'2026-02-25T12:00:00Z')
        self.assertFalse(p['priorSeason']);self.assertEqual(p['state'],'ready');self.assertEqual(p['model']['full']['total'],140)
    def test_opening_day_uses_labeled_prior_reference(self):
        e={'id':'game','date':'2026-11-01T12:00:00Z','competitions':[{'competitors':[{'id':'a','homeAway':'away'},{'id':'h','homeAway':'home'}]}]}
        def read(path):
            return schedule(str(path).split('/')[-1][:-5],2026) if 'schedules/2026' in str(path) else None
        with patch.object(prepare,'read',read):p=prepare.prepare(e,'2026-10-30T12:00:00Z')
        self.assertTrue(p['priorSeason']);self.assertEqual(p['season'],2026);self.assertEqual(p['state'],'ready')
    def test_missing_games_remain_in_daily_output(self):
        events=[{'id':str(i),'date':'2026-11-01T12:00:00Z','competitions':[]} for i in range(7)]
        rows=[prepare.prepare(e,'2026-10-30T12:00:00Z') for e in events]
        self.assertEqual(len(rows),7);self.assertTrue(all(x['state']=='unavailable' for x in rows))
    def test_future_and_unfinished_games_excluded(self):
        p=schedule('a',2026);p['data']['events'][0]['competitions'][0]['status']['type']['completed']=False
        with patch.object(prepare,'read',lambda _:p):rows,_=prepare.sample('a',2026,'2026-02-03T12:00:00Z')
        self.assertEqual(len(rows),1)

    def test_ratings_after_tipoff_rejected(self):
        game={'date':'2026-11-01T19:00:00Z','competitions':[{'competitors':[
            {'id':'1','homeAway':'away','team':{'displayName':'Away'}},
            {'id':'2','homeAway':'home','team':{'displayName':'Home'}}]}]}
        ratings={'source':'test','fetchedAt':'2026-11-01T19:01:00Z','teams':{
            '1':{'adj_off':110,'adj_def':100,'adj_tempo':67},
            '2':{'adj_off':105,'adj_def':102,'adj_tempo':68}}}
        pair,error=prepare.ratings_for(game,ratings)
        self.assertIsNone(pair)
        self.assertIn('after tipoff',error)
        ratings['fetchedAt']='2026-11-01T18:59:00Z'
        pair,error=prepare.ratings_for(game,ratings)
        self.assertIsNone(error)
        self.assertEqual(pair[0].name,'Away')
    def test_ratings_without_timezone_rejected(self):
        game={'date':'2026-11-01T19:00:00Z','competitions':[{'competitors':[]}]}
        ratings={'source':'test','fetchedAt':'2026-11-01T18:00:00','teams':{}}
        pair,error=prepare.ratings_for(game,ratings)
        self.assertIsNone(pair)
        self.assertIn('timezones',error)

if __name__=='__main__':unittest.main()
