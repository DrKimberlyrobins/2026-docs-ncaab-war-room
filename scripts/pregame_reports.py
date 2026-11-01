"""Public-source report evidence only; no projection code, logins or paid APIs."""
import copy
import hashlib
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
ESPN='https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/news?limit=100'
class Plain(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,data):self.parts.append(data)
def plain(s):
 p=Plain();p.feed(s or '');return re.sub(r'\s+',' ',html.unescape(' '.join(p.parts))).strip()
def instant(s):
 try:d=datetime.fromisoformat(s.replace('Z','+00:00'))
 except ValueError:d=parsedate_to_datetime(s)
 return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
def safe_url(s):
 p=urlparse(s or '');return p.scheme in ('https','http') and bool(p.hostname) and not p.username and not p.password
def key(url):return url.rstrip('/').replace('http://','https://')
def recent(date,now):
 try:return now-timedelta(days=14)<=instant(date)<=now
 except (ValueError,TypeError,AttributeError):return False

def parse_feed(raw,source,stamp):
 root=ET.fromstring(raw);out=[]
 entries=root.findall('.//item') or root.findall('{http://www.w3.org/2005/Atom}entry')
 for entry in entries:
  def text(name):return next((''.join(c.itertext()).strip() for c in entry if c.tag.split('}')[-1]==name),'')
  title=plain(text('title'));url=text('link')
  if not url:
   url=next((c.attrib.get('href','') for c in entry if c.tag.split('}')[-1]=='link' and c.attrib.get('rel','alternate')=='alternate'),'')
  categories=[c.text or c.attrib.get('term','') for c in entry if c.tag.split('}')[-1]=='category']
  context=' '.join([title,url,*categories]).lower()
  if any(w in context for w in ("women",'wbb','football','volleyball')):continue
  if not source.get('basketballOnly') and not any(w in context for w in ('basketball','hoops','mbb')):continue
  if source.get('requiredTerm') and source['requiredTerm'] not in context:continue
  if not title or not safe_url(url):continue
  published=text('published') or text('pubDate')
  if not recent(published,instant(stamp)):continue
  author=text('creator') or text('author') or 'Byline not provided'
  out.append({'id':hashlib.sha256(key(url).encode()).hexdigest()[:20], 'title':title,'url':url,
    'publisher':source['name'],'kind':source['kind'],'author':author,
    'publishedAt':instant(published).isoformat(),'retrievedAt':stamp,'teamIds':source['teamIds'],
    'categories':categories,'headlineOnly':True,'notes':[], 'discoverySource':source['url']})
 return out

def parse_espn(data,stamp):
 if not isinstance(data.get('articles'),list):raise ValueError('ESPN articles missing')
 out=[]
 for a in data['articles']:
  url=a.get('links',{}).get('web',{}).get('href');cats=a.get('categories',[])
  ids={str(c.get('teamId',c.get('team',{}).get('id'))) for c in cats if c.get('type')=='team' and c.get('sportId')==41}
  if not ids or not safe_url(url) or not recent(a.get('published'),instant(stamp)):continue
  out.append({'id':'espn-'+str(a['id']),'title':plain(a['headline']),'url':url,'publisher':'ESPN',
   'kind':'National coverage / syndicated report','author':a.get('byline') or 'Byline not provided by feed',
   'publishedAt':a['published'],'retrievedAt':stamp,'teamIds':sorted(ids),
   'eventIds':[str(c['eventId']) for c in cats if c.get('type')=='event' and c.get('eventId')],
   'headlineOnly':True,'notes':[],'discoverySource':ESPN})
 return out

