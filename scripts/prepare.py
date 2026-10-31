"""Prepare every returned matchup by date from timestamped cached evidence."""
import json, math
from datetime import datetime, timezone
from pathlib import Path
from refresh import ROOT, save
from possession_simulator import Team, simulate

def number(x):
    if isinstance(x,dict): x=x.get('value',x.get('displayValue'))
    if x is None or x=='':return None
    try:
        n=float(x)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None

def read(path):
    try:return json.loads((ROOT/path).read_text())
    except (OSError,ValueError):return None

def sample(team,season,cutoff):
    p=read(Path(f'data/schedules/{season}/{team}.json'))
    if not p:return [],[]
    rows=[];sources=[{'url':p['url'],'fetchedAt':p['fetchedAt']}]
    for e in p.get('data',{}).get('events',[]):
        if not f'{season-1}-07-01'<=e['date']<f'{season}-07-01' or e['date']>=cutoff:continue
        c=(e.get('competitions') or [{}])[0]
        if not c.get('status',{}).get('type',{}).get('completed'):continue
        if c.get('type',{}).get('slug')=='exhibition' or e.get('seasonType',{}).get('type')==1:continue
        me=next((t for t in c.get('competitors',[]) if str(t['id'])==team),None)
        op=next((t for t in c.get('competitors',[]) if str(t['id'])!=team),None)
        if not me or not op:continue
        pf,pa=number(me.get('score')),number(op.get('score'))
        if pf is None or pa is None:continue
        first=lambda t:number((t.get('linescores') or [None])[0])
        rows.append({'id':e['id'],'date':e['date'],'pf':pf,'pa':pa,'hf':first(me),'ha':first(op),'opponent':op.get('team',{}).get('displayName','Unknown'),'site':'Neutral' if c.get('neutralSite') else me.get('homeAway','Unavailable')})
    rows=sorted(rows,key=lambda x:x['date'],reverse=True)[:10]
    for row in rows[:3]:
        p=read(Path(f"data/summaries/{row['id']}.json"))
        if not p:continue
        c=(p.get('data',{}).get('header',{}).get('competitions') or [{}])[0]
        if not c.get('status',{}).get('type',{}).get('completed'):continue
        me=next((t for t in c.get('competitors',[]) if str(t['id'])==team),{})
        op=next((t for t in c.get('competitors',[]) if str(t['id'])!=team),{})
        row['hf'],row['ha']=first(me),first(op)
        sources.append({'url':p['url'],'fetchedAt':p['fetchedAt']})
    return rows,sources

def baseline(a,h):
    def period(pf,pa):
        aa=[r for r in a if r[pf] is not None and r[pa] is not None]
        hh=[r for r in h if r[pf] is not None and r[pa] is not None]
        if min(len(aa),len(hh))<3:return None
        avg=lambda rows,k:sum(r[k] for r in rows)/len(rows)
        away=(avg(aa,pf)+avg(hh,pa))/2
        home=(avg(hh,pf)+avg(aa,pa))/2
        return {'away':away,'home':home,'total':away+home,'homeMargin':home-away,'nAway':len(aa),'nHome':len(hh)}
    return {'full':period('pf','pa'),'half':period('hf','ha')}

def ratings_for(matchup, ratings):
    """Only explicitly sourced adjusted ratings are accepted; no inferred KenPom data."""
    if not ratings or not isinstance(ratings.get('teams'), dict):
        return None, 'No verified adjusted-efficiency ratings feed configured.'
    if not ratings.get('source') or not ratings.get('fetchedAt'):
        return None, 'Ratings source and timestamp required.'
    # Never allow a ratings snapshot from after tipoff into a pregame forecast.
    try:
        stamp = datetime.fromisoformat(ratings['fetchedAt'].replace('Z', '+00:00'))
        tip = datetime.fromisoformat(matchup['date'].replace('Z', '+00:00'))
        if stamp.tzinfo is None or tip.tzinfo is None:
            return None, 'Ratings and tipoff timestamps must include timezones.'
        if stamp > tip:
            return None, 'Ratings were fetched after tipoff; pregame forecast blocked.'
    except (ValueError, TypeError, KeyError):
        return None, 'Invalid ratings timestamp or matchup tipoff.'
    c=(matchup.get('competitions') or [{}])[0]
    away=next((t for t in c.get('competitors',[]) if t.get('homeAway')=='away'),None)
    home=next((t for t in c.get('competitors',[]) if t.get('homeAway')=='home'),None)
    if not away or not home:return None,'Teams unavailable.'
    try:
        def team(t):
            item=ratings['teams'][str(t['id'])]
            return Team(t['team']['displayName'],float(item['adj_off']),float(item['adj_def']),float(item['adj_tempo']))
        return (team(away),team(home)),None
    except (KeyError,TypeError,ValueError):
        return None,'Verified ratings missing for one or both teams.'

def prepare(e,now,ratings=None):
    c=(e.get('competitions') or [{}])[0]
    a=next((t for t in c.get('competitors',[]) if t.get('homeAway')=='away'),None)
    h=next((t for t in c.get('competitors',[]) if t.get('homeAway')=='home'),None)
    if not a or not h:return {'id':e['id'],'state':'unavailable','reason':'Source is missing a matchup team.'}
    season=int(e['date'][:4])+(int(e['date'][5:7])>=7)
    cutoff=min(now,e['date'])
    aa,sa=sample(str(a['id']),season,cutoff);hh,sh=sample(str(h['id']),season,cutoff)
    model=baseline(aa,hh);prior=False
    if not model['full']:
        season-=1;prior=True
        aa,sa=sample(str(a['id']),season,cutoff);hh,sh=sample(str(h['id']),season,cutoff)
        model=baseline(aa,hh)
    pair,sim_error=ratings_for(e,ratings)
    sim_result=None
    if pair and e.get('date','')>now:
        try:
            sim_result=simulate(*pair,n=10000,seed=int(e['id']) % (2**32))
            sim_result['rating_source']={'source':ratings['source'],'fetchedAt':ratings['fetchedAt']}
        except (ValueError,OverflowError) as exc:
            sim_error='Simulator rejected inputs: '+str(exc)
    elif pair:
        sim_error='Game has started or passed; no retrospective pregame simulation generated.'
    return {'simulation':sim_result,'simulationStatus':sim_error,'id':e['id'],'date':e['date'],'name':e.get('name'),'preparedAt':now,'season':season,'priorSeason':prior,'modelVersion':'score-baseline-v1','model':model,'samples':{'away':aa,'home':hh},'source':sa+sh,'state':'ready' if model['full'] and model['half'] else 'partial' if model['full'] else 'unavailable','reason':None if model['full'] else 'Fewer than 3 scored games for one or both teams, or source unavailable.'}

def main():
    now=datetime.now(timezone.utc).isoformat()
    ratings=read(Path('data/ratings.json'))
    for path in sorted((ROOT/'data/slates').glob('*.json')):
        slate=json.loads(path.read_text());events=slate['data'].get('events',[])
        rows=[prepare(e,now,ratings) for e in events]
        counts={k:sum(r['state']==k for r in rows) for k in ('ready','partial','unavailable')}
        save(Path('data/daily')/path.name,{'date':path.stem,'preparedAt':now,'slateSource':{'url':slate['url'],'fetchedAt':slate['fetchedAt']},'returnedGames':len(events),'counts':counts,'matchups':rows})
        print(path.stem,len(events),'matchups',counts,flush=True)
if __name__=='__main__':main()
