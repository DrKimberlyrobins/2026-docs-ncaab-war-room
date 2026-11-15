"""Freeze first verified pregame receipt; store actual results separately."""
import hashlib
import copy
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from grade_frozen_scores import grade, pregame, residuals, schedule_check
from rank_matchup_markets import load_history, markets, replay, settle, VERSION
from kalshi_markets import collect as collect_kalshi

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
 if not time(payload['ratingsFetchedAt'])<=time(payload['preparedAt']) or (now-time(payload['ratingsFetchedAt'])).total_seconds()>86400: return None
 ids={c['homeAway']:str(c['team']['id']) for c in comp['competitors']}
 if any(game.get(side+'Id') and str(game[side+'Id'])!=ids[side] for side in ('away','home')): return None
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
 for team,side in ((a,'away'),(h,'home')):
  if team.get('homeAway') and team['homeAway']!=side:return None
 if comp.get('date') and time(comp['date'])<=time(snapshot['savedAt']):return None
 if fetched_at and comp.get('date') and time(comp['date'])>=time(fetched_at):return None
 av,hv=score(a.get('score')),score(h.get('score'))
 if av is None or hv is None:return None
 def values(a,h):return {'away':a,'home':h,'total':a+h,'homeMargin':h-a}
 half=None
 if len(a.get('linescores',[]))>=2 and len(h.get('linescores',[]))>=2:
  ah,hh=score(a['linescores'][0]),score(h['linescores'][0])
  a2,h2=score(a['linescores'][1]),score(h['linescores'][1])
  def valid_periods(team, final):
   periods=[score(part) for part in team['linescores']]
   return None not in periods and sum(periods)==final
  if None not in (ah,hh,a2,h2) and valid_periods(a,av) and valid_periods(h,hv):half=values(ah,hh)
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

