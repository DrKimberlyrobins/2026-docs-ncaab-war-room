"""Keep the canonical men's Division I directory independent of ESPN discovery."""
import json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from refresh import save
URL='https://web3.ncaa.org/directory/api/directory/memberList?type=12&division=I&sportCode=MBB'
PUBLIC_URL='https://web3.ncaa.org/directory/memberList?division=I&sportCode=MBB&type=12'

def build(rows):
    teams=[]
    for row in rows:
        if str(row.get('division'))!='1':raise ValueError('Non-Division-I member in source')
        if row.get('academicYear')!=2027:raise ValueError('Unexpected membership year; review season settings')
        teams.append({'id':'ncaa-'+str(row['orgId']),'ncaaId':row['orgId'],'displayName':row['nameOfficial'],'abbreviation':'','conference':(row.get('conferenceName') or 'Independent').strip(),'sourceUrl':'https://web3.ncaa.org/directory/orgDetail?id='+str(row['orgId'])})
    if len({t['id'] for t in teams})!=len(teams):raise ValueError('Duplicate NCAA institution IDs')
    if len(teams)!=365:raise ValueError('2026–27 directory differs from NCAA 365-team benchmark; review required')
    return {'season':'2026–27','academicYear':2027,'expectedCount':365,'teamCount':len(teams),'source':URL,'publicSource':PUBLIC_URL,'fetchedAt':datetime.now(timezone.utc).isoformat(),'teams':sorted(teams,key=lambda x:x['displayName'])}

if __name__=='__main__':
    req=urllib.request.Request(URL,headers={'User-Agent':'Docs-NCAAB-Research/1.0'})
    with urllib.request.urlopen(req,timeout=35) as response:rows=json.load(response)
    p=build(rows);save(Path('data/membership.json'),p)
    print('NCAA directory:',p['teamCount'],'unique institutions for',p['season'])
