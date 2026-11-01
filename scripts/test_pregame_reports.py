import copy,json,unittest
from datetime import datetime,timezone
from pathlib import Path
from pregame_reports import parse_feed,parse_espn,for_game,safe_url
NOW=datetime(2026,11,1,12,tzinfo=timezone.utc);STAMP=NOW.isoformat()
SRC={'id':'test','name':'Local desk','kind':'Local coverage','url':'https://example.com/feed','teamIds':['87']}
G={'id':'g','awayId':'87','homeId':'222','date':'2026-11-01T14:30:00Z','model':{'total':148.2}}
def rss(title='Notre Dame basketball preview',date='Sat, 31 Oct 2026 12:00:00 GMT',url='https://example.com/preview'):
 return f'<rss><channel><item><title>{title}</title><link>{url}</link><pubDate>{date}</pubDate><author>Reporter</author><category>Basketball</category></item></channel></rss>'
class ReportsTests(unittest.TestCase):
 def test_rss_attribution_and_headline_not_status(self):
  a=parse_feed(rss(),SRC,STAMP)[0];self.assertEqual(a['author'],'Reporter');self.assertTrue(a['headlineOnly']);self.assertEqual(a['notes'],[])
 def test_future_stale_wrong_sport_and_unsafe_links_excluded(self):
  for raw in [rss(date='Mon, 02 Nov 2026 12:00:00 GMT'),rss(date='Thu, 01 Oct 2026 12:00:00 GMT'),rss(title='Notre Dame women basketball'),rss(title='Notre Dame football update'),rss(url='javascript:alert(1)')]:self.assertEqual(parse_feed(raw,SRC,STAMP),[])
 def test_atom_author_and_link(self):
  raw='<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Notre Dame basketball</title><link href="https://example.com/article"/><published>2026-10-31T12:00:00Z</published><author><name>Named Reporter</name></author></entry></feed>'
  self.assertEqual(parse_feed(raw,SRC,STAMP)[0]['author'],'Named Reporter')
 def test_exact_ids_scope_and_posttip_exclusion(self):
  a=parse_feed(rss(),SRC,STAMP)[0];before=copy.deepcopy(G)
  self.assertEqual(len(for_game(G,[a],NOW)),1);a['teamIds']=['99'];self.assertEqual(for_game(G,[a],NOW),[])
  a['teamIds']=['87'];a['eventIds']=['wrong'];self.assertEqual(for_game(G,[a],NOW),[])
  a['eventIds']=['g'];a['publishedAt']='2026-11-01T15:00:00Z';self.assertEqual(for_game(G,[a],datetime(2026,11,1,16,tzinfo=timezone.utc)),[]);self.assertEqual(G,before)
 def test_reviewed_notes_win_dedupe_and_expire(self):
  a=parse_feed(rss(),SRC,STAMP)[0];b=copy.deepcopy(a);b.update(notes=[{'text':'Reported uncertainty'}],reviewedAt=STAMP,validUntil='2026-11-01T13:00:00Z')
  self.assertTrue(for_game(G,[a,b],NOW)[0]['notes']);self.assertFalse(for_game(G,[a,b],datetime(2026,11,1,14,tzinfo=timezone.utc))[0]['notes'])
 def test_national_ids_require_mens_basketball_category(self):
  a={'id':1,'headline':'Preview','published':'2026-10-31T12:00:00Z','links':{'web':{'href':'https://example.com/a'}},'categories':[{'type':'team','sportId':41,'teamId':87}]}
  self.assertEqual(parse_espn({'articles':[a]},STAMP)[0]['teamIds'],['87']);a['categories'][0]['sportId']=23;self.assertEqual(parse_espn({'articles':[a]},STAMP),[])
 def test_reviewed_sources_have_safe_links_and_no_confirmed_starting_five_claim(self):
  path=Path(__file__).resolve().parents[1]/'config/reviewed-reports.json'
  for a in json.loads(path.read_text()):
   self.assertTrue(safe_url(a['url']));self.assertTrue(a['author']);self.assertTrue(a['reviewedAt']);self.assertTrue(a['eventIds']);self.assertNotIn('Confirmed starter',[n['status'] for n in a['notes']])
if __name__=='__main__':unittest.main()