def for_game(game,articles,now):
 ids={str(game.get('awayId','')),str(game.get('homeId',''))}- {''}
 chosen={}
 for a in articles:
  if not ids.intersection(a.get('teamIds',[])):continue
  if a.get('eventIds') and str(game['id']) not in a['eventIds']:continue
  if not recent(a.get('publishedAt'),now):continue
  if a.get('validUntil') and instant(a['validUntil'])<now:continue
  # Post-tipoff reporting never appears as pregame evidence for that matchup.
  if instant(a['publishedAt'])>=instant(game['date']):continue
  item=copy.deepcopy(a)
  if item.get('reviewedAt') and instant(item['reviewedAt'])>=instant(game['date']):continue
  previous=chosen.get(key(item['url']))
  if not previous or (item.get('notes') and not previous.get('notes')):chosen[key(item['url'])]=item
 return sorted(chosen.values(),key=lambda a:(not bool(a.get('notes')), -instant(a['publishedAt']).timestamp()))[:10]

def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Docs-NCAAB-Research/1.0','Accept':'application/rss+xml, application/atom+xml, application/json, text/xml'})
 with urllib.request.urlopen(req,timeout=30) as r:
  raw=r.read(5_000_001)
  if len(raw)>5_000_000:raise ValueError('Source too large')
  return raw.decode('utf-8-sig')
def read(path,default=None):return json.loads(path.read_text()) if path.exists() else default
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2,allow_nan=False,ensure_ascii=False)+'\n');tmp.replace(path)
def main():
 now=datetime.now(timezone.utc);stamp=now.isoformat();today=now.astimezone(ZoneInfo('America/Chicago')).date()
 folder=ROOT/'data/reports';sources=read(ROOT/'config/report-sources.json');articles=[];health=[]
 def collect(s):
  path=folder/'sources'/(s['id']+'.json')
  try:
   raw=fetch(s['url']);items=parse_espn(json.loads(raw),stamp) if s['id']=='espn' else parse_feed(raw,s,stamp)
   write(path,{'retrievedAt':stamp,'articles':items})
   return items,{'name':s['name'],'url':s['url'],'status':'READY','retrievedAt':stamp,'articles':len(items)}
  except Exception as e:
   cache=read(path,{});return cache.get('articles',[]),{'name':s['name'],'url':s['url'],'status':'SOURCE_ERROR','message':str(e),'lastSuccess':cache.get('retrievedAt')}
 sources=sources+[{'id':'espn','name':'ESPN men’s college basketball news','url':ESPN}]
 with ThreadPoolExecutor(max_workers=5) as pool:
  for items,status in pool.map(collect,sources):articles.extend(items);health.append(status)
 reviewed=read(ROOT/'config/reviewed-reports.json',[])
 # Reviewed notes carry their real review timestamp; feed refreshes do not make them new confirmations.
 articles.extend(reviewed)
 days=[]
 for p in sorted((ROOT/'data/calculator/daily').glob('*.json')):
  d=read(p)
  if not str(today)<=d['date']<=str(today+timedelta(days=4)):continue
  games={}
  for g in d['matchups']:
   items=for_game(g,articles,now)
   games[g['id']]={'preparedAt':stamp,'articles':items,
    'localSourceTeams':sorted({tid for s in sources if s['id']!='espn' for tid in s.get('teamIds',[]) if tid in {g.get('awayId'),g.get('homeId')}}),
    'coverage':'Connected public feeds and reviewed articles only; not exhaustive. No report does not establish player availability.'}
  write(folder/(d['date']+'.json'),{'date':d['date'],'checkedAt':stamp,'games':games,'sources':health})
  days.append({'date':d['date'],'games':len(games),'withReports':sum(bool(g['articles']) for g in games.values())})
 status='PARTIAL' if any(s['status']!='READY' for s in health) else 'READY'
 write(folder/'health.json',{'status':status,'checkedAt':stamp,'sources':health,'days':days,'reviewedNotes':'Dated human-reviewed summaries; new feed items are headlines until reviewed'})
 print(json.dumps({'status':status,'sources':health,'days':days}))
 if all(s['status']!='READY' for s in health):raise SystemExit(1)
if __name__=='__main__':main()
