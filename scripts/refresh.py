"""Fetch timestamped ESPN snapshots without replacing good files on source failure."""
import json, os, time, urllib.request, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
BASE='https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball'
ROOT=Path(__file__).resolve().parents[1]
def fetch(path):
    url=BASE+path
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Docs-NCAAB-Research/1.0'})
            with urllib.request.urlopen(req,timeout=35) as r: data=json.load(r)
            return {'data':data,'url':url,'fetchedAt':datetime.now(timezone.utc).isoformat()}
        except Exception:
            if attempt==2: raise
            time.sleep(attempt+1)
def compact(obj):
    d=obj['data']
    if 'sports' in d:
        obj['data']={'sports':[{'leagues':[{'teams':[{'team':{k:t['team'][k] for k in ('id','displayName','abbreviation') if k in t['team']}} for t in l.get('teams',[])]} for l in s.get('leagues',[])]} for s in d['sports']]}
    elif 'events' in d:
        out=[]
        for e in d['events']:
            item={k:e[k] for k in ('id','name','date','status','season') if k in e}
            item['competitions']=[]
            for c in e.get('competitions',[]):
                co={k:c[k] for k in ('id','date','neutralSite','venue','odds','status') if k in c}
                co['competitors']=[{**{k:t[k] for k in ('id','homeAway','score','linescores') if k in t},'team':{k:t.get('team',{})[k] for k in ('id','displayName','abbreviation') if k in t.get('team',{})}} for t in c.get('competitors',[])]
                item['competitions'].append(co)
            out.append(item)
        obj['data']={'events':out}
    obj['transformation']='Display fields retained from ESPN response; no statistics inferred.'
    return obj

def save(path,obj):
    path=ROOT/path; path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp'); tmp.write_text(json.dumps(obj,separators=(',',':'))); tmp.replace(path)
def main():
    failures=[]
    jobs=[('teams?groups=50&limit=1000','data/teams.json')]
    today=datetime.now(ZoneInfo('America/Chicago')).date()
    for day in [today+timedelta(days=i) for i in range(-1,5)]:
        jobs.append(('scoreboard?groups=50&limit=1000&dates='+day.strftime('%Y%m%d'),'data/slates/'+day.isoformat()+'.json'))
    for endpoint,path in jobs:
        try:
            result=fetch('/'+endpoint)
            if 'teams?' in endpoint and not result['data'].get('sports'): raise ValueError('Malformed team source')
            if 'scoreboard?' in endpoint and 'events' not in result['data']: raise ValueError('Malformed scoreboard source')
            save(Path(path),compact(result))
            print('Updated',path)
        except Exception as exc:
            failures.append(path+': '+str(exc)); print('SOURCE FAILURE',failures[-1])
    save(Path('data/health.json'),{'checkedAt':datetime.now(timezone.utc).isoformat(),'failures':failures})
    if failures: raise SystemExit(1)
if __name__=='__main__': main()
