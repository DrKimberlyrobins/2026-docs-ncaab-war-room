"""Cache team schedules and actual half scores for teams in upcoming source slates."""
from refresh import BASE, ROOT, fetch, save
import json
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def fresh(path):
    p=ROOT/path
    try:
        fetched=datetime.fromisoformat(json.loads(p.read_text())['fetchedAt'].replace('Z','+00:00'))
        return (datetime.now(timezone.utc)-fetched).total_seconds()<43200
    except (OSError,ValueError,KeyError):return False

def warm(team):
    errors=[]
    year=datetime.now(timezone.utc).year+(datetime.now(timezone.utc).month>=7)
    for season in (year-1,year):
        path=Path(f'data/schedules/{season}/{team}.json')
        try:
            if fresh(path): p=json.loads((ROOT/path).read_text())
            else:
                p=fetch(f'/teams/{team}/schedule?season={season}')
                events=[]
                for e in p['data'].get('events',[]):
                    # ESPN sometimes reports current season metadata for historical responses.
                    if not f'{season-1}-07-01'<=e['date']<f'{season}-07-01': continue
                    item={k:e[k] for k in ('id','date','name','season','seasonType') if k in e};item['competitions']=[]
                    for c in e.get('competitions',[]):
                        co={k:c[k] for k in ('status','neutralSite','type') if k in c}
                        co['competitors']=[{**{k:t[k] for k in ('id','homeAway','score','linescores') if k in t},'team':{'displayName':t.get('team',{}).get('displayName','Unknown')}} for t in c.get('competitors',[])]
                        item['competitions'].append(co)
                    events.append(item)
                p['data']={'events':events};save(path,p)
            completed=[e for e in p['data']['events'] if e.get('competitions',[{}])[0].get('status',{}).get('type',{}).get('completed') and e.get('seasonType',{}).get('type')!=1 and e.get('competitions',[{}])[0].get('type',{}).get('slug')!='exhibition']
            for e in sorted(completed,key=lambda x:x['date'],reverse=True)[:3]:
                sp=Path(f"data/summaries/{e['id']}.json")
                if (ROOT/sp).exists():continue
                summary=fetch('/summary?event='+e['id'])
                header=summary['data'].get('header',{})
                header['competitions']=[{'status':c.get('status'),'competitors':[{k:t[k] for k in ('id','homeAway','score','linescores') if k in t} for t in c.get('competitors',[])]} for c in header.get('competitions',[])]
                summary['data']={'header':header};save(sp,summary)
        except Exception as exc:errors.append(f'{team}/{season}: {exc}')
    return errors
if __name__=='__main__':
    import os
    ids=set(os.environ.get('NCAAB_SEED_TEAMS','').split(','))-{''}
    if not ids:
        for path in (ROOT/'data/slates').glob('*.json'):
            for e in json.loads(path.read_text())['data'].get('events',[]):
                if datetime.fromisoformat(e['date'].replace('Z','+00:00'))<datetime.now(timezone.utc):continue
                for c in e.get('competitions',[]):
                    ids.update(str(t['id']) for t in c.get('competitors',[]))
    errors=[]
    with ThreadPoolExecutor(max_workers=16) as pool:
        for result in pool.map(warm,sorted(ids)): errors.extend(result)
    print('Cached schedule evidence for',len(ids),'teams;',len(errors),'source failures')
    save(Path('data/schedule-health.json'),{'checkedAt':datetime.now(timezone.utc).isoformat(),'teamsRequested':len(ids),'failures':errors})
    if errors:raise SystemExit(1)
