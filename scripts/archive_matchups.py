"""Freeze first verified pregame receipt; store actual results separately."""
import hashlib
import copy
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball'

def time(s):
 d=datetime.fromisoformat(s.replace('Z','+00:00'))
 return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
def score(x):
 if isinstance(x,dict): x=x.get('value',x.get('displayValue'))
 try:
  n=float(x)
  return n if math.isfinite(n) and n>=0 else None
 except (TypeError,ValueError): return None

def freeze(game, payload, event, market, baseline, now):
 comp=(event.get('competitions') or [{}])[0]
 status=comp.get('status',event.get('status',{})).get('type',{})
 if not game.get('model') or status.get('state')!='pre' or status.get('completed'): return None
 tip=time(event['date'])
 if str(event['id'])!=str(game['id']) or time(game['date'])!=tip: return None
 if not time(payload['preparedAt'])<=now<tip: return None
 if not time(payload['ratingsFetchedAt'])<=now or (now-time(payload['ratingsFetchedAt'])).total_seconds()>86400: return None
 ids={c['homeAway']:str(c['team']['id']) for c in comp['competitors']}
 g=copy.deepcopy(game);g.update(awayId=ids['away'],homeId=ids['home'])
 saved_market=None
 if market and not market.get('error') and market.get('state')=='NOT_STARTED':
  mt=time(market['fetchedAt'])
  if mt<=now and (now-mt).total_seconds()<=3600 and time(market['start'])>now:
   saved_market=copy.deepcopy(market)
 if baseline and time(baseline['preparedAt'])>now: baseline=None
 return {'version':1,'id':str(game['id']),'savedAt':now.isoformat(),'scheduledTipoff':event['date'],
  'gameDate':payload['date'],'matchup':g,'config':copy.deepcopy(payload['config']),
  'ratingsFetchedAt':payload['ratingsFetchedAt'],'preparedAt':payload['preparedAt'],
  'ratingSource':payload.get('ratingSource'),'scheduleSource':payload.get('scheduleSource'),
  'verification':'ESPN pregame state and future tipoff checked at server save time',
  'gameRoomBaseline':copy.deepcopy(baseline),'kambi':saved_market,
  'marketStatus':'Frozen with pregame receipt' if saved_market else 'No verified fresh pregame market available at save time'}

def result(summary, snapshot, fetched_at):
 event=summary.get('header',{});comp=(event.get('competitions') or [{}])[0]
 if str(event.get('id'))!=snapshot['id'] or not comp.get('status',{}).get('type',{}).get('completed'): return None
 competitors={str(c.get('id',c.get('team',{}).get('id'))):c for c in comp.get('competitors',[])}
 g=snapshot['matchup'];a=competitors.get(g['awayId']);h=competitors.get(g['homeId'])
 if not a or not h:return None
 av,hv=score(a.get('score')),score(h.get('score'))
 if av is None or hv is None:return None
 def values(a,h):return {'away':a,'home':h,'total':a+h,'homeMargin':h-a}
 half=None
 if len(a.get('linescores',[]))>=2 and len(h.get('linescores',[]))>=2:
  ah,hh=score(a['linescores'][0]),score(h['linescores'][0])
  a2,h2=score(a['linescores'][1]),score(h['linescores'][1])
  if None not in (ah,hh,a2,h2) and ah+a2<=av and hh+h2<=hv:half=values(ah,hh)
 return {'fetchedAt':fetched_at,'sourceUrl':ESPN+'/summary?event='+snapshot['id'],
         'full':values(av,hv),'half':half,'status':'Final'}

