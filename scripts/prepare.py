"""Prepare every returned matchup by date from timestamped cached evidence."""
import json, math
from datetime import datetime, timezone
from pathlib import Path
from refresh import ROOT, save

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

def prepare(e,now):
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
    return {'id':e['id'],'date':e['date'],'name':e.get('name'),'preparedAt':now,'season':season,'priorSeason':prior,'modelVersion':'score-baseline-v1','model':model,'samples':{'away':aa,'home':hh},'source':sa+sh,'state':'ready' if model['full'] and model['half'] else 'partial' if model['full'] else 'unavailable','reason':None if model['full'] else 'Fewer than 3 scored games for one or both teams, or source unavailable.'}

def main():
    now=datetime.now(timezone.utc).isoformat()
    for path in sorted((ROOT/'data/slates').glob('*.json')):
        slate=json.loads(path.read_text());events=slate['data'].get('events',[])
        rows=[prepare(e,now) for e in events]
        counts={k:sum(r['state']==k for r in rows) for k in ('ready','partial','unavailable')}
        save(Path('data/daily')/path.name,{'date':path.stem,'preparedAt':now,'slateSource':{'url':slate['url'],'fetchedAt':slate['fetchedAt']},'returnedGames':len(events),'counts':counts,'matchups':rows})
        print(path.stem,len(events),'matchups',counts,flush=True)
if __name__=='__main__':main()
