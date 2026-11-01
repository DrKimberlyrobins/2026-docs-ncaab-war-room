import copy
import unittest
from kambi_markets import parse_offers, match_event

E={'id':1,'sport':'BASKETBALL','group':'NCAAB','awayName':'Villanova','homeName':'Notre Dame','start':'2026-11-01T14:30:00Z'}
G={'id':'espn','date':E['start'],'competitions':[{'competitors':[{'team':{'id':'87','location':'Notre Dame'}},{'team':{'id':'222','location':'Villanova'}}]}]}
M={'notredame':'87','villanova':'222'}
def offer(cid='1001159940',label='Spread - 1st Half'):
 return {'id':10,'eventId':1,'criterion':{'id':cid,'label':label},'tags':['OFFERED_PREMATCH','MAIN_LINE'], 'outcomes':[
 {'id':11,'betOfferId':10,'participant':'Notre Dame','line':3500,'oddsAmerican':'-109','status':'OPEN'},
 {'id':12,'betOfferId':10,'participant':'Villanova','line':-3500,'oddsAmerican':'-120','status':'OPEN'}]}
class KambiTests(unittest.TestCase):
 def test_neutral_side_reversal_matches_by_identity(self):
  g,m=match_event(E,[G],{});self.assertEqual(g['id'],'espn');self.assertEqual(m,M)
 def test_ambiguous_or_wrong_start_never_matches(self):
  self.assertIsNone(match_event(E,[G,G],{}))
  g=copy.deepcopy(G);g['date']='2026-11-02T14:30:00Z';self.assertIsNone(match_event(E,[g],{}))
 def test_half_units_prices_ids_preserved(self):
  r=parse_offers([offer()],E,M)['half']['spread'];self.assertEqual(r['outcomes'][0]['line'],3.5);self.assertEqual(r['outcomes'][1]['price'],-120)
  self.assertEqual(r['id'],'10');self.assertEqual(r['outcomes'][0]['teamId'],'87')
 def test_closed_unknown_and_id_mismatch_withheld(self):
  for mutation in [lambda o:o['outcomes'][0].update(status='SUSPENDED'),lambda o:o.update(eventId=2),lambda o:o['outcomes'][0].update(betOfferId=2),lambda o:o['criterion'].update(label='Total Points by Villanova - 1st Half')]:
   o=offer();mutation(o);self.assertEqual(parse_offers([o],E,M)['half'],{})
 def test_alternates_dont_replace_main(self):
  a=offer();b=copy.deepcopy(a);b['tags']=['OFFERED_PREMATCH'];b['id']=20
  for x in b['outcomes']:x['betOfferId']=20;x['line']*=2
  self.assertEqual(parse_offers([b,a],E,M)['half']['spread']['id'],'10')
  a['tags']=['OFFERED_PREMATCH'];self.assertEqual(parse_offers([b,a],E,M)['half'],{})
 def test_total_not_team_total_and_no_projection_mutation(self):
  o=offer('1001159947','Total Points - 1st Half')
  for x,side in zip(o['outcomes'],['Over','Under']):x.update(label=side,line=67500)
  before=copy.deepcopy(o);r=parse_offers([o],E,M);self.assertEqual(r['half']['total']['outcomes'][0]['line'],67.5);self.assertEqual(o,before)
  o['criterion']['id']='1001159567';self.assertEqual(parse_offers([o],E,M)['half'],{})
if __name__=='__main__':unittest.main()