def main(include_kalshi=False):
 folder=ROOT/'data/archive';folder.mkdir(parents=True,exist_ok=True)
 now=datetime.now(timezone.utc);errors=[];saved=0;graded=0
 # The cached ESPN evidence index includes moved games on their revised dates.
 event_index={}
 for path in sorted((ROOT/'data/slates').glob('*.json')):
  evidence=read(path,{})
  for event in evidence.get('data',{}).get('events',[]):
   key=str(event['id'])
   stamp=evidence.get('fetchedAt','')
   if key not in event_index or stamp>event_index[key][0]:
    event_index[key]=(stamp,event)
 events={key:pair[1] for key,pair in event_index.items()}
 history=grade((read(p) for p in (folder/'games').glob('*.json')),events)
 for p in sorted((ROOT/'data/calculator/daily').glob('*.json')):
  payload=read(p)
  if not any(time(g['date'])>now and g.get('model') and not (folder/'games'/(g['id']+'.json')).exists() for g in payload['matchups']):continue
  try:
   slate=fetch(ESPN+'/scoreboard?groups=50&limit=1000&dates='+payload['date'].replace('-',''))
   events={str(e['id']):e for e in slate['events']}
   quotes=read(ROOT/'data/kambi'/p.name,{}).get('games',{})
   baselines={str(g['id']):g for g in read(ROOT/'data/daily'/p.name,{}).get('matchups',[])}
   for game in payload['matchups']:
    path=folder/'games'/(game['id']+'.json')
    if path.exists() or game['id'] not in events:continue
    snap=freeze(game,payload,events[game['id']],quotes.get(game['id']),baselines.get(game['id']),datetime.now(timezone.utc))
    if snap:
     # Exclusive creation: the original pregame snapshot is never refreshed.
     path.parent.mkdir(parents=True,exist_ok=True)
     decisions=markets(snap,snap['kambi'],residuals(history,snap))
     with path.open('x') as f:
      json.dump({'snapshot':snap,'result':None,'decisionEvidence':{'version':VERSION,'markets':[{**row,'evaluatedAt':snap['savedAt']} for row in decisions]}},f,indent=2,allow_nan=False)
      f.write('\n')
     saved+=1
  except Exception as exc:errors.append({'date':payload['date'],'message':str(exc)})
 index=[];records=[]
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
  check=schedule_check(record,events)
  if time(snap['scheduledTipoff'])>now and not check and pregame(snap):
   quote=read(ROOT/'data/kambi'/(snap['gameDate']+'.json'),{}).get('games',{}).get(snap['id'])
   current={**snap,'savedAt':now.isoformat()}
   rows=markets(current,quote,residuals(history,current))
   if rows:
    evidence=record.setdefault('decisionEvidence',{'version':VERSION,'markets':[]})
    known={(row['outcomeId'],row['line'],row['price']) for row in evidence['markets']}
    new=[{**row,'evaluatedAt':now.isoformat()} for row in rows
         if (row['outcomeId'],row['line'],row['price']) not in known]
    if new:
     evidence['markets'].extend(new)
     write(p,record)
  previous=record.get('result')
  if not (check and check['exclude']) and (not previous or not previous.get('half')) and time(snap['scheduledTipoff'])<now:
   try:
    actual=result(fetch(ESPN+'/summary?event='+snap['id']),snap,datetime.now(timezone.utc).isoformat())
    if actual and (not previous or actual.get('half')):
     record['result']=actual;write(p,record);graded+=1
   except Exception as exc:errors.append({'id':snap['id'],'message':str(exc)})
  records.append(record)
  g=snap['matchup']
  index.append({'id':snap['id'],'date':snap['gameDate'],'tipoff':snap['scheduledTipoff'],
   'awayName':g['awayName'],'homeName':g['homeName'],'savedAt':snap['savedAt'],
   'final':bool(record.get('result')),'scheduleCheck':check})
 report=grade(records,events)
 for record in records:
  if record.get('result') and record.get('decisionEvidence'):
   snap=record['snapshot']
   day=report['dates'][snap['gameDate']]
   if snap['id'] not in day['forecastErrors']:continue
   check=day['scheduleChecks'].get(snap['id'],{})
   cutoff=min(time(snap['scheduledTipoff']),time(check.get('revisedTipoff',snap['scheduledTipoff'])))
   timely=[row for row in record['decisionEvidence']['markets']
           if time(row.get('evaluatedAt',row['quoteFetchedAt']))<cutoff]
   day.setdefault('marketResults',{})[snap['id']]=list(settle(timely,snap,record['result']))
 report['marketReplay']=replay(records,report,load_history(ROOT/'data/kambi/history'))
 write(folder/'score-grades.json',report)
 board={}
 for record in records:
  snap=record['snapshot']
  if time(snap['scheduledTipoff'])<=now or record.get('result') or schedule_check(record,events) or not pregame(snap):continue
  quote=read(ROOT/'data/kambi'/(snap['gameDate']+'.json'),{}).get('games',{}).get(snap['id'])
  current={**snap,'savedAt':now.isoformat()}
  rows=markets(current,quote,residuals(report,current))
  board.setdefault(snap['gameDate'],{})[snap['id']]={'markets':rows,'tipoff':snap['scheduledTipoff']}
 if include_kalshi:
  candidates=[r['snapshot'] for r in records
              if time(r['snapshot']['scheduledTipoff'])>now and not r.get('result')
              and not schedule_check(r,events) and pregame(r['snapshot'])]
  exchange=collect_kalshi(candidates,report,residuals) if candidates else {'status':{},'dates':{}}
  for games in exchange['dates'].values():
   for game_id,game in games.items():
    path=folder/'games'/(game_id+'.json')
    record=read(path)
    evidence=record.setdefault('kalshiEvidence',{'version':VERSION,'markets':[]})
    known={(row['ticker'],row['answer']) for row in evidence['markets']}
    newly_observed=[row for row in game['markets'] if (row['ticker'],row['answer']) not in known]
    if newly_observed:
     evidence['markets'].extend(newly_observed)
     write(path,record)
  write(folder/'kalshi-board.json',exchange)
 write(folder/'market-board.json',{'updatedAt':now.isoformat(),'modelVersion':VERSION,'dates':board})
 write(folder/'index.json',{'updatedAt':datetime.now(timezone.utc).isoformat(),'games':index})
 write(folder/'health.json',{'status':'PARTIAL' if errors else 'READY','checkedAt':datetime.now(timezone.utc).isoformat(),
  'savedThisRun':saved,'gradedThisRun':graded,'totalSaved':len(index),'errors':errors})
 print(json.dumps({'saved':saved,'graded':graded,'total':len(index),'errors':errors}))
 if errors:raise SystemExit(1)
if __name__=='__main__':main(include_kalshi=True)