def fetch(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Docs-NCAAB-Research/1.0'}),timeout=30) as r:
  raw=r.read(10_000_001)
  if len(raw)>10_000_000:raise ValueError('Source too large')
  return json.loads(raw)
def read(path,default=None):
 return json.loads(path.read_text()) if path.exists() else default
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temp.replace(path)

def main():
 folder=ROOT/'data/archive';folder.mkdir(parents=True,exist_ok=True)
 now=datetime.now(timezone.utc);errors=[];saved=0;graded=0
 for p in sorted((ROOT/'data/calculator/daily').glob('*.json')):
  payload=read(p)
  if not any(time(g['date'])>now and g.get('model') and not (folder/'games'/(g['id']+'.json')).exists() for g in payload['matchups']):continue
  try:
   slate=fetch(ESPN+'/scoreboard?groups=50&limit=1000&dates='+payload['date'].replace('-',''))
   events={str(e['id']):e for e in slate['events']}
   markets=read(ROOT/'data/kambi'/p.name,{}).get('games',{})
   baselines={str(g['id']):g for g in read(ROOT/'data/daily'/p.name,{}).get('matchups',[])}
   for game in payload['matchups']:
    path=folder/'games'/(game['id']+'.json')
    if path.exists() or game['id'] not in events:continue
    snap=freeze(game,payload,events[game['id']],markets.get(game['id']),baselines.get(game['id']),datetime.now(timezone.utc))
    if snap:
     # Exclusive creation: the original pregame snapshot is never refreshed.
     path.parent.mkdir(parents=True,exist_ok=True)
     with path.open('x') as f:json.dump({'snapshot':snap,'result':None},f,indent=2,allow_nan=False);f.write('\n')
     saved+=1
  except Exception as exc:errors.append({'date':payload['date'],'message':str(exc)})
 index=[]
 for p in sorted((folder/'games').glob('*.json')):
  record=read(p);snap=record['snapshot']
  # Later-opening periods get their own first pregame quote. Existing saved
  # offers and the original projection receipt are never replaced.
  if time(snap['scheduledTipoff'])>now:
   quote=read(ROOT/'data/kambi'/(snap['gameDate']+'.json'),{}).get('games',{}).get(snap['id'])
   if quote and not quote.get('error') and quote.get('state')=='NOT_STARTED':
    qt=time(quote['fetchedAt'])
    if qt<=now and (now-qt).total_seconds()<=3600 and time(quote['start'])>now:
     changed=False;extra=record.setdefault('additionalMarkets',{'half':{},'full':{}})
     for period in ('half','full'):
      for kind,offer in quote.get('periods',{}).get(period,{}).items():
       if kind not in (snap.get('kambi') or {}).get('periods',{}).get(period,{}) and kind not in extra[period]:
        extra[period][kind]={**copy.deepcopy(offer),'quoteFetchedAt':quote['fetchedAt'],'quoteSavedAt':now.isoformat(),'sourceUrl':quote.get('sourceUrl')};changed=True
     if changed:write(p,record)
  # Reporting is separate append-only evidence, never a change to frozen scores.
  if time(snap['scheduledTipoff'])>now:
   public=read(ROOT/'data/reports'/(snap['gameDate']+'.json'),{}).get('games',{}).get(snap['id'],{})
   retained=record.setdefault('reportEvidence',{'articles':[]})
   known={a.get('evidenceId') for a in retained['articles']};changed=False
   for article in public.get('articles',[]):
    checked=article.get('reviewedAt') or article.get('retrievedAt')
    if not checked or not time(article['publishedAt'])<time(snap['scheduledTipoff']):continue
    if not time(checked)<=now<time(snap['scheduledTipoff']):continue
    identity={k:article.get(k) for k in ('url','title','publishedAt','reviewedAt','notes')}
    fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    if fingerprint not in known:
     retained['articles'].append({**copy.deepcopy(article),'evidenceId':fingerprint,'savedAt':now.isoformat()});known.add(fingerprint);changed=True
   if changed:write(p,record)
  if not record.get('result') and time(snap['scheduledTipoff'])<now:
   try:
    actual=result(fetch(ESPN+'/summary?event='+snap['id']),snap,datetime.now(timezone.utc).isoformat())
    if actual:record['result']=actual;write(p,record);graded+=1
   except Exception as exc:errors.append({'id':snap['id'],'message':str(exc)})
  g=snap['matchup']
  index.append({'id':snap['id'],'date':snap['gameDate'],'tipoff':snap['scheduledTipoff'],
   'awayName':g['awayName'],'homeName':g['homeName'],'savedAt':snap['savedAt'],
   'final':bool(record.get('result'))})
 write(folder/'index.json',{'updatedAt':datetime.now(timezone.utc).isoformat(),'games':index})
 write(folder/'health.json',{'status':'PARTIAL' if errors else 'READY','checkedAt':datetime.now(timezone.utc).isoformat(),
  'savedThisRun':saved,'gradedThisRun':graded,'totalSaved':len(index),'errors':errors})
 print(json.dumps({'saved':saved,'graded':graded,'total':len(index),'errors':errors}))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
