import unittest
from automatic_matchups import parse_ratings, match_team, build

class AutomaticTests(unittest.TestCase):
    def html(self, count=300):
        rows=[]
        for i in range(count):
            cells=[str(i+1),'School '+str(i),'ACC','0-0','+10','110','1','100','1','70','1','0','1','0','1','0','1','0','1','0','1']
            rows.append('<tr>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr>')
        return '<h2>2027 Pomeroy College Basketball Ratings</h2><table>'+''.join(rows)+'</table>'
    def test_complete_page(self):
        r=parse_ratings(self.html(),2027)
        self.assertEqual(len(r),300)
        self.assertEqual(r['School 0']['tempo'],70)
    def test_signin_or_wrong_season_not_ratings(self):
        for html in ('<h2>Sign in</h2>',self.html().replace('2027','2026')):
            with self.assertRaises(ValueError):parse_ratings(html,2027)
    def test_incomplete_page_rejected(self):
        with self.assertRaises(ValueError):parse_ratings(self.html(50),2027)
    def test_duplicate_and_bad_rating_rejected(self):
        for html in (self.html().replace('School 1<','School 0<'),self.html().replace('<td>110</td>','<td>NaN</td>',1)):
            with self.assertRaises(ValueError):parse_ratings(html,2027)
    def test_exact_identity_and_reviewed_alias(self):
        r={'Ohio St.':{},'Connecticut':{}}
        self.assertEqual(match_team({'id':'1','location':'Ohio State'},{},r,{}),'Ohio St.')
        self.assertIsNone(match_team({'id':'41','location':'UConn'},{},r,{}))
        self.assertEqual(match_team({'id':'41','location':'UConn'},{},r,{'41':'Connecticut'}),'Connecticut')
    def test_missing_ratings_preserves_game(self):
        game={'id':'g','date':'2026-11-01T14:30Z','competitions':[{'neutralSite':True,'competitors':[{'homeAway':'away','team':{'id':'87','displayName':'Notre Dame','location':'Notre Dame'}},{'homeAway':'home','team':{'id':'222','displayName':'Villanova','location':'Villanova'}}]}]}
        ratings={'Notre Dame':dict(offense=110.6,defense=99.8,tempo=69.8),'Villanova':dict(offense=119,defense=98.3,tempo=70.4)}
        cfg=dict(nationalEfficiency=106,nationalTempo=71.5,homeAdvantagePoints=0)
        output=build([game],{},ratings,cfg,{})
        self.assertAlmostEqual(output[0]['model']['total'],148.1859)
        del ratings['Villanova']
        self.assertIsNone(build([game],{},ratings,cfg,{})[0]['model'])
        self.assertEqual(len(build([game],{},ratings,cfg,{})),1)

if __name__=='__main__':unittest.main()
