import copy,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
import archive_matchups as archive

NOW=datetime(2026,11,1,10,tzinfo=timezone.utc)
GAME={'id':'1','date':'2026-11-01T14:30:00Z','awayName':'ND','homeName':'Nova','model':{'away':70,'home':77,'total':147,'homeMargin':7},'firstHalf':{'away':32,'home':36,'total':68,'homeMargin':4}}
PAYLOAD={'date':'2026-11-01','preparedAt':'2026-11-01T09:00:00Z','ratingsFetchedAt':'2026-11-01T09:00:00Z','config':{'season':2027},'matchups':[GAME]}
EVENT={'id':'1','date':GAME['date'],'status':{'type':{'state':'pre'}},'competitions':[{'competitors':[{'homeAway':'away','team':{'id':'87'}},{'homeAway':'home','team':{'id':'222'}}]}]}
def freeze(g=GAME,p=PAYLOAD,e=EVENT,m=None):return archive.freeze(g,p,e,m,None,NOW)
def summary():return {'header':{'id':'1','competitions':[{'status':{'type':{'completed':True}},'competitors':[{'id':'87','score':'75','linescores':[{'value':35},{'value':35},{'value':5}]},{'id':'222','score':'80','linescores':[{'value':36},{'value':34},{'value':10}]}]}]}}
class ArchiveTests(unittest.TestCase):
 def test_freeze_copies_inputs(self):
  g=copy.deepcopy(GAME);s=freeze(g=g);g['model']['total']=999;self.assertEqual(s['matchup']['model']['total'],147);self.assertEqual(s['matchup']['awayId'],'87')
 def test_started_future_preparation_wrong_event_and_stale_ratings_blocked(self):
  e=copy.deepcopy(EVENT);e['status']['type']['state']='in';self.assertIsNone(freeze(e=e))
  p=copy.deepcopy(PAYLOAD);p['preparedAt']='2026-11-01T15:00:00Z';self.assertIsNone(freeze(p=p))
  p['preparedAt']=PAYLOAD['preparedAt'];p['ratingsFetchedAt']='2026-10-29T10:00:00Z';self.assertIsNone(freeze(p=p))
  e=copy.deepcopy(EVENT);e['id']='different';self.assertIsNone(freeze(e=e))
  self.assertIsNone(archive.freeze(GAME,PAYLOAD,EVENT,None,None,datetime(2026,11,1,15,tzinfo=timezone.utc)))
 def test_stale_markets_not_saved(self):
  m={'state':'NOT_STARTED','fetchedAt':'2026-11-01T08:00:00Z','start':GAME['date']};self.assertIsNone(freeze(m=m)['kambi'])
 def test_final_and_halftime_exclude_overtime(self):
  r=archive.result(summary(),freeze(),NOW.isoformat());self.assertEqual(r['full']['total'],155);self.assertEqual(r['half']['total'],71)
 def test_unfinished_wrong_identity_missing_score_never_graded(self):
  d=summary();d['header']['competitions'][0]['status']['type']['completed']=False;self.assertIsNone(archive.result(d,freeze(),NOW.isoformat()))
  d=summary();d['header']['id']='2';self.assertIsNone(archive.result(d,freeze(),NOW.isoformat()))
  d=summary();d['header']['competitions'][0]['competitors'][0]['score']=None;self.assertIsNone(archive.result(d,freeze(),NOW.isoformat()))
 def test_missing_halves_never_invented(self):
  d=summary();d['header']['competitions'][0]['competitors'][0]['linescores']=[]
  self.assertIsNone(archive.result(d,freeze(),NOW.isoformat())['half'])
 def test_repeat_run_preserves_original_receipt(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'data/calculator/daily/2099-11-01.json';p.parent.mkdir(parents=True)
   payload=copy.deepcopy(PAYLOAD);payload['date']='2099-11-01';payload['matchups'][0]['date']='2099-11-01T14:30:00Z'
   event=copy.deepcopy(EVENT);event['date']=payload['matchups'][0]['date'];p.write_text(json.dumps(payload))
   with patch.object(archive,'ROOT',root),patch.object(archive,'fetch',return_value={'events':[event]}):
    archive.main();target=root/'data/archive/games/1.json';before=json.loads(target.read_text())['snapshot'];payload['matchups'][0]['model']['total']=999;p.write_text(json.dumps(payload));archive.main();after=json.loads(target.read_text())['snapshot'];self.assertEqual(before,after)
 def test_later_opened_market_is_saved_separately_once(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/'data/archive/games';folder.mkdir(parents=True)
   snap=freeze();snap['scheduledTipoff']='2099-11-01T14:30:00Z';snap['matchup']['date']=snap['scheduledTipoff']
   target=folder/'1.json';target.write_text(json.dumps({'snapshot':snap,'result':None}))
   quote={'state':'NOT_STARTED','fetchedAt':datetime.now(timezone.utc).isoformat(),'start':snap['scheduledTipoff'],'periods':{'half':{'total':{'id':'offer','outcomes':[{'price':-110}]}}}}
   qp=root/'data/kambi/2026-11-01.json';qp.parent.mkdir(parents=True);qp.write_text(json.dumps({'games':{'1':quote}}))
   with patch.object(archive,'ROOT',root):
    archive.main();first=json.loads(target.read_text());quote['periods']['half']['total']['outcomes'][0]['price']=-150;qp.write_text(json.dumps({'games':{'1':quote}}));archive.main();second=json.loads(target.read_text())
   self.assertEqual(first['snapshot'],snap);self.assertEqual(first['additionalMarkets'],second['additionalMarkets']);self.assertEqual(second['snapshot'],snap)
if __name__=='__main__':unittest.main()
